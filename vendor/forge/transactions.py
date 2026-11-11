"""Simulation-only, deterministic Forge transaction state machine."""
from __future__ import annotations

import hashlib
import json

from forge.domain.models import ValidationError

STATES = (
    "DRAFT", "REQUEST_READY", "MATCHING", "CANDIDATES_READY", "QUOTE_REQUEST_READY", "QUOTING",
    "QUOTES_RECEIVED", "PROVIDER_SELECTED", "AUTHORIZATION_PENDING", "AUTHORIZED", "WORK_IN_PROGRESS",
    "DELIVERABLE_SUBMITTED", "VERIFICATION_PENDING", "VERIFICATION_INCOMPLETE", "VERIFICATION_FAILED",
    "REVISION_REQUESTED", "POLICY_PENDING", "POLICY_HOLD", "POLICY_DENIED", "ACCEPTANCE_PENDING",
    "ACCEPTED", "TRANSACTION_READY", "SIMULATED_SETTLED", "CANCELLED", "EXPIRED", "FAILED",
)
ACTORS = ("BUYER", "PROVIDER", "FORGE", "ROUTER", "BENCH", "SENTINEL", "COMMERCE", "OPERATOR", "SYSTEM", "UNKNOWN", "HUMAN_REVIEW")
TERMINAL = {"SIMULATED_SETTLED", "CANCELLED", "EXPIRED", "FAILED"}
TRANSITIONS = {
    "DRAFT": {"REQUEST_READY", "CANCELLED"},
    "REQUEST_READY": {"MATCHING", "CANCELLED", "EXPIRED"},
    "MATCHING": {"CANDIDATES_READY", "FAILED", "CANCELLED"},
    "CANDIDATES_READY": {"QUOTE_REQUEST_READY", "CANCELLED", "EXPIRED"},
    "QUOTE_REQUEST_READY": {"QUOTING", "CANCELLED", "EXPIRED"},
    "QUOTING": {"QUOTES_RECEIVED", "CANCELLED", "EXPIRED", "FAILED"},
    "QUOTES_RECEIVED": {"PROVIDER_SELECTED", "CANCELLED", "EXPIRED"},
    "PROVIDER_SELECTED": {"AUTHORIZATION_PENDING", "CANCELLED", "EXPIRED"},
    "AUTHORIZATION_PENDING": {"AUTHORIZED", "POLICY_HOLD", "POLICY_DENIED", "CANCELLED", "EXPIRED"},
    "AUTHORIZED": {"WORK_IN_PROGRESS", "CANCELLED"},
    "WORK_IN_PROGRESS": {"DELIVERABLE_SUBMITTED", "CANCELLED", "EXPIRED"},
    "DELIVERABLE_SUBMITTED": {"VERIFICATION_PENDING", "CANCELLED"},
    "VERIFICATION_PENDING": {"VERIFICATION_INCOMPLETE", "VERIFICATION_FAILED", "POLICY_PENDING", "CANCELLED"},
    "VERIFICATION_INCOMPLETE": {"REVISION_REQUESTED", "POLICY_PENDING", "CANCELLED"},
    "VERIFICATION_FAILED": {"REVISION_REQUESTED", "CANCELLED"},
    "REVISION_REQUESTED": {"WORK_IN_PROGRESS", "CANCELLED"},
    "POLICY_PENDING": {"POLICY_HOLD", "POLICY_DENIED", "ACCEPTANCE_PENDING", "CANCELLED"},
    "POLICY_HOLD": {"POLICY_PENDING", "CANCELLED"},
    "POLICY_DENIED": {"CANCELLED"},
    "ACCEPTANCE_PENDING": {"ACCEPTED", "REVISION_REQUESTED", "CANCELLED"},
    "ACCEPTED": {"TRANSACTION_READY", "CANCELLED"},
    "TRANSACTION_READY": {"SIMULATED_SETTLED", "CANCELLED"},
}
_HEX = set("0123456789abcdef")


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _guard(previous, target, data):
    if target == "REQUEST_READY" and data.get("request_valid") is not True:
        raise ValidationError("valid request required")
    if target == "PROVIDER_SELECTED":
        if data.get("quote_valid") is not True or data.get("selection_authority") not in {"BUYER", "OPERATOR"} or data.get("quote_status") not in {"VALID", "SUBMITTED"}:
            raise ValidationError("explicit selection of a valid quote required")
        if data.get("budget_status") == "OUTSIDE" or data.get("quote_status") in {"EXPIRED", "INVALID"}:
            raise ValidationError("quote is not selectable")
        if data.get("mode_compatible") is False:
            raise ValidationError("provider fulfillment mode mismatch")
    if target == "AUTHORIZED":
        if data.get("quote_valid") is not True or data.get("authorization_mode") != "SIMULATED" or "unresolved_conditions" not in data:
            raise ValidationError("valid quote and simulated authorization required")
        if data.get("policy_decision") in {"DENY", "HOLD"}:
            raise ValidationError("policy blocks authorization")
        manual=data.get("authorization_record",{})
        if data.get("policy_decision")=="UNKNOWN" and not (manual.get("mode") in {"EXTERNAL_MANUAL_AUTHORIZATION_RECORDED","SIMULATED_AUTHORIZATION"} and manual.get("reference")):
            raise ValidationError("unknown policy requires a separately recorded external manual authorization")
        if data.get("unresolved_conditions"):
            raise ValidationError("authorization has unresolved policy conditions")
    if target == "POLICY_PENDING" and (data.get("verification_result") != "PASS" or not data.get("verification_ref")):
        raise ValidationError("referenced verification result must PASS before policy gate")
    if target == "ACCEPTANCE_PENDING" and (data.get("policy_decision") not in {"ALLOW", "ALLOW_WITH_CONDITIONS"} or not data.get("policy_ref")):
        raise ValidationError("referenced policy result must allow before acceptance")
    if target == "ACCEPTED":
        if data.get("acceptance_status") != "ACCEPTED" or data.get("authority") not in {"BUYER", "OPERATOR"} or not data.get("verification_ref") or not data.get("policy_ref"):
            raise ValidationError("explicit buyer/operator acceptance with verification and policy references required")
    if target == "TRANSACTION_READY":
        required = ("request_valid", "quote_valid", "simulated_authorization", "deliverable_submitted", "verification_pass", "policy_satisfied", "buyer_accepted")
        if any(data.get(key) is not True for key in required) or data.get("unresolved_conditions"):
            raise ValidationError("transaction readiness preconditions not satisfied")
    if target == "CANCELLED" and data.get("cancellation_reason") not in {"BUYER_CANCELLED", "PROVIDER_WITHDRAWAL", "QUOTE_EXPIRED", "POLICY_DENIED", "VERIFICATION_FAILED", "OPERATOR_CANCELLED", "BUYER_REJECTED"}:
        raise ValidationError("structured cancellation reason required")
    if target == "SIMULATED_SETTLED":
        if previous != "TRANSACTION_READY":
            raise ValidationError("only a ready transaction can be simulated settled")
        expected={"settlement_mode":"SIMULATED", "payment_executed":False, "transfer_executed":False, "wallet_used":False, "external_system_invoked":False}
        if any(data.get(k) != v for k,v in expected.items()):
            raise ValidationError("simulated settlement receipt must prove no external transfer")
    if target == "VERIFICATION_FAILED" and data.get("verification_result") != "FAIL":
        raise ValidationError("verification result must be FAIL")
    if target == "VERIFICATION_INCOMPLETE" and data.get("verification_result") not in {"INCOMPLETE", "UNKNOWN"}:
        raise ValidationError("verification result must be INCOMPLETE or UNKNOWN")
    if target == "POLICY_DENIED" and data.get("policy_decision") != "DENY":
        raise ValidationError("policy result must be DENY")
    if target == "POLICY_HOLD" and data.get("policy_decision") not in {"HOLD", "ALLOW_WITH_CONDITIONS", "UNKNOWN"}:
        raise ValidationError("policy result must require hold")


