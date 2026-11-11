# 90-second recording script

Record the browser at http://127.0.0.1:8766/#demo after starting `python3 -m relay.server --demo --port 8766`. Use a fresh run. Keep unrelated tabs, passwords and account pages out of frame. This is a script, not a completed recording.

| Time | Action | Suggested narration |
|---|---|---|
| 0–12 seconds | Show the task and acceptance requirements | “FORGE Relay compares agent marketplaces before work or money is committed. This demo asks for a cited comparison of research and extraction providers.” |
| 12–25 seconds | Briefly show Market intelligence, then return to Local handoff demo | “These are frozen public listings from NEAR Agent Market, TakoAPI and AgentMarket. Our live integration can also read NEAR pricing and buyer jobs. Frozen evidence makes this demo reproducible without keys.” |
| 25–40 seconds | Leave the citation-fault checkbox on and click Run | “The task passes through separate local extractor, writer and verifier processes. These are deterministic demo workers, not agents hired from those marketplaces.” |
| 40–55 seconds | Show FAIL → PASS and the event sequence | “We deliberately remove one citation. The verifier rejects that artifact, requests a revision, and checks the corrected version against the frozen evidence.” |
| 55–72 seconds | Show the returned report and expand acceptance checks | “The report compares six providers across three markets. Price units, observation dates and uncertainty stay visible. This verifies evidence consistency, not provider quality.” |
| 72–85 seconds | Click Accept this verified revision locally | “Acceptance is pinned to this exact artifact hash. The receipt and full handoff bundle can be exported. No external provider was contacted and no funds moved.” |
| 85–90 seconds | Show the export controls | “Next is authorized external fulfillment and settlement. Today the coordination and verification flow runs locally, with a reproducible public repository.” |

If the repository is not yet public, replace the last phrase with “with a repository prepared for publication.” Do not claim payment, independent provider collaboration, autonomous LLM research, or NEAR settlement.

A screenshot is included as supporting evidence, but local-only submission requires the actual video. The owner records and publishes the demo post.
