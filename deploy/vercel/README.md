# Isolated Vercel deployment

Public discovery: https://forge-relay-pearl.vercel.app.

Build with `python3 -B scripts/prepare_vercel.py --live`. Publish only the new allowlisted `build/vercel-*` package into a separate project. The package includes a filtered public catalog, the discovery frontend and optional buyer pilot. See [live setup](../../docs/LIVE-PILOT.md) for required private environment configuration. Secrets, session databases and authenticated job-board records must never enter the bundle.

The public discovery flow works without login; the buyer pilot requires its separately configured owner connection. A successful hosted buyer hire has not been demonstrated. Local offline reproduction remains free and independent of hosting.
