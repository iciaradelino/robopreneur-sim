# Blockchain demo

Standalone multi-terminal demo of the blockchain layer: agents and a master node, each its
own process, coordinating only through transactions and events on a local Ganache chain.
Plan and design: [../docs/blockchain-demo-plan.md](../docs/blockchain-demo-plan.md).
Nothing here is imported by the simulator.

## Setup (once)

Requires Node.js (LTS or newer) and Python 3.11+. From `demo/`:

```bash
npm install
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

The first compile downloads solc 0.8.24 into `~/.solcx`.

## Run the contract smoke test

Terminal 1, the local chain (fresh and empty every time it starts):

```bash
npm run ganache
```

On Node 22+, Ganache prints `Cannot find module '../binaries/uws_win32_x64_...node'`.
That's harmless: it falls back to a pure-JS server and keeps going until
`RPC Listening on 127.0.0.1:8545`.

Terminal 2:

```bash
.venv/Scripts/python smoke_test.py
```

The test compiles and deploys the 4 contracts, funds agents from the master, runs a
completed, a failed and a cancelled task, checks every revert rule, and checks that
master + agents + escrow always equals the total supply.

## Layout

| Path | What |
| --- | --- |
| `contracts/` | `IECToken`, `AgentRegistry`, `ServiceRegistry`, `TaskEscrow` (Solidity) |
| `chain/compile.py` | compiles the contracts → `out/compiled.json` (`python -m chain.compile`) |
| `chain/wallets.py` | deterministic agent keys from seed + name (local demo only) |
| `demo_config.yaml` | agents, services, wealth, chain settings |
| `smoke_test.py` | end-to-end contract check against a running Ganache |