def replay(events):
    state, previous_hash, seen_ids, seen_keys = "DRAFT", "0" * 64, set(), {}
    facts, revisions = {}, []
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or event.get("sequence") != index:
            raise ValidationError("malformed or out-of-order event sequence")
        required = {"schema", "event_id", "transaction_id", "sequence", "prior_state", "next_state", "event_type", "actor", "timestamp", "reason_code", "evidence", "data", "synthetic", "previous_hash", "event_hash", "idempotency_key"}
        if set(event) != required or event["actor"] not in ACTORS or event["synthetic"] is not True:
            raise ValidationError("malformed transaction event")
        if event["event_id"] in seen_ids or event["previous_hash"] != previous_hash or event["prior_state"] != state:
            raise ValidationError("duplicate event or broken event chain")
        if event["next_state"] not in TRANSITIONS.get(state, set()):
            raise ValidationError("invalid transaction transition")
        key = event["idempotency_key"]
        if key in seen_keys:
            raise ValidationError("duplicate idempotency key in event log")
        if not all(isinstance(event[k], str) and event[k] for k in ("event_id", "transaction_id", "timestamp", "reason_code", "idempotency_key")):
            raise ValidationError("malformed transaction event identifiers")
        if not isinstance(event["evidence"], list) or not isinstance(event["data"], dict):
            raise ValidationError("malformed transaction event evidence or facts")
        if event["next_state"] == "PROVIDER_SELECTED" and event["actor"] not in {"BUYER", "OPERATOR"}:
            raise ValidationError("provider selection requires buyer or operator authority")
        if event["next_state"] == "ACCEPTED" and event["actor"] not in {"BUYER", "OPERATOR"}:
            raise ValidationError("acceptance requires buyer or operator authority")
        if event["next_state"] == "AUTHORIZED" and event["actor"] not in {"FORGE", "OPERATOR", "SYSTEM"}:
            raise ValidationError("simulated authorization requires Forge/operator authority")
        combined={**facts, **event["data"]}
        _guard(state, event["next_state"], combined)
        expected_id="txn-event-" + digest([event["transaction_id"], index, event["next_state"], event["data"], event["idempotency_key"]])[:24]
        if event["event_id"] != expected_id:
            raise ValidationError("transaction event ID is not deterministic")
        body = {k: v for k, v in event.items() if k != "event_hash"}
        if event["event_hash"] != digest(body):
            raise ValidationError("transaction event hash mismatch")
        seen_ids.add(event["event_id"]); seen_keys[key] = event["event_id"]
        facts.update(event["data"])
        if event["next_state"] == "REVISION_REQUESTED": revisions.append(event["data"].get("revision", len(revisions) + 1))
        state, previous_hash = event["next_state"], event["event_hash"]
    return {"state": state, "event_count": len(events), "last_event_hash": previous_hash, "facts": facts, "revision_history": revisions}


