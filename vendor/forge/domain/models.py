"""Small strict JSON object validator and immutable-by-convention domain records."""
from dataclasses import dataclass
from typing import Any, Dict, Mapping


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Record:
    schema: str
    data: Mapping[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"schema": self.schema, **dict(self.data)}


# Fields required by each versioned public object. Closed field sets prevent accidental trust.
FIELDS = {
    "forge-provider/v1": ({"id", "name", "provider_type", "entity_type", "evidence_state"},
        {"id", "name", "provider_type", "entity_type", "evidence_state", "claims", "metadata"}),
    "forge-capability/v1": ({"id", "capability_id", "evidence_state"},
        {"id", "capability_id", "evidence_state", "evidence", "platforms", "formats", "metadata"}),
    "forge-service/v1": ({"id", "service_id", "required_capabilities", "accepted_inputs", "possible_outputs", "pricing_models", "verification_profile", "suitability"},
        {"id", "service_id", "required_capabilities", "accepted_inputs", "possible_outputs", "platform_constraints", "pricing_models", "verification_profile", "suitability"}),
    "forge-request/v1": ({"id", "requested_capabilities", "supplied_assets", "required_deliverables", "preferred_deliverables", "worker_preference", "source_requirement", "normalization_provenance"},
        {"id", "requested_capabilities", "supplied_assets", "current_platform", "acceptable_authoring_platforms", "required_deliverables", "preferred_deliverables", "industry", "manufacturing_process", "budget", "currency", "deadline", "geography", "worker_preference", "provider_mode", "verification_profile", "confidentiality_sensitivity", "source_requirement", "normalization_provenance"}),
    "forge-match/v1": ({"request_id", "provider_id", "score", "reasons"}, {"request_id", "provider_id", "score", "reasons", "router_ref", "eligibility", "hard_constraint_failures", "unknown_constraints", "router_rank", "router_score", "router_decision", "adapter_version", "evidence_refs", "supplier_engagement"}),
    "forge-quote/v1": ({"id", "provider_id", "service_id", "amount", "currency", "status"}, {"id", "provider_id", "service_id", "amount", "currency", "status", "valid_until", "terms"}),
    "forge-deliverable/v1": ({"id", "request_id", "kind", "format", "artifact_ref"}, {"id", "request_id", "kind", "format", "artifact_ref", "metadata", "artifacts", "artifact_id", "filename", "role", "declared_format", "expected_format", "actual_format", "sha256", "size_bytes", "revision", "native_neutral", "source", "optional", "mime_type"}),
    "forge-verification/v1": ({"id", "deliverable_id", "profile", "status", "checks"}, {"id", "deliverable_id", "profile", "status", "checks", "bench_ref", "request_id", "profile_id", "overall_result", "execution_mode", "evidence_refs", "verifier_identity", "verifier_version", "verifier_commit", "timestamp", "human_review_status", "provenance", "request_hash", "deliverable_hash", "profile_hash", "result_hash", "no_implication_payment_release"}),
    "forge-transaction/v1": ({"id", "request_id", "provider_id", "quote_id", "status"}, {"id", "request_id", "provider_id", "quote_id", "status", "currency", "amount", "simulation"}),
    "forge-provider-evidence/v1": ({"evidence_id", "provider_identity_candidate", "source_type", "title", "observed_at", "source_quality", "evidence_hash", "asserted_capabilities", "asserted_platforms", "asserted_formats", "asserted_industries", "asserted_services", "asserted_pricing", "asserted_turnaround", "asserted_api_agent", "geographic_claims", "uncertainty_notes", "extraction_method", "extraction_provenance", "normalization_status"}, {"evidence_id", "provider_identity_candidate", "source_url", "source_id", "source_type", "title", "observed_at", "evidence_text", "structured_facts", "source_quality", "evidence_hash", "asserted_capabilities", "asserted_platforms", "asserted_formats", "asserted_industries", "asserted_services", "asserted_pricing", "asserted_turnaround", "asserted_api_agent", "geographic_claims", "uncertainty_notes", "extraction_method", "extraction_provenance", "normalization_status"}),
    "forge-provider-record/v2": ({"provider_id", "canonical_name", "canonical_domain", "provider_type", "observed_names", "known_aliases", "identity_confidence", "evidence_refs", "claims", "fulfillment_readiness", "pricing_evidence", "turnaround_evidence", "api_agent_evidence", "conflicts", "rebuild_hash"}, {"provider_id", "canonical_name", "canonical_domain", "provider_type", "observed_names", "known_aliases", "identity_confidence", "evidence_refs", "claims", "fulfillment_readiness", "pricing_evidence", "turnaround_evidence", "api_agent_evidence", "conflicts", "rebuild_hash"}),
    "forge-commercial-terms/v1": ({"transaction_id", "provider_quote", "provider_amount", "currency", "sourcing_fee", "verification_fee", "buyer_total", "taxes", "refund_terms", "cancellation_terms", "payment_method_classification", "payment_status", "provenance", "operator_approval", "execution_mode", "recorded_at", "upfront_payment_required", "upfront_payment_amount"}, {"transaction_id", "provider_quote", "provider_amount", "currency", "sourcing_fee", "verification_fee", "buyer_total", "taxes", "refund_terms", "cancellation_terms", "payment_method_classification", "payment_status", "provenance", "operator_approval", "execution_mode", "recorded_at", "upfront_payment_required", "upfront_payment_amount"}),
    "forge-pilot-acknowledgment/v1": ({"transaction_id", "party_type", "party_id", "acknowledgment_version", "terms_hash", "acknowledged_at", "terms_acknowledged", "disclosures", "provenance"}, {"transaction_id", "party_type", "party_id", "acknowledgment_version", "terms_hash", "acknowledged_at", "terms_acknowledged", "disclosures", "provenance"}),
    "forge-pilot-outcome/v1": ({"transaction_id", "execution_mode", "completion_status", "completion_milestones", "provider_id", "final_quote_id", "provider_amount", "forge_fee", "payment_status", "verification_outcome", "human_review_outcome", "buyer_acceptance", "metrics", "feedback_refs", "lessons", "recorded_at", "recorded_by"}, {"transaction_id", "execution_mode", "completion_status", "completion_milestones", "provider_id", "final_quote_id", "provider_amount", "forge_fee", "payment_status", "verification_outcome", "human_review_outcome", "buyer_acceptance", "metrics", "feedback_refs", "lessons", "recorded_at", "recorded_by"}),
    "forge-provider-record/v3": ({"provider_id", "canonical_name", "canonical_domain", "provider_type", "observed_names", "known_aliases", "identity_confidence", "evidence_refs", "claims", "fulfillment_readiness", "pricing_evidence", "turnaround_evidence", "api_agent_evidence", "supply_workflow_evidence", "conflicts", "rebuild_hash"}, {"provider_id", "canonical_name", "canonical_domain", "provider_type", "observed_names", "known_aliases", "identity_confidence", "evidence_refs", "claims", "fulfillment_readiness", "pricing_evidence", "turnaround_evidence", "api_agent_evidence", "supply_workflow_evidence", "conflicts", "rebuild_hash"}),
}
ENUMS = {
    ("provider_type",): {"individual", "engineering_firm", "design_studio", "marketplace", "manufacturer", "software_service", "cad_agent", "engineering_agent", "multi_agent_service"},
    ("entity_type",): {"HUMAN", "ORGANIZATION", "SOFTWARE", "AGENT", "HYBRID"},
    ("evidence_state",): {"UNKNOWN", "CLAIMED", "EVIDENCE_SUPPORTED", "VERIFIED", "BENCH_VERIFIED", "TRANSACTION_VERIFIED"},
    ("worker_preference",): {"human_only", "agent_allowed", "either"},
    ("status",): {"SIMULATED", "PENDING", "ACCEPTED", "REJECTED", "VERIFIED", "FAILED"},
    ("source_type",): {"official_provider_site", "official_service_page", "official_documentation", "official_api_documentation", "marketplace_profile", "public_directory", "public_social_profile", "public_case_study", "public_job_listing", "third_party_article", "search_snippet", "manually_supplied", "unknown"},
    ("source_quality",): {"PRIMARY", "STRONG_SECONDARY", "SECONDARY", "WEAK", "UNKNOWN"},
    ("normalization_status",): {"RAW", "EXTRACTED", "NORMALIZED", "REVIEW_REQUIRED"},
    ("identity_confidence",): {"high", "medium", "low"},
    ("claim_status",): {"UNKNOWN", "CLAIMED", "EVIDENCE_SUPPORTED", "VERIFIED", "BENCH_VERIFIED", "TRANSACTION_VERIFIED"},
    ("native_neutral",): {"native", "neutral", "mixed", "unknown"},
}
ARRAY_FIELDS = {"claims", "evidence", "platforms", "formats", "required_capabilities", "accepted_inputs", "possible_outputs", "platform_constraints", "pricing_models", "requested_capabilities", "supplied_assets", "acceptable_authoring_platforms", "required_deliverables", "preferred_deliverables", "manufacturing_process", "reasons", "checks", "artifacts", "asserted_capabilities", "asserted_platforms", "asserted_formats", "asserted_industries", "asserted_services", "asserted_pricing", "asserted_turnaround", "geographic_claims", "uncertainty_notes", "known_aliases", "observed_names", "evidence_refs", "pricing_evidence", "turnaround_evidence", "api_agent_evidence", "conflicts", "fulfillment_readiness"}
OBJECT_FIELDS = {"metadata", "geography", "normalization_provenance", "terms", "provider_identity_candidate", "structured_facts", "asserted_api_agent", "extraction_provenance"}
STRING_FIELDS = {"id", "name", "provider_type", "entity_type", "evidence_state", "capability_id", "service_id", "request_id", "provider_id", "quote_id", "deliverable_id", "verification_profile", "profile", "profile_id", "status", "execution_mode", "verifier_identity", "verifier_version", "timestamp", "currency", "valid_until", "current_platform", "industry", "deadline", "worker_preference", "provider_mode", "confidentiality_sensitivity", "source_requirement", "kind", "format", "artifact_ref", "artifact_id", "filename", "role", "declared_format", "expected_format", "revision", "native_neutral", "source", "mime_type", "sha256", "evidence_id", "source_url", "source_id", "source_type", "title", "observed_at", "evidence_text", "source_quality", "evidence_hash", "extraction_method", "normalization_status", "canonical_name", "canonical_domain", "rebuild_hash"}


