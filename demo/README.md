# Blockchain demo

Standalone multi-terminal demo of the blockchain layer: a master and four agents, each its
own process and wallet, coordinating only through transactions and events on a local
Ganache chain. **Nothing happens automatically.** Every action is a command you type in
that node's terminal, and the other terminals see it through contract events.
Design background: [../docs/blockchain-demo-plan.md](../docs/blockchain-demo-plan.md).
Nothing here is imported by the simulator.

## Setup (once)

Runs in bash under WSL (Ubuntu). Requires Node.js, Python 3.11+ with `venv`, and tmux
(`sudo apt install nodejs npm python3-venv tmux`). From `demo/`, inside WSL:

```bash
npm install
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

`node_modules/` and `.venv/` are platform-specific: if they were created from Windows,
delete them and run these steps again inside WSL.

`npm install` also installs a local **Node 20** (the `node` package) that `npm run ganache`
uses automatically. Ganache's native web server doesn't support newer Node versions. On
those it falls back to a slow server that stalls under load, so keep this dependency even
if your system Node is newer. The first `deploy` downloads solc 0.8.24 into `~/.solcx`.

## Start the terminals

```bash
./start-demo.sh        # from demo/, inside WSL
```

This opens a tmux session with every node in its own pane, tiled:

```
| chain   | master  | robot_1 |
| robot_2 | human_1 | human_2 |
```

Move between panes with `Ctrl-b` + arrow keys and zoom one with `Ctrl-b z`. Or start them
by hand in separate terminals from `demo/`: `npm run ganache`, `.venv/bin/python master.py`,
`.venv/bin/python agent.py robot_1` (and so on). Agents wait until the master has deployed,
then show their prompt. Closing Ganache wipes the chain, so every run starts fresh:
`tmux kill-session -t robopreneur-demo` stops everything.

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
| agent | `complete <task_id>` | `completeTask`: mark a task assigned to me as done; it waits for its poster's confirmation |
| agent | `confirm <task_id>` | `confirmTask`: confirm the work on my own delivered task; the reward goes to the worker |
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
| 6 | human_1 | `complete 1` | task delivered, reward still locked; robot_1: `delivered by human_1 → confirm 1` |
| 7 | human_1 | `confirm 1` | ✗ `not assigner`: only the task's poster can confirm |
| 8 | robot_1 | `confirm 1` | human_1 +150; robot_1, human_1 and master log the payment |
| 9 | robot_2 | `create BatteryCharging 400` | ✗ `insufficient balance` (it only has 300); nothing changes on-chain |
| 10 | master | `assign 1 human_2` | ✗ `task not open` (it's already completed): the contract enforces the rules |
| 11 | any | `balances` | master + agents + escrow = 100 000 IEC ✓ conserved |

Every transaction line shows its block, gas and hash. Every terminal is mirrored to
`out/logs/<node>.log`.

## Layout

| Path | What |
| --- | --- |
| `contracts/` | `IECToken`, `AgentRegistry`, `ServiceRegistry`, `TaskEscrow` (Solidity) |
| `master.py` | master terminal: `deploy`, `fund`, `assign`, `requeue` |
| `agent.py` | agent terminal: `register`, `approve`, `offer`, `create`, `complete`, `confirm`, `cancel` |
| `chain/node.py` | shared prompt + `tasks`, `balances`, `providers`; every `cmd_*` method is a command |
| `chain/client.py` | the only module that talks to the chain: deploy, sign and send, reverts → `TxReverted`, event listener thread |
| `chain/compile.py` | compiles the contracts with py-solc-x |
| `chain/wallets.py` | deterministic agent keys from seed + name (local demo only), address book |
| `chain/log.py` | coloured per-node terminal log |
| `chain/config.py` | paths and `demo_config.yaml` loading |
| `demo_config.yaml` | agents, their services, starting IEC, chain settings |
| `start-demo.sh` | opens each node in its own tmux pane |