class Transaction:
    def __init__(self, transaction_id, events=None):
        if not transaction_id:
            raise ValidationError("transaction ID required")
        self.transaction_id = transaction_id
        self.events = list(events or [])
        self.snapshot = replay(self.events)
        if any(e["transaction_id"] != transaction_id for e in self.events):
            raise ValidationError("transaction ID mismatch")

    @property
    def state(self):
        return self.snapshot["state"]

    def state_record(self):
        return {"schema":"forge-transaction-state/v1", "transaction_id":self.transaction_id,
                "state":self.state, "event_count":len(self.events), "last_event_hash":self.snapshot["last_event_hash"]}

    def transition(self, target, *, actor, timestamp, reason_code, evidence=(), data=None, idempotency_key):
        if actor not in ACTORS or target not in STATES:
            raise ValidationError("unknown actor or transaction state")
        data = dict(data or {})
        prior_key = next((e for e in self.events if e["idempotency_key"] == idempotency_key), None)
        if prior_key:
            if prior_key["next_state"] == target and prior_key["data"] == data:
                return prior_key
            raise ValidationError("idempotency key reused with different command")
        if target not in TRANSITIONS.get(self.state, set()):
            raise ValidationError(f"invalid transaction transition: {self.state} -> {target}")
        _guard(self.state, target, {**self.snapshot["facts"], **data})
        seq = len(self.events) + 1
        prev = self.snapshot["last_event_hash"]
        body = {"schema": "forge-transaction-event/v1", "event_id": "txn-event-" + digest([self.transaction_id, seq, target, data, idempotency_key])[:24],
            "transaction_id": self.transaction_id, "sequence": seq, "prior_state": self.state, "next_state": target,
            "event_type": target, "actor": actor, "timestamp": timestamp, "reason_code": reason_code,
            "evidence": list(evidence), "data": data, "synthetic": True, "previous_hash": prev, "idempotency_key": idempotency_key}
        event = dict(body, event_hash=digest(body))
        self.events.append(event)
        self.snapshot = replay(self.events)
        return event


