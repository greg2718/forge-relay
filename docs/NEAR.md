# Separate NEAR connection

Use a separate NEAR Agent Market account and project agent. Marketplace account handles, agent handles and blockchain payout accounts are different identifiers. Do not use a FLOP identity or credential.

1. In your NEAR builder form, retain Self-hosted and Draft. No price, funded job, wallet or webhook is needed for this discovery integration.
2. Use NEAR's **Save draft & get token** control. This creates a credential with broader worker authority than Relay uses; the user performs this step.
3. Copy the agent token directly into **NEAR connection** at http://127.0.0.1:8765 and select **Connect for job discovery**. Never paste it into chat or a tracked file.
4. A successful connection imports eligible public standard jobs from the first 50 recent board results. An empty board is valid and is not fabricated into demand. Refresh is manual.
5. Disconnect clears local memory only. Revoke the token through NEAR's agent Edit page when no longer needed. Restarting Relay also clears local authentication.

The local server accepts same-origin JSON only and stores no token in SQLite, environment files or browser storage. It never reads browser cookies or wallet secrets. Its outbound credential-bearing request is limited to `GET https://market.near.ai/v1/jobs/board?kind=standard&sort=recent&limit=50&offset=0`. Public catalog and pricing reads do not use the token. A successful read confirms access, not independent ownership of the expected agent.

Discovery is not permission to subcontract. Before any real fulfillment, establish scope, buyer permission, provider terms, acceptance criteria and separate execution authorization. Spending remains disabled.

Official references: [self-hosted agents](https://docs.market.near.ai/guides/self-hosted-agents), [worker tools](https://docs.market.near.ai/mcp/worker-tools), [OpenAPI schema](https://market.near.ai/openapi.json).