def validate(schema: str, value: Mapping[str, Any]) -> Record:
    if schema not in FIELDS:
        raise ValidationError("unsupported schema: " + schema)
    if not isinstance(value, Mapping):
        raise ValidationError("object must be a mapping")
    required, allowed = FIELDS[schema]
    payload = dict(value)
    declared = payload.pop("schema", None)
    if declared is not None and declared != schema:
        raise ValidationError("schema discriminator does not match requested validator")
    missing = required - set(payload)
    extra = set(payload) - allowed
    if missing:
        raise ValidationError("missing required fields: " + ", ".join(sorted(missing)))
    if extra:
        raise ValidationError("unknown fields: " + ", ".join(sorted(extra)))
    for key, choices in ENUMS.items():
        field = key[0]
        if field in payload and payload[field] not in choices:
            raise ValidationError("invalid " + field + ": " + str(payload[field]))
    for field in ARRAY_FIELDS & set(payload):
        if not isinstance(payload[field], list):
            raise ValidationError(field + " must be an array")
    for field in OBJECT_FIELDS & set(payload):
        if not isinstance(payload[field], dict):
            raise ValidationError(field + " must be an object")
    for field in STRING_FIELDS & set(payload):
        if not isinstance(payload[field], str):
            raise ValidationError(field + " must be a string")
    for field in {"score", "amount", "budget", "router_score"} & set(payload):
        if payload[field] is None and field in {"router_score", "score"}:
            continue
        if not isinstance(payload[field], (int, float)) or isinstance(payload[field], bool):
            raise ValidationError(field + " must be numeric")
    if "size_bytes" in payload and (type(payload["size_bytes"]) is not int or payload["size_bytes"] < 0):
        raise ValidationError("size_bytes must be a non-negative integer")
    if schema == "forge-deliverable/v1":
        if "actual_format" in payload and payload["actual_format"] is not None and not isinstance(payload["actual_format"], str):
            raise ValidationError("actual_format must be a string or null")
        for artifact in payload.get("artifacts", []):
            if not isinstance(artifact, dict):
                raise ValidationError("artifacts must contain objects")
            required_artifact = {"artifact_id", "filename", "role", "declared_format", "expected_format", "sha256", "size_bytes", "revision", "native_neutral", "source", "optional", "mime_type", "actual_format"}
            if not required_artifact.issubset(artifact) or set(artifact) - required_artifact - {"artifact_ref"}:
                raise ValidationError("artifact has missing or unknown fields")
            for field in required_artifact - {"sha256", "size_bytes", "actual_format"}:
                if field in {"optional"}:
                    if type(artifact[field]) is not bool:
                        raise ValidationError("artifact optional must be boolean")
                elif field == "native_neutral":
                    if artifact[field] not in ENUMS[("native_neutral",)]:
                        raise ValidationError("invalid artifact native_neutral")
                elif not isinstance(artifact[field], str):
                    raise ValidationError("artifact " + field + " must be a string")
            if artifact["actual_format"] is not None and not isinstance(artifact["actual_format"], str):
                raise ValidationError("artifact actual_format must be a string or null")
            if artifact["sha256"] is not None and (not isinstance(artifact["sha256"], str) or len(artifact["sha256"]) != 64):
                raise ValidationError("artifact sha256 must be a 64-character string or null")
            if artifact["size_bytes"] is not None and (type(artifact["size_bytes"]) is not int or artifact["size_bytes"] < 0):
                raise ValidationError("artifact size_bytes must be a non-negative integer or null")
    if schema == "forge-capability/v1":
        from forge.ontology.registry import CAPABILITIES, FORMATS, PLATFORMS
        if payload["capability_id"] not in CAPABILITIES:
            raise ValidationError("unknown capability_id")
        if set(payload.get("platforms", [])) - set(PLATFORMS):
            raise ValidationError("unknown CAD platform reference")
        if set(payload.get("formats", [])) - set(FORMATS):
            raise ValidationError("unknown file-format reference")
    if schema == "forge-provider/v1" and payload["evidence_state"] == "UNKNOWN" and payload.get("claims"):
        raise ValidationError("UNKNOWN provider cannot carry factual claims")
    if schema == "forge-provider/v1" and payload["evidence_state"] != "UNKNOWN":
        for claim in payload.get("claims", []):
            if not isinstance(claim, dict) or not claim.get("evidence"):
                raise ValidationError("provider capability claims require evidence provenance")
    if schema == "forge-capability/v1" and payload["evidence_state"] != "UNKNOWN" and not payload.get("evidence"):
        raise ValidationError("non-UNKNOWN capability requires evidence provenance")
    if schema == "forge-request/v1" and not isinstance(payload["source_requirement"], str):
        raise ValidationError("source_requirement must preserve source text")
    if schema == "forge-request/v1" and payload.get("provider_mode", "either") not in {"human_only", "agent_only", "either"}:
        raise ValidationError("invalid provider_mode")
    if schema == "forge-match/v1" and "eligibility" in payload:
        if payload["eligibility"] not in {"ELIGIBLE", "INELIGIBLE", "UNKNOWN"}:
            raise ValidationError("invalid match eligibility")
        if payload.get("supplier_engagement") is not False:
            raise ValidationError("shadow matches cannot imply supplier engagement")
        if payload.get("router_rank") is not None and (type(payload["router_rank"]) is not int or payload["router_rank"] < 1):
            raise ValidationError("router_rank must be a positive integer or null")
    if schema == "forge-verification/v1" and "overall_result" in payload:
        if payload["overall_result"] not in {"PASS", "FAIL", "INCOMPLETE"}:
            raise ValidationError("invalid overall verification result")
        if payload.get("no_implication_payment_release") is not False:
            raise ValidationError("verification cannot imply payment release")
        if payload.get("execution_mode") not in {"SYNTHETIC", "OFFLINE", "SHADOW", "REAL"}:
            raise ValidationError("invalid verification execution mode")
        if payload.get("human_review_status") not in {"NOT_REQUIRED", "REQUIRED", "IN_PROGRESS", "APPROVED", "REJECTED"}:
            raise ValidationError("invalid human review status")
        for check in payload.get("checks", []):
            allowed = {"check_id", "requirement_type", "severity", "execution_authority", "support_state", "result", "expected_result", "actual", "evidence_refs", "source", "provenance", "reason_code"}
            if not isinstance(check, dict) or set(check) != allowed:
                raise ValidationError("invalid verification check fields")
            if check["severity"] not in {"REQUIRED", "OPTIONAL"}:
                raise ValidationError("invalid verification check severity")
            if check["execution_authority"] not in {"BENCH", "FORGE_DETERMINISTIC", "HUMAN_REVIEW", "EXTERNAL_TOOL", "UNKNOWN"}:
                raise ValidationError("invalid verification execution authority")
            if check["support_state"] not in {"EXECUTABLE", "REPRESENTABLE_ONLY", "HUMAN_REVIEW_REQUIRED", "UNSUPPORTED"}:
                raise ValidationError("invalid verification support state")
            if check["result"] not in {"PASS", "FAIL", "UNKNOWN", "NOT_EXECUTED", "UNSUPPORTED"}:
                raise ValidationError("invalid verification check result")
    if schema == "forge-provider-evidence/v1":
        from forge.evidence import evidence_hash
        from datetime import datetime
        from urllib.parse import urlsplit
        if not payload.get("source_url") and not payload.get("source_id"):
            raise ValidationError("evidence requires source_url or source_id")
        if payload.get("source_url"):
            parsed = urlsplit(payload["source_url"])
            if parsed.scheme not in {"https", "http"} or not parsed.hostname:
                raise ValidationError("source_url must be an HTTP(S) URL")
        if not payload.get("evidence_text") and not payload.get("structured_facts"):
            raise ValidationError("evidence requires observed text or structured facts")
        candidate = payload["provider_identity_candidate"]
        candidate_allowed = {"provider_id", "observed_name", "canonical_name", "canonical_domain", "domain", "provider_type", "known_aliases", "identity_confidence", "profile_linkages", "aliases_explicit", "manual_confirmation"}
        if set(candidate) - candidate_allowed or not {"observed_name", "provider_type"}.issubset(candidate):
            raise ValidationError("provider identity candidate has missing or unknown fields")
        if candidate["provider_type"] not in ENUMS[("provider_type",)]:
            raise ValidationError("invalid candidate provider_type")
        try:
            observed = datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
            if observed.tzinfo is None:
                raise ValueError("timezone is required")
        except ValueError as exc:
            raise ValidationError("observed_at must be ISO 8601") from exc
        api_data = payload["asserted_api_agent"]
        if api_data.get("fulfillment_readiness", "UNKNOWN") not in {"HUMAN_ONLY", "HUMAN_ASSISTED_AI", "SOFTWARE_ASSISTED", "AGENT_CAPABLE", "API_CAPABLE", "UNKNOWN"}:
            raise ValidationError("invalid fulfillment readiness")
        from forge.ontology.registry import CAPABILITIES
        for assertion in payload["asserted_capabilities"]:
            if set(assertion) - {"observed_text", "canonical_id", "mapping_type", "mapping_note"} or not isinstance(assertion.get("observed_text"), str):
                raise ValidationError("invalid asserted capability structure")
            if assertion.get("mapping_type", "direct") not in {"direct", "normalized"}:
                raise ValidationError("invalid capability mapping_type")
            if assertion.get("canonical_id") and assertion["canonical_id"] not in CAPABILITIES:
                raise ValidationError("unknown canonical capability assertion")
        pricing_types = {"fixed_price", "hourly", "starting_at", "quote_required", "subscription", "per_task", "marketplace_listing", "unknown"}
        pricing_allowed = {"pricing_kind", "currency", "amount", "range_min", "range_max", "pricing_unit", "service_id", "evidence_id", "observed_text"}
        if any(item.get("pricing_kind") not in pricing_types or set(item) - pricing_allowed for item in payload["asserted_pricing"]):
            raise ValidationError("invalid pricing evidence kind")
        for item in payload["asserted_pricing"]:
            if any(key in item and (not isinstance(item[key], (int, float)) or isinstance(item[key], bool) or item[key] < 0) for key in {"amount", "range_min", "range_max"}):
                raise ValidationError("pricing amounts must be non-negative numbers")
            if item.get("range_min") is not None and item.get("range_max") is not None and item["range_min"] > item["range_max"]:
                raise ValidationError("pricing range minimum exceeds maximum")
            if item.get("evidence_id") != payload["evidence_id"]:
                raise ValidationError("pricing evidence must reference its evidence record")
        turnaround_kinds = {"stated_duration", "stated_range", "service_specific", "quote_required", "unknown"}
        turnaround_allowed = {"kind", "duration_value", "duration_unit", "range_min", "range_max", "service_id", "evidence_id", "observed_text"}
        if any(item.get("kind") not in turnaround_kinds or set(item) - turnaround_allowed for item in payload["asserted_turnaround"]):
            raise ValidationError("invalid turnaround evidence")
        if any(item.get("evidence_id") != payload["evidence_id"] for item in payload["asserted_turnaround"]):
            raise ValidationError("turnaround evidence must reference its evidence record")
        for assertion in payload["asserted_platforms"] + payload["asserted_formats"]:
            allowed_assertion = {"observed_text", "mapping_type", "mapping_note"}
            if assertion in payload["asserted_formats"]:
                allowed_assertion.add("operation")
            if isinstance(assertion, dict) and set(assertion) - allowed_assertion:
                raise ValidationError("unknown platform/format assertion field")
            if not isinstance(assertion, (str, dict)):
                raise ValidationError("platform/format assertion must be a string or object")
            if isinstance(assertion, dict) and assertion.get("operation", "can_read") not in {"can_read", "can_modify", "can_author", "can_deliver"}:
                raise ValidationError("invalid file-format operation")
        for assertion in payload["asserted_services"]:
            if set(assertion) - {"value", "observed_text"} or not isinstance(assertion.get("value"), str):
                raise ValidationError("invalid asserted service structure")
        for assertion in payload["asserted_industries"]:
            if set(assertion) - {"value", "observed_text"} or not isinstance(assertion.get("value"), str):
                raise ValidationError("invalid asserted industry structure")
        for assertion in payload["geographic_claims"]:
            if set(assertion) - {"observed_text", "country", "region", "city", "scope"}:
                raise ValidationError("unknown geographic claim field")
        api_allowed = {"public_api_documented", "private_api_claimed", "mcp_endpoint", "agent_endpoint", "autonomous_fulfillment", "human_approval_required", "fulfillment_readiness", "evidence_text"}
        if set(api_data) - api_allowed:
            raise ValidationError("unknown API/agent evidence field")
        for field in {"public_api_documented", "private_api_claimed", "mcp_endpoint", "agent_endpoint", "autonomous_fulfillment", "human_approval_required"} & set(api_data):
            if not isinstance(api_data[field], bool):
                raise ValidationError(field + " must be boolean")
        workflow_fields = {
            "request_channel": {"web_form", "email", "api", "marketplace_listing", "phone", "unknown"},
            "quote_method": {"manual_quote", "instant_automated", "request_for_quote", "fixed_sku", "marketplace_catalog", "unknown"},
            "fixed_price_sku_available": {True, False}, "file_upload_workflow": {True, False},
            "human_interaction_requirement": {"required", "optional", "unknown"}, "structured_intake": {True, False},
            "agent_compatibility": {"compatible", "not_documented", "unknown"},
        }
        for assertion in payload.get("structured_facts", {}).get("supply_workflow", []):
            if set(assertion) - {"field", "value", "observed_text"} or assertion.get("field") not in workflow_fields:
                raise ValidationError("invalid supply workflow assertion structure")
            if type(assertion.get("value")) not in {str, bool} or assertion["value"] not in workflow_fields[assertion["field"]]:
                raise ValidationError("invalid supply workflow assertion value")
        expected = evidence_hash(payload)
        if payload["evidence_hash"] != expected:
            raise ValidationError("evidence_hash does not match canonical evidence content")
    if schema in {"forge-provider-record/v2", "forge-provider-record/v3"}:
        claim_statuses = ENUMS[("claim_status",)]
        allowed_claim_fields = {"claim_id", "kind", "value", "claim_status", "evidence_refs", "assertion_type", "observed_text", "mapping_note", "operation"}
        evidence_refs = set(payload["evidence_refs"])
        for claim in payload["claims"]:
            if not {"claim_id", "kind", "value", "claim_status", "evidence_refs"}.issubset(claim) or set(claim) - allowed_claim_fields:
                raise ValidationError("invalid normalized claim structure")
            if claim["claim_status"] not in claim_statuses:
                raise ValidationError("invalid claim_status")
            if claim["claim_status"] != "UNKNOWN" and not claim["evidence_refs"]:
                raise ValidationError("factual claims require provenance evidence")
            if set(claim["evidence_refs"]) - evidence_refs:
                raise ValidationError("claim references unknown evidence")
        readiness_values = {"HUMAN_ONLY", "HUMAN_ASSISTED_AI", "SOFTWARE_ASSISTED", "AGENT_CAPABLE", "API_CAPABLE", "UNKNOWN"}
        for item in payload["fulfillment_readiness"]:
            if set(item) - {"classification", "evidence_refs"} or item.get("classification") not in readiness_values:
                raise ValidationError("invalid provider readiness record")
            if set(item.get("evidence_refs", [])) - evidence_refs:
                raise ValidationError("readiness references unknown evidence")
        for item in payload.get("supply_workflow_evidence", []):
            if not {"field", "value", "evidence_id"}.issubset(item) or item["evidence_id"] not in evidence_refs:
                raise ValidationError("supply workflow facts require an evidence reference")
    return Record(schema, payload)
