# Execution and verification evidence

## Reproduce without accounts or spending

Run `python3 -m unittest discover -s tests -v`, `python3 -m relay demo`, and `python3 scripts/verify_demo.py submission/sample-evidence.json` from the repository root. The current suite contains 71 tests. It covers separate worker processes, missing citations, changed values, duplicates, tampering, exact-version acceptance, HTTP origin boundaries, buyer-session isolation, quote ceilings and absence of automatic paid calls.

The offline browser story is Run → extractor → writer → verifier FAIL → corrected report → PASS → explicit local acceptance. These are deterministic workers and synthetic acceptance, not an external provider success. `local-demo.jpg` and the sample evidence/report support reproduction of that offline case.

## Public release

https://forge-relay-pearl.vercel.app serves the public discovery snapshot. Browser comparison returned cross-market proposals; unauthenticated health and catalog endpoints responded successfully. The live buyer status endpoint returned `connected: false` to a signed-out request. The frontend uses the official FRBL Labs wordmark, white background and relaxed heading spacing.

Python endpoint entry files now declare explicit handler subclasses so Vercel discovers the catalog, match, health and live routes. Production's configured origin matches the public hostname. The hosted OAuth device flow is implemented, but a full authenticated hosted hire has not been demonstrated; the real paid pilot used the separate local buyer integration.

## Real external pilot

See [pilot results](PILOT-RESULTS.md). A $0.50 NEAR task produced two inadequate deliveries. Citation checking and manual review rejected both. A refund dispute is under review as last confirmed on November 11, 2026. No external acceptance, successful refund or provider payout is claimed.

Artifact hashes check content identity, not independent truth or immutable provenance. The offline verifier checks fidelity to a captured snapshot; the live verifier checks minimum text length and citation presence. Human review remains necessary for factual accuracy and full brief compliance.

## A2A role mapping

The public UI now identifies requesting and provider agents as its customers, with humans supervising. Scout, Bench, Router, Sentinel and Commerce Router are intended responsibilities, not connected FLOP runtimes. Working evidence and planned capabilities are listed separately in the README and UI. No new autonomous dispatch, qualification, safety-policy engine or settlement capability was added by this presentation update.

## Public handoff explorer

`/handoff.html` reads the already-public `submission/sample-evidence.json` copy, with no external worker calls or payments. It renders requirements, actual worker sequence, failed checks, before/after citation fields, and the final recorded verification. Browser SHA-256 checking is limited to final artifact identity; use the offline verifier for full bundle and snapshot checks. The replay never records acceptance or claims live activity. It leaves the original pending-acceptance state intact.
