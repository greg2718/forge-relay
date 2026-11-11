# Live buyer pilot

The separate live pilot connects cross-market discovery to NEAR's buyer checkout, job tracking and artifact review. It does not use the FLOP runtime or credentials. Other marketplaces remain discovery and proposal sources; cross-market paid execution is not yet implemented.

## Behavior

1. Open a candidate from discovery and check its current NEAR price, payment rails, availability, required services and description.
2. Connect a buyer identity through NEAR OAuth with PKCE. A worker's agent token cannot hire other agents.
3. Prepare one task with a stable random request ID. `prepare_job` creates a draft without payment; retries reuse the same ID.
4. Inspect NEAR's exact checkout and funding fees. Payment is an operator action on NEAR. No `create_job` or automatic payment tool is exposed.
5. Refresh the saved task after checkout. NEAR's funded job ID and subsequent status are retained in durable storage.
6. Retrieve the provider's delivered text and record its digest, version and assignment. Automated verification checks minimum content and three citation links, not factual correctness.
7. After reviewing the artifact, request the NEAR acceptance page. FORGE refreshes the result and rejects a changed digest/version/assignment or failed checks. Acceptance releases escrow on NEAR. Only marketplace completion is reported as completed.

One pilot per configured buyer is supported. A pending or uncertain request is never replaced automatically. External-link deliverables require review on NEAR and are not claimed as verified by FORGE. Large artifacts are refused rather than truncated into a misleading verification result.

## Local setup

Run `python3 -B -m relay.live_server` on 127.0.0.1:8767. This is separate from the existing discovery server at 8765 and offline demo at 8766.

Register a public OAuth client at NEAR's documented registration endpoint with callback `http://127.0.0.1:8767/api/live/callback`. Keep the registration response in ignored `data/live/oauth-client.json`, mode 0600. The server stores private session data in the separate `data/live/state.sqlite3`. Never publish either file. Local default pilot owner is `frbl`; set `FORGE_OWNER` to the actual buyer handle for a different installation.

OAuth access expires within one hour. Reconnect to resume the saved pilot. Disconnect removes the local session; revoking the marketplace grant is a separate action in NEAR Connections. The connection grants broader marketplace permissions than the application uses; the server only exposes its explicit buyer-tool allowlist.

## Vercel package

Run `python3 -B scripts/prepare_vercel.py --live`. Deploy only the resulting allowlisted `build/vercel-*` folder into the dedicated FORGE project and team. The original repository, local databases, credentials, authenticated board records and unrelated sources are not deployment inputs.

Hosted configuration requires `FORGE_ORIGIN`, `FORGE_OAUTH_CLIENT_ID`, `FORGE_OWNER`, `UPSTASH_REDIS_REST_URL`, and `UPSTASH_REDIS_REST_TOKEN` (the Vercel integration’s `KV_REST_API_URL` and `KV_REST_API_TOKEN` names are also accepted). NEAR currently rejects arbitrary hosted redirect domains. The hosted app therefore uses NEAR's advertised OAuth device authorization flow: open the verification link, check the displayed code, authorize as the buyer, and press Check approved connection. The local app continues using a loopback PKCE callback. Register a separate public client for the hosted installation; do not claim its hosted callback is allowlisted. Redis must be a separate free-plan FORGE database. Configure the token as a sensitive production-only variable. Never use a FLOP or frbl.ai store.

Hosted state uses atomic Redis compare-and-swap. Missing configuration fails closed; a serverless filesystem or process-memory fallback is deliberately unavailable. Job state expires after 30 days; this pilot is not a long-term records archive.

## Verification and publication

The test suite exercises draft-to-funded-to-result-to-review behavior with fixtures, idempotent retries after timeout, quote ceilings, access boundaries, CSRF, OAuth state replay, exact artifact review, storage atomicity, and the absence of automatic paid tool calls. Passing fixture tests does not prove the live provider has been hired or delivered work.

Before publishing a result, record the actual provider, complete charge including fees, job URL, returned artifact digest, buyer acceptance and any unsupported claims. Do not include OAuth tokens, registration responses, financial details or private buyer briefs in the public repository.

## Observed pilot outcome

The first live task was funded and produced two artifacts that failed review. Correction and dispute actions were performed by an operator in NEAR, not by the application. The latest confirmed dispute is pending. See [pilot evidence](../submission/PILOT-RESULTS.md). The public host is https://forge-relay-pearl.vercel.app; configured origin must match it. Hosted authentication is not claimed as fully exercised by that local pilot.
