# Blockchain demo

Standalone multi-terminal demo of the blockchain layer: a master and four agents, each its
own process and wallet, coordinating only through transactions and events on a local
Ganache chain. **Nothing happens automatically.** Every action is a command you type in
that node's terminal, and the other terminals see it through contract events.
Design background: [../docs/blockchain-demo-plan.md](../docs/blockchain-demo-plan.md).
Nothing here is imported by the simulator.

## Setup (once)

Requires Node.js and Python 3.11+. From `demo/`:

```bash
npm install
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

`npm install` also installs a local **Node 20** (the `node` package) that `npm run ganache`
uses automatically. Ganache's native web server doesn't support newer Node versions. On
those it falls back to a slow server that stalls under load, so keep this dependency even
if your system Node is newer. The first `deploy` downloads solc 0.8.24 into `~/.solcx`.

## Start the terminals

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1        # from demo/
```

This opens every node in its own window (move and resize them freely), starting tiled:

```
| chain   | master  | robot_1 |
| robot_2 | human_1 | human_2 |
```

Or start them by hand from `demo/`: `npm run ganache`, `.venv/Scripts/python master.py`,
`.venv/Scripts/python agent.py robot_1` (and so on). Agents wait until the master has
deployed, then show their prompt. Closing Ganache wipes the chain, so every run starts fresh.

## Commands

Type `help` in any terminal. Tab completes command names.

| Terminal | Command | What it does (transaction) |
| --- | --- | --- |
| master | `deploy` | compile and deploy IECToken → AgentRegistry → ServiceRegistry → TaskEscrow; the master holds all 100 000 IEC |
| master | `fund <agent\|all> [amount]` | send 10 ETH for gas (if the agent has none) and IEC (default: its `initial_wealth`) |
| master | `assign <task_id> <agent>` | `assignTask`: give an open task to an agent that offers the service |
| master | `requeue <task_id>` | `requeueTask`: take an assigned task back; the reward stays locked |
| agent | `register` | `registerAgent`: join the market |
| agent | `approve` | `approve`: allow the escrow to lock rewards from this wallet |
| agent | `offer [service]` | `registerService`: list one or all of the agent's services |
| agent | `create <service> <reward>` | `createTask`: post a task; the reward moves into escrow |
| agent | `complete <task_id>` | `completeTask`: finish a task assigned to me; I get the reward |
| agent | `cancel <task_id>` | `cancelTask`: withdraw my task while it's still open; full refund |
| all | `tasks` | list every task with its status (read-only) |
| all | `balances` | IEC and ETH of every wallet + escrow, and the total supply check (read-only) |
| all | `providers <service>` | who offers a service (read-only) |

## Demo script

| # | Terminal | Type | You'll see |
| --- | --- | --- | --- |
| 1 | master | `deploy` | 4 contracts deployed; agents print `ready` |
| 2 | master | `fund all` | each agent logs `received … IEC from the master` |
| 3 | each agent | `register`, `approve`, `offer` | master logs who joined and what they offer |
| 4 | robot_1 | `create LabCleaning 150` | master: `providers: human_1, robot_2 → assign 1 human_1`; providers see `I offer this` |
| 5 | master | `assign 1 human_1` | human_1: `assigned to me → complete 1`; robot_1: `my task #1 → human_1` |
| 6 | human_1 | `complete 1` | human_1 +150, robot_1 and master log the payment |
| 7 | robot_2 | `create BatteryCharging 400` | ✗ `insufficient balance` (it only has 300); nothing changes on-chain |
| 8 | master | `assign 1 human_2` | ✗ `task not open` (it's already completed): the contract enforces the rules |
| 9 | any | `balances` | master + agents + escrow = 100 000 IEC ✓ conserved |

Every transaction line shows its block, gas and hash. Every terminal is mirrored to
`out/logs/<node>.log`.

## Layout

| Path | What |
| --- | --- |
| `contracts/` | `IECToken`, `AgentRegistry`, `ServiceRegistry`, `TaskEscrow` (Solidity) |
| `master.py` | master terminal: `deploy`, `fund`, `assign`, `requeue` |
| `agent.py` | agent terminal: `register`, `approve`, `offer`, `create`, `complete`, `cancel` |
| `chain/node.py` | shared prompt + `tasks`, `balances`, `providers`; every `cmd_*` method is a command |
| `chain/client.py` | the only module that talks to the chain: deploy, sign and send, reverts → `TxReverted`, event listener thread |
| `chain/compile.py` | compiles the contracts with py-solc-x |
| `chain/wallets.py` | deterministic agent keys from seed + name (local demo only), address book |
| `chain/log.py` | coloured per-node terminal log |
| `chain/config.py` | paths and `demo_config.yaml` loading |
| `demo_config.yaml` | agents, their services, starting IEC, chain settings |
| `start-demo.ps1` | opens each node in its own Windows Terminal window |

