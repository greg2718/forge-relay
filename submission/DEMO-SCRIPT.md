# Forge Relay demo script

Target length: about 2 minutes 30 seconds. Product: Forge Relay. Company: FRBL Labs. Record the public site and the free offline demo; use the sanitized pilot summary for the real case. Do not display account settings, tokens, private messages or billing pages. This is a recording script, not a completed video.

## Narration and screen sequence

### 0:00–0:25 The problem

Show the public task form at https://forge-relay-pearl.vercel.app.

“An agent may be capable of one part of a job and still need a specialist to finish it. That specialist may be listed in a different marketplace. Buyers face fragmented catalogs, incompatible prices, and capability claims that do not tell them whether the work will be usable.”

### 0:25–0:50 The approach

Click Compare providers with the default research-and-extraction brief. Show a cross-market proposal and its original listing links.

“Forge Relay, built by FRBL Labs, connects discovery across marketplaces to explicit delivery requirements. It compares candidates and shows what is still unknown: availability, full-job price, timing and whether providers can actually work together. This is a proposal, not an automatically executed purchase.”

### 0:50–1:20 Reproducible coordination

Switch to http://127.0.0.1:8766/#demo. Run the missing-citation example. Show FAIL, revision, PASS, then the exact-version local acceptance receipt. Do not click a real NEAR hire or acceptance control.

“Our reproducible demo sends the task through separate local extractor, writer and verifier processes. A missing citation fails the check. A corrected result passes, and the operator can accept that exact version. These workers are deterministic Python programs using frozen marketplace evidence. This sequence spends no money and does not represent independent marketplace agents.”

### 1:20–1:55 The real pilot

Show submission/PILOT-RESULTS.md, focused on the funding, delivery, verification and dispute rows. Label this screen ‘Real NEAR pilot — operator-reported evidence’.

“We also funded a real fifty-cent research task through NEAR Agent Market. NEAR supplied the provider, checkout, escrow and returned results. Both deliveries failed our citation check, and human review found the requested research missing. We requested corrections, then opened a full-refund dispute. At the last confirmed check, it remained under review. We did not accept the work, and we do not claim a refund or provider payout.”

### 1:55–2:25 Value and honest limits

Return to the cross-market proposal and finish on the public repository and app links.

“The value we aim to create goes beyond finding agents: buyers could coordinate specialists with less effort, providers could reach demand beyond their home marketplace, and delivery evidence could improve future selections. Our pilot proved a funded handoff, result inspection and rejection of missing evidence. It did not prove that cross-market matching produces more accepted work. That is our next measurable test.”

### 2:25–2:35 Closing

“Forge Relay: discover across markets, carry the requirements, inspect the result. Try the public demo or reproduce the offline workflow from our GitHub repository.”

## Recording checklist

- Confirm the published site loads and run one comparison before recording.
- Start the free local demo with `python3 -m relay.server --demo --port 8766`.
- Keep the local synthetic pass clearly separate from the real failed-delivery case.
- Recheck the dispute status before recording; change only the outcome sentence if a decision is confirmed.
- Never describe citation presence as factual truth, a proposal as a completed cross-market transaction, or a hash as a cryptographic attestation.
- Add captions and a closing frame with https://forge-relay-pearl.vercel.app and https://github.com/greg2718/forge-relay.
- Attach the recording, or screenshots of the hosted flow, to the owner's X demo post. The script itself is not the required demo post.
