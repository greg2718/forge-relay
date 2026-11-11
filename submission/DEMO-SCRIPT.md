# Two-minute demo script — problem, differentiation and value

Purpose: explain why cross-market agent coordination matters, then use the working demo as evidence. Target 1:45–2:00 at a natural speaking pace. The narration distinguishes demonstrated behavior from intended economic value.

## Narration

An agent can be good at one task and still need help finishing the job. The right specialist may be in another marketplace. That creates a practical problem: how do you compare providers, hand off the work, and know whether the result meets the request?

In the catalogs we connected, capabilities, prices and evidence come in different forms. A listing is not a verified capability. A per-call price is not a complete-job quote. Finding a provider is only the beginning.

Our approach is to connect discovery across marketplaces with an explicit agreement about what a successful result must contain. We make the unknowns visible before work starts, then carry the task, evidence and acceptance criteria through the handoff.

Here, NEAR Agent Market supplies provider and pricing discovery, plus authenticated access to its public job board. This reproducible demo uses frozen listings from NEAR and two other sources.

Watch what happens when the returned artifact is missing a citation. Verification rejects it. A corrected version comes back, and acceptance is tied to that exact revision. These are local deterministic workers; no marketplace agent was hired and no funds moved.

The value we aim to create is larger than a comparison tool: buyers spend less effort coordinating specialists, capable agents can reach demand outside their home marketplace, and marketplaces can participate in work they could not fulfill alone.

Our next test is whether those connections turn more requests into accepted work. That is the business hypothesis. Today, we demonstrate the coordination and evidence trail needed to test it.

## Screen direction

| Time | Show | Purpose |
|---|---|---|
| 0–20 seconds | The task brief and acceptance requirements | Start with the buyer's problem, not a tour of buttons. |
| 20–40 seconds | Market intelligence: one NEAR listing and one other source; show pricing units and evidence | Make the comparison problem concrete. Use the frozen evidence labels. |
| 40–65 seconds | Return to Local handoff demo; show the requirements and click Run with the missing-citation fault selected | Explain the distinct approach: shared requirements and evidence across the handoff. |
| 65–90 seconds | Show FAIL → PASS, the returned report, then accept the verified revision locally | Provide observable proof of rejection, revision and exact-artifact acceptance. |
| 90–110 seconds | Hold on the accepted result and export controls | Explain the intended value to buyers, agents and marketplaces. |
| 110–120 seconds | End on the public repository URL | State the next business validation and invite inspection. |

Timing is approximate; follow the narration rather than rushing the interface. The flow runs quickly, so pause on the result while explaining the value.

## Recording setup

Start `python3 -m relay.server --demo --port 8766` and open http://127.0.0.1:8766/#demo. Use a fresh run. Keep unrelated tabs and account pages out of frame. Public repository: https://github.com/greg2718/forge-relay.

## Claim boundaries

- The differentiator is the combination of cross-market discovery, explicit uncertainty, task acceptance criteria, revision and evidence-bound acceptance. Do not claim no one else offers these features.
- Lower coordination cost, broader demand access and more completed work are intended benefits, not measured results. No conversion, revenue, quality or cost improvement has been established.
- The local flow verifies consistency with frozen source evidence. It does not establish provider trust, independent factual truth or marketplace buyer acceptance.
- NEAR discovery is implemented; onchain settlement, paid outcomes and autonomous external fulfillment are not.
- This script does not represent a recorded or published video. The local-only submission needs an actual video; the owner records and publishes the X post.
