# FORGE Relay — NEAR Hackathon 2026

FORGE Relay compares task demand and provider listings across agent marketplaces, exposes evidence and procurement gaps, and demonstrates an auditable task-to-artifact handoff locally. Research and structured data are the initial use cases.

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
| Payments | Disabled. No paid outcome, onchain settlement or external agent fulfillment has occurred |

Local workers are deterministic Python programs, **not LLM agents or independent marketplace operators**. Discovery does not establish provider trust, availability, subcontract permission or full-job pricing. Hashes detect inconsistencies; they are not signatures or independent attestations and cannot prevent an owner from rewriting an entire bundle. Verification checks fidelity to captured evidence, not whether marketplace claims are true. The existing synthetic FORGE lifecycle rehearsal is separately labeled and does not establish settlement.

## NEAR's role and hackathon scope

NEAR Agent Market supplies live provider identities, pricing plans and buyer-job discovery. New code built during the hackathon normalizes those records alongside other catalogs, compares capability/cost constraints and records local coordination evidence. The offline demo uses frozen public facts so judges can reproduce it without credentials. This project does not integrate NEAR Intents, deploy a smart contract or demonstrate trustless settlement.

The seven vendored FORGE files are **pre-existing baseline**, copied unchanged from commit `168a23bfecd67aee05b54004f6fdac3eb0992efa`; see `vendor/PROVENANCE.json`. No original FLOP runtime or repository is used. The new hackathon work is the `relay/`, `web/`, `tests/`, `fixtures/` and deployment preparation code; the first isolated project commit is `ab4b936`. The public candidate uses a fresh history for privacy; those development commits remain in the private working repository. AI coding assistance was used. License selection and public repository publication remain owner review items; see `PUBLICATION-REVIEW.md`.

## Submission materials

See [publication review](PUBLICATION-REVIEW.md), [recording script](submission/DEMO-SCRIPT.md), and [implementation evidence](submission/VERIFICATION.md). This repository has not yet been published or submitted.


## Optional live discovery

Run `python3 -m relay refresh` and `python3 -m relay.server` for the separate live workspace at http://127.0.0.1:8765. Public refresh makes fixed catalog GET requests. A project-specific NEAR token can be entered privately for job-board reads; no token is required for the offline demo. See [NEAR setup](docs/NEAR.md).

## Rights and publication status

This is a private review candidate. `LICENSE.proposed.txt` is a proposal, not an adopted license. Public release requires owner approval of the license and the seven baseline FORGE files listed in `vendor/PROVENANCE.json`. Public visibility permits source inspection and GitHub forks even when commercial reuse is restricted. No unrelated FLOP project source is included.
