# Discovery sources and integration boundaries

| Source | Official public reference | Current integration |
|---|---|---|
| NEAR Agent Market | https://market.near.ai/discover/all | Public API: first 20 research and 20 data agents, deduplicated, with live default pricing-plan reads |
| Circle | https://agents.circle.com/services/exa | Two Exa endpoint listings, API services rather than agents |
| Taskmarket | https://taskmarket.dev/tasks?status=open | Public task cards; rewards and subcontract rights unconfirmed |
| TakoAPI | https://takoapi.com/api/registry?format=json | First 1,000 registry records; only HOSTED entries with supported capabilities retained |
| AgentMarket | https://www.agentmarket.trade/docs/agent-discovery | Free read-only search API, first 20 organic research agent/A2A results; demos excluded |
| Olas | https://marketplace.olas.network/gnosis/ai-agents | First-page public registry snapshot; not a verified hireable-Mech catalog |
| Agentverse | https://docs.agentverse.ai/v-1/api-reference/search/agents | Search probe returned HTTP 403; no integration represented as live |
| Virtuals ACP | https://github.com/Virtual-Protocol/acp-node | SDK browse endpoint probe returned HTTP 403; no integration represented as live |

All installed refresh adapters use fixed catalog GET URLs. User task text is compared locally and is never sent to these sources. Provider endpoints are recorded as untrusted metadata only; no requests are made to them. No SDK was installed, no wallet was connected, and no browser credentials were read. Optional project-agent authentication is entered privately through the local connection panel and used only for the fixed NEAR public job-board GET.

AgentMarket explicitly distinguishes discovery from execution and says unclaimed listings may be stale. Tako registry records may label paid-provider capabilities FREE; Relay preserves advertised pricing separately and leaves executable job cost unknown. Both sources add discovery, not assurance of successful paid fulfillment.

Research-only probes also read Olas's official mech-client query definitions. Its subgraph endpoint returned HTTP 403; the installed Olas adapter uses only the public registry page, with no RPC or GraphQL execution path.
