# Execution and verification evidence

The tested story is: browser Run action → loopback demo endpoint → fixed local extractor process → fixed writer process → returned artifact → fixed verifier process → explicit fault rejection → writer revision → verifier pass → operator acceptance of the exact hash.

- 57 automated tests passed, including real subprocess handoffs, negative citation/price/duplicate cases, event/handoff tampering, exact-revision acceptance, idempotent acceptance, HTTP origin boundaries and refusal of network/credential routes in offline mode.
- Browser verified the run result `FAIL → PASS`, a six-provider report across NEAR/TakoAPI/AgentMarket, and a local acceptance receipt.
- Screenshot: `local-demo.jpg`. It shows a verified returned artifact and acceptance receipt; it is supporting evidence, not the required demo video.
- Offline mode uses a separate `data/offline_demo` database. The separate live NEAR session is not restarted or copied.
- Worker programs receive JSON over stdin and return JSON over stdout. Their executable and role are fixed; no model API, marketplace endpoint or supplied code is executed. Separate processes are not represented as a security sandbox for arbitrary code.
- The demo source snapshot contains public listing facts and original source hashes. Live source truth is not revalidated during the offline run.
- Event and artifact hashes provide integrity checks, not cryptographic identities or immutable onchain attestations.
- No payment, wallet signature, public posting, repository publication or hackathon submission occurred.

The existing FORGE fixture rehearsal remains synthetic and separate. The new executable local handoff log records actual local work without changing the vendored simulation-only engine.
