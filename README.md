# Forge Relay by FRBL Labs

**[Open the public discovery demo](https://forge-relay-pearl.vercel.app)** · [Demo script](submission/DEMO-SCRIPT.md) · [Pilot evidence and limits](submission/PILOT-RESULTS.md)

Forge Relay connects fragmented agent catalogs to explicit task requirements and reviewable delivery evidence. It aims to help buyers find specialists beyond one marketplace while keeping price uncertainty and acceptance decisions visible. The hypothesis that this increases accepted work remains untested.

## Try the public demo

1. Open the public demo; expect a dated snapshot with provider and public demand records.
2. Keep the example research/extraction brief and click **Compare providers**. Expect candidate listings and single- or cross-market proposals with unresolved pricing and execution conditions disclosed.
3. Inspect source links and download a proposal. Comparing and downloading do not hire anyone or move funds.
4. The live pilot page is an owner-configured buyer integration, not public access to our private NEAR task. A signed-out visitor sees a connection prompt. Judges need no account for discovery or the offline workflow below.

The production frontend is a filtered public snapshot preview, not the full local workspace. Authenticated buyer jobs, local databases and credentials are not published. The public site uses FRBL Labs branding, a white background and readable heading spacing.

## Real pilot result

On November 11, 2026, an operator funded one $0.50 research task on NEAR Agent Market. Forge Relay retrieved two actual delivered revisions and failed their citation checks. Human review also found the directory research absent. An operator requested corrections and then opened a full-refund dispute after the second inadequate delivery. The last confirmed state is **dispute under review**, with a $0.0250 deposit held; refund and deposit return are not confirmed.

This demonstrates a funded single-market handoff, artifact retrieval, inadequate-delivery detection and operator-led escalation. It does not demonstrate accepted external research, provider payout, completed cross-market execution, an autonomous dispute agent, or a higher conversion rate. The Bench evaluation is an isolated evidence record prepared with operator assistance; it is not an invocation of the existing FLOP Bench agent or an enforced reputation policy. See the [claim-by-claim evidence](submission/PILOT-RESULTS.md).

## Judge quick start — offline, no keys, no spending

Requires Python 3.9+; the runtime uses the standard library. Node is optional for JavaScript syntax checking. No package installation, wallet, model API, account or network connection is needed for this demo.

```sh
python3 -m relay.server --demo --port 8766
```

Open **http://127.0.0.1:8766/#demo**. Select **Run local handoff demo** with the citation fault selected. Expect **FAIL → PASS**, a returned six-provider comparison from three marketplaces, and **VERIFIED PENDING OPERATOR ACCEPTANCE**. Inspect the returned artifact and its checks. Select **Accept this verified revision locally** to record a receipt pinned to its hash. Export the report or the complete evidence bundle.

To reproduce the worker flow without a browser:

```sh
python3 -m relay demo
python3 scripts/verify_demo.py submission/sample-evidence.json
python3 -m unittest discover -s tests -v
```

Expected CLI output: a unique run ID, `verification_results: ["FAIL", "PASS"]`, an artifact SHA-256 and a saved bundle path. A clean run without injected failure is available by unchecking the demo checkbox. Each run has a new ID; identical final artifact content has the same hash. Local acceptance is an explicit operator action, never inferred from verification.

## What executes and what does not

| Layer | Implemented behavior |
|---|---|
| NEAR integration | Public agent/pricing API discovery and optional authenticated public job-board reads in the separate live workspace |
| Cross-market discovery | NEAR, Circle Exa APIs, Taskmarket, TakoAPI, AgentMarket and Olas; evidence quality differs by source |
| Offline input | Twelve frozen public provider records from NEAR, TakoAPI and AgentMarket, with source URLs and observation dates |
| Handoff | JSON requests/results between actual separate local extractor, writer and verifier processes; input/output hashes recorded |
| Verification | Row count, marketplace diversity, duplicates, every returned field against the frozen snapshot, citations, timestamps and uncertainty disclosures |
| Revision | Optional, explicitly injected missing-citation fault is rejected; a corrected artifact is returned and checked |
| Acceptance | Local operator receipt bound to the verified artifact and sealed run bundle |
| Payments | Offline demo: disabled. Optional live pilot: operator-approved NEAR checkout, with no automatic payment calls. External delivery and settlement must be verified before claiming a paid outcome |

Local workers are deterministic Python programs, **not LLM agents or independent marketplace operators**. Discovery does not establish provider trust, availability, subcontract permission or full-job pricing. Hashes detect inconsistencies; they are not signatures or independent attestations and cannot prevent an owner from rewriting an entire bundle. Verification checks fidelity to captured evidence, not whether marketplace claims are true. The existing synthetic FORGE lifecycle rehearsal is separately labeled and does not establish settlement.

## NEAR's role and hackathon scope

NEAR Agent Market supplies provider identities, price discovery, buyer checkout, escrow-backed task status and delivered results. The real pilot used its USD balance and operator-approved marketplace checkout; no NEAR Intents or onchain transaction is claimed. New code built during the hackathon normalizes those records alongside other catalogs, compares capability/cost constraints and records local coordination evidence. The offline demo uses frozen public facts so judges can reproduce it without credentials. This project does not integrate NEAR Intents, deploy a smart contract or demonstrate trustless settlement.

The seven vendored FORGE files are **pre-existing baseline**, copied unchanged from commit `168a23bfecd67aee05b54004f6fdac3eb0992efa`; see `vendor/PROVENANCE.json`. No original FLOP runtime or repository is used. The new hackathon work is the `relay/`, `web/`, `tests/`, `fixtures/` and deployment preparation code; the first isolated project commit is `ab4b936`. The public candidate uses a fresh history for privacy; those development commits remain in the private working repository. AI coding assistance was used. The owner approved the evaluation license and publication, including the seven baseline files; see `LICENSE` and `PUBLICATION-REVIEW.md`.

## Submission materials

See [publication review](PUBLICATION-REVIEW.md), [recording script](submission/DEMO-SCRIPT.md), and [implementation evidence](submission/VERIFICATION.md). The repository is released for review; the hackathon application and X demo post remain drafts. Proposed tracks: AI Swarms and AI Security & Defense. The swarm example is not implemented: there are no sealed bids, pooled funds or per-agent subaccounts. The implemented coordination approach is cross-market discovery plus explicit delivery review.


## Optional live discovery

Run `python3 -m relay refresh` and `python3 -m relay.server` for the separate live workspace at http://127.0.0.1:8765. Public refresh makes fixed catalog GET requests. A project-specific NEAR token can be entered privately for job-board reads; no token is required for the offline demo. See [NEAR setup](docs/NEAR.md).

## Rights and publication status

Released under the [Hackathon Evaluation License](LICENSE), with owner approval covering the seven baseline FORGE files listed in `vendor/PROVENANCE.json`. Public visibility permits source inspection and GitHub forks even when commercial reuse is restricted. No unrelated FLOP project source is included.

## Optional live buyer pilot

The separate pilot at port 8767 adds buyer OAuth, current provider quotes, a stable checkout draft, read-only draft/job tracking, returned-artifact hashing and an exact-version acceptance handoff. It does not execute other marketplaces’ providers automatically. See [live pilot setup and limitations](docs/LIVE-PILOT.md).

`python3 -B scripts/prepare_vercel.py --live` builds a separate hosted package with durable Redis state. The offline quick start still requires no accounts, keys, payment, or network. Automated fixtures cover the full handoff; they are not evidence that an external provider has delivered work.
