# Blockchain demo

Standalone multi-terminal demo of the blockchain layer: a master and four agents, each its
own process and wallet, coordinating only through transactions and events on a local
Ganache chain.

Tasks live in an on-chain registry (`TaskManager`), so every task and every step of its life
(posted, assigned to whom at what price, delivered, paid) is an immutable, traceable record.
Assignment happens on-chain too, following the logic of RODEO's
[`Organization.sol`](https://github.com/IERoboticsAILab/RODEO/blob/main/blockchain-network/smart-contracts/contracts/Organization.sol):
**as soon as a task is registered, the `Organization` contract assigns it in the same
transaction** (see [On-chain assignment](#on-chain-assignment)). Nobody picks assignees by hand.

There are two ways to run it:

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
| master | `deploy` | compile and deploy IECToken → AgentRegistry → ServiceRegistry → TaskManager → Organization and wire the Organization to the other two; the master holds all 100 000 IEC and owns the Organization |
| master | `register` | for every agent: send its wallet (derived from `seed`) 10 ETH for gas and its `initial_wealth` in IEC, then, signed with that wallet, `registerAgent`, `approve` the TaskManager and `registerService` for each of its services at its price |
| master | `start` | `deploy` and `register` if not done yet, then run the market on its own (see below) |
| master | `stop` | pause: no new tasks arrive; work in progress still finishes and frees providers pick up waiting tasks. `start` resumes |
| master | `fund <agent\|all> [amount]` | top up IEC (default: its `initial_wealth`) |
| master | `requeue <task_id>` | `Organization.unassignTask`: take a task back from its provider; the contract gives it to another provider (never the same one) or queues it, and the freed provider picks up the best waiting task |
| agent | `create <service> <reward>` | `createTask`: register a task with a maximum reward; the reward moves into escrow and the Organization assigns the task in the same transaction (or queues it) |
| agent | `complete <task_id>` | `completeTask`: mark a task assigned to me as done; I'm free at once (and may get a waiting task in the same transaction), the money waits for its poster's confirmation |
| agent | `confirm <task_id>` | `confirmTask`: confirm the work on my own delivered task; the worker gets its price, I get the rest of the reward back |
| agent | `cancel <task_id>` | `cancelTask`: withdraw my task while it's still open; full refund |
| all | `tasks` | list every task in the registry with its status, assignee and price (read-only) |
| all | `balances` | IEC and ETH of every wallet, including the TaskManager (the rewards it holds in escrow), and the total supply check (read-only) |
| all | `providers <service>` | who offers a service, at what price, and who is busy (read-only) |

## On-chain assignment

`contracts/Organization.sol` is adapted from RODEO's `Organization.sol`: `TaskManager` plays
its TaskManager and `ServiceRegistry` its ServiceManager. Each agent lists its services with
a price (`agents.<name>.services` in `demo_config.yaml`). The contract assigns at three moments:

| When | Organization.sol | What happens |
| --- | --- | --- |
| a task is registered (`createTask`) | `onTaskRegistered` → `assignTask` | the task goes to the **cheapest idle provider** whose offer matches its category and service with `price <= reward`. If there is none it waits in the contract's queue (`TaskQueued` event) |
| a provider is free again (`completeTask`, `requeue`) | `onTaskComplete` → `tryAssignTaskForService` | the provider gets the **waiting task with the highest reward** it can do (oldest first on a tie) |
| a provider lists a service (`registerService`) | `onServiceRegistered` | same as above |

The reward is the poster's budget: on `confirm` the worker is paid its price and the rest goes
back to the poster. A task whose reward is below every provider's price waits until its
poster cancels it. Differences from RODEO: busy is per agent rather than per service (an agent
does one job at a time), a poster never gets its own task, and the contract keeps a queue of
waiting tasks instead of scanning every task ever registered.

## Automatic mode

`start` runs the market like the simulator (`../config.yaml`), with time in simulated
minutes (`auto.step_s` real seconds each, set in `demo_config.yaml`):

- **Tasks arrive on their own.** Each agent posts its own tasks: Poisson arrivals adding up
  to `auto.arrival_rate` tasks per hour. Each task is for a random service another agent
  offers (never `BatteryCharging`), with a reward drawn from that service's lognormal. An
  agent that can't afford the reward skips that task and logs a warning.
- **The Organization contract assigns them on registration**, by the rules in
  [On-chain assignment](#on-chain-assignment). The master only watches.
- **Agents finish their work on their own.** The assignee works for the service's sampled
  duration, then sends `completeTask`, which can hand it its next waiting task in the same
  transaction. The poster then sends `confirmTask` right away.

Every step is still a transaction signed by its own wallet. `out/auto.json` only tells the
terminals that the mode is on. Manual commands keep working, but once `start` has run,
agents complete and confirm their work on their own. Use the step-by-step script below on
a chain where `start` hasn't been typed.

## Demo script (step by step)

| # | Terminal | Type | You'll see |
| --- | --- | --- | --- |
| 1 | master | `deploy` | 5 contracts deployed and wired; agents wait for their wallet |
| 2 | master | `register` | each agent's wallet gets gas, IEC, its registration, TaskManager approval and priced services; agent terminals show their address and prompt |
| 3 | robot_1 | `create LabCleaning 150` | same transaction: `assigned to robot_2 at 95.00 IEC` (the cheapest of robot_2 95, human_1 125; robot_1 never gets its own task); robot_2: `→ complete 1` |
| 4 | human_2 | `create LabCleaning 100` | `no idle provider at that price yet · waiting in the queue`: robot_2 is busy, robot_1 (110) and human_1 (125) cost more than 100 |
| 5 | robot_2 | `complete 1` | robot_2 is free, so in the same transaction the contract gives it the waiting task #2; robot_1: `→ confirm 1` |
| 6 | robot_2 | `confirm 1` | ✗ `not assigner`: only the task's poster can confirm |
| 7 | robot_1 | `confirm 1` | robot_2 +95, and 55 back to robot_1 |
| 8 | master | `requeue 2` | task #2 taken back from robot_2; nobody else does it for 100, so it waits again |
| 9 | human_2 | `cancel 2` | full refund of the 100 |
| 10 | robot_2 | `create BatteryCharging 400` | ✗ `insufficient balance` (it has 395); nothing changes on-chain |
| 11 | any | `tasks`, `balances` | the registry's history of both tasks; master + agents + taskmanager = 100 000 IEC ✓ conserved |

Every transaction line shows its block, gas and hash. Every terminal is mirrored to
`out/logs/<node>.log`.

## Layout

| Path | What |
| --- | --- |
| `contracts/` | `IECToken`, `AgentRegistry`, `ServiceRegistry` (offers + prices), `TaskManager` (the task registry), `Organization` (on-chain assignment) (Solidity) |
| `master.py` | master terminal: `deploy`, `register`, `start`, `stop`, `fund`, `requeue`; logs the assignments the contract makes |
| `agent.py` | agent terminal: `create`, `complete`, `confirm`, `cancel`; in automatic mode posts, completes and confirms on its own |
| `chain/auto.py` | automatic mode: Poisson arrivals, reward and duration sampling as in the simulator |
| `chain/node.py` | shared prompt + `tasks`, `balances`, `providers`; every `cmd_*` method is a command |
| `chain/client.py` | the only module that talks to the chain: deploy, sign and send, reverts → `TxReverted`, event listener thread |
| `chain/compile.py` | compiles the contracts with py-solc-x |
| `chain/wallets.py` | deterministic agent keys from seed + name (local demo only), address book |
| `chain/log.py` | coloured per-node terminal log |
| `chain/config.py` | paths and `demo_config.yaml` loading |
| `demo_config.yaml` | agents, their services and prices, starting IEC, service rewards and durations, automatic-mode speed and arrival rate, chain settings |
| `start-demo.sh` | opens each node in its own terminal window |

