# Blockchain demo

Standalone multi-terminal demo of the blockchain layer: a master and four agents, each its
own process and wallet, coordinating only through transactions and events on a local
Ganache chain. There are two ways to run it:

- **Automatic:** type `start` in the master terminal. It deploys and registers if needed,
  then the market runs on its own, like the simulator.
- **Step by step:** every action is a command you type in that node's terminal. Setup is
  `deploy`, then `register`, which sets up every agent's wallet.

Either way, the other terminals see every action through contract events.
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

This opens every node in its own Windows Terminal window, tiled over the screen:

```
| chain   | master  | robot_1 |
| robot_2 | human_1 | human_2 |
```

Each node runs in its own tmux session, so closing a window only detaches it: reopen it
with `tmux -L robopreneur-demo attach -t master` (or `chain`, `robot_1`, ...). Without
Windows Terminal it attaches in the current terminal; switch nodes with `Ctrl-b s`. Or start them
by hand in separate terminals from `demo/`: `npm run ganache`, `.venv/bin/python master.py`,
`.venv/bin/python agent.py robot_1` (and so on). Agent wallets are derived from `seed` + the
agent's name, so they are the same every run. Agent terminals wait for `deploy` and `register`, then show their prompt. Closing Ganache wipes the chain, so every run starts fresh:
`tmux -L robopreneur-demo kill-server` stops everything.

## Commands

Type `help` in any terminal. Tab completes command names.

| Terminal | Command | What it does (transaction) |
| --- | --- | --- |
| master | `deploy` | compile and deploy IECToken → AgentRegistry → ServiceRegistry → TaskEscrow; the master holds all 100 000 IEC |
| master | `register` | for every agent: send its wallet (derived from `seed`) 10 ETH for gas and its `initial_wealth` in IEC, then, signed with that wallet, `registerAgent`, `approve` the escrow and `registerService` for each of its services |
| master | `start` | `deploy` and `register` if not done yet, then run the market on its own (see below) |
| master | `stop` | pause: no new tasks or assignments; work in progress still finishes. `start` resumes |
| master | `fund <agent\|all> [amount]` | top up IEC (default: its `initial_wealth`) |
| master | `assign <task_id> <agent>` | `assignTask`: give an open task to an agent that offers the service |
| master | `requeue <task_id>` | `requeueTask`: take an assigned task back; the reward stays locked |
| agent | `create <service> <reward>` | `createTask`: post a task; the reward moves into escrow |
| agent | `complete <task_id>` | `completeTask`: mark a task assigned to me as done; it waits for its poster's confirmation |
| agent | `confirm <task_id>` | `confirmTask`: confirm the work on my own delivered task; the reward goes to the worker |
| agent | `cancel <task_id>` | `cancelTask`: withdraw my task while it's still open; full refund |
| all | `tasks` | list every task with its status (read-only) |
| all | `balances` | IEC and ETH of every wallet + escrow, and the total supply check (read-only) |
| all | `providers <service>` | who offers a service (read-only) |

## Automatic mode

`start` runs the market like the simulator (`../config.yaml`), with time in simulated
minutes (`auto.step_s` real seconds each, set in `demo_config.yaml`):

- **Tasks arrive on their own.** Each agent posts its own tasks: Poisson arrivals adding up
  to `auto.arrival_rate` tasks per hour. Each task is for a random service another agent
  offers (never `BatteryCharging`), with a reward drawn from that service's lognormal. An
  agent that can't afford the reward skips that task and logs a warning.
- **The master assigns FIFO.** It works through the open tasks oldest first and gives each
  to a random idle provider that isn't the task's poster. A task with no idle provider
  keeps its place in the queue.
- **Agents finish their work on their own.** The assignee works for the service's sampled
  duration, then sends `completeTask`. The poster then sends `confirmTask` right away.

Every step is still a transaction signed by its own wallet. `out/auto.json` only tells the
terminals that the mode is on. Manual commands keep working, but once `start` has run,
agents complete and confirm their work on their own. Use the step-by-step script below on
a chain where `start` hasn't been typed.

## Demo script (step by step)

| # | Terminal | Type | You'll see |
| --- | --- | --- | --- |
| 1 | master | `deploy` | 4 contracts deployed; agents wait for their wallet |
| 2 | master | `register` | each agent's wallet gets gas, IEC, its registration, escrow approval and services; agent terminals show their address and prompt |
| 3 | robot_1 | `create LabCleaning 150` | master: `providers: robot_2, human_1 → assign 1 robot_2`; providers see `I offer this` |
| 4 | master | `assign 1 human_1` | human_1: `assigned to me → complete 1`; robot_1: `my task #1 → human_1` |
| 5 | human_1 | `complete 1` | task delivered, reward still locked; robot_1: `delivered by human_1 → confirm 1` |
| 6 | human_1 | `confirm 1` | ✗ `not assigner`: only the task's poster can confirm |
| 7 | robot_1 | `confirm 1` | human_1 +150; robot_1, human_1 and master log the payment |
| 8 | robot_2 | `create BatteryCharging 400` | ✗ `insufficient balance` (it only has 300); nothing changes on-chain |
| 9 | master | `assign 1 human_2` | ✗ `task not open` (it's already completed): the contract enforces the rules |
| 10 | any | `balances` | master + agents + escrow = 100 000 IEC ✓ conserved |

Every transaction line shows its block, gas and hash. Every terminal is mirrored to
`out/logs/<node>.log`.

## Layout

| Path | What |
| --- | --- |
| `contracts/` | `IECToken`, `AgentRegistry`, `ServiceRegistry`, `TaskEscrow` (Solidity) |
| `master.py` | master terminal: `deploy`, `register`, `start`, `stop`, `fund`, `assign`, `requeue` |
| `agent.py` | agent terminal: `create`, `complete`, `confirm`, `cancel`; in automatic mode posts, completes and confirms on its own |
| `chain/auto.py` | automatic mode: Poisson arrivals, reward and duration sampling as in the simulator |
| `chain/node.py` | shared prompt + `tasks`, `balances`, `providers`; every `cmd_*` method is a command |
| `chain/client.py` | the only module that talks to the chain: deploy, sign and send, reverts → `TxReverted`, event listener thread |
| `chain/compile.py` | compiles the contracts with py-solc-x |
| `chain/wallets.py` | deterministic agent keys from seed + name (local demo only), address book |
| `chain/log.py` | coloured per-node terminal log |
| `chain/config.py` | paths and `demo_config.yaml` loading |
| `demo_config.yaml` | agents, their services, starting IEC, service rewards and durations, automatic-mode speed and arrival rate, chain settings |
| `start-demo.sh` | opens each node in its own terminal window |