def settlement_receipt():
    return {"settlement_mode": "SIMULATED", "payment_executed": False, "transfer_executed": False,
            "wallet_used": False, "external_system_invoked": False}


def validate_quote(quote, *, now, budget=None, required_formats=(), required_input_formats=(), required_capabilities=(), fulfillment_mode=None, verification_required=False):
    """Evaluate only supplied hard requirements; never rank or fill missing quote terms."""
    from datetime import datetime
    if not isinstance(quote, dict) or not all(quote.get(k) for k in ("id", "provider_id", "service_id", "currency", "status")):
        raise ValidationError("quote identity, service, currency, and status are required")
    import pathlib
    from jsonschema import Draft202012Validator
    schema=json.loads((pathlib.Path(__file__).resolve().parents[1]/"schemas/forge-quote-v1.json").read_text())
    try: Draft202012Validator(schema).validate(quote)
    except Exception as exc: raise ValidationError("quote does not satisfy forge-quote/v1") from exc
    try:
        current=datetime.fromisoformat(now.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValidationError("comparison timestamp must be ISO-8601") from exc
    result={"quote_id":quote["id"], "price_status":"UNKNOWN", "budget_status":"UNKNOWN", "turnaround_status":"UNKNOWN", "format_compliant":None, "capabilities_compliant":None, "mode_compatible":None, "verification_commitment":None, "valid":False}
    if quote.get("amount") is not None:
        result["price_status"]="KNOWN"
        result["budget_status"]="WITHIN" if budget is None or quote["amount"] <= budget else "OUTSIDE"
    if quote.get("estimated_turnaround"):
        result["turnaround_status"]="KNOWN"
    if required_formats:
        result["format_compliant"]={str(x).lower() for x in required_formats}.issubset({str(x).lower() for x in quote.get("output_formats", [])})
    if required_input_formats:
        result["input_format_compliant"]={str(x).lower() for x in required_input_formats}.issubset({str(x).lower() for x in quote.get("accepted_input_formats", [])})
    if required_capabilities:
        result["capabilities_compliant"]=set(required_capabilities).issubset(set(quote.get("capabilities_covered", [])))
    if fulfillment_mode:
        result["mode_compatible"]=quote.get("fulfillment_mode", "UNKNOWN") == fulfillment_mode
    if verification_required:
        result["verification_commitment"]=bool(quote.get("verification_obligations"))
    expiration=quote.get("valid_until")
    if expiration:
        try: expired=current >= datetime.fromisoformat(expiration.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc: raise ValidationError("quote expiration must be ISO-8601") from exc
        result["expired"]=expired
    else: result["expired"]=False
    result["valid"]=(quote.get("status") in {"SUBMITTED", "VALID", "SELECTED"} and not result["expired"] and result["budget_status"] != "OUTSIDE" and result["format_compliant"] is not False and result.get("input_format_compliant") is not False and result["capabilities_compliant"] is not False and result["mode_compatible"] is not False and result["verification_commitment"] is not False)
    return result


def provider_selection(*, selection_id, request_id, provider_id, quote_id, authority, selected_at, reasons, required_conditions=(), unresolved_conditions=()):
    if authority not in {"BUYER", "OPERATOR"}: raise ValidationError("selection authority must be BUYER or OPERATOR")
    return {"schema":"forge-provider-selection/v1", "selection_id":selection_id, "request_id":request_id, "provider_id":provider_id, "quote_id":quote_id, "selection_authority":authority, "selected_at":selected_at, "reasons":list(reasons), "required_conditions":list(required_conditions), "unresolved_conditions":list(unresolved_conditions), "synthetic":True}


def acceptance_record(*, acceptance_id, status, authority, deliverable_revision, timestamp, reason, verification_ref, policy_ref):
    if status not in {"ACCEPTED", "REJECTED", "REVISION_REQUESTED", "PENDING"} or authority not in {"BUYER", "OPERATOR"}:
        raise ValidationError("invalid acceptance status or authority")
    return {"schema":"forge-acceptance/v1", "acceptance_id":acceptance_id, "status":status, "authority":authority, "deliverable_revision":deliverable_revision, "timestamp":timestamp, "reason":reason, "verification_ref":verification_ref, "policy_ref":policy_ref, "synthetic":True}
