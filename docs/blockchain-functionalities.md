# Blockchain & Web3 functionalities

What the blockchain layer will do inside the simulator, concept by concept, and why each
decision was made. Written for someone new to blockchain.

---

## 0 · Blockchain in 2 minutes

| Term | Plain meaning | In our simulator |
| --- | --- | --- |
| **Blockchain / ledger** | A shared notebook of every money movement and important action. Pages can only be added, never edited or torn out. | Replaces the floating `wealth` numbers with a history everyone can check. |
| **Block** | One page of that notebook — a batch of actions recorded together. | Ganache mines **one block per transaction**, instantly. The block's timestamp tells us the simulation step (D2). |
| **Ganache** | A personal Ethereum blockchain that runs on your own computer. Free, instant, no internet, comes with pre-funded test accounts. | Started fresh by the simulator for every run. |
| **ETH (test ether)** | Ethereum's own currency, needed to pay gas. On Ganache it's free play money. | Only used to pay gas. Separate from IEC. |
| **Wallet** | An account: an *address* (like an IBAN, public) + a *private key* (like a PIN, secret, used to sign). | Every human and robot gets one. |
| **Token** | The money that lives on the chain. | `IEC` — the currency already used in `config.yaml` (`initial_wealth: 2000 # IEC`). |
| **Transaction** | A signed request to change something on the chain ("send 120 IEC to X", "create task"). | Every money move or task state change. |
| **Smart contract** | A small program stored on the chain. Nobody can change its rules once deployed, and it can hold money itself. | The rules of our marketplace: registries + task escrow. |
| **Escrow** | Money parked with a neutral third party until a job is done. | The contract holds the reward while a task is in progress. |
| **Event** | A public announcement a contract makes ("task 42 completed"). Cheap to emit, easy to listen to. | Feeds metrics, dashboard and CSV logs. |
| **Gas** | The fee paid to the network for running a transaction, paid in ETH. | Paid with Ganache test ETH, recorded per transaction; never touches IEC (D6). |
| **Oracle** | Someone who tells the chain about the real world. The chain can't "see" if a robot actually cleaned the lab. | The simulator itself reports task outcomes. |
| **On-chain / off-chain** | Stored on the blockchain vs. stored in normal program memory. | Money + agreements on-chain; movement, battery, physics off-chain. |

---

## 1 · The big picture

Today, the economy of the simulator is one function:

```python
# economy.py
assigner.wealth -= task.reward
assignee.wealth += task.reward
```

It runs only when a task succeeds, it doesn't check whether the assigner can pay, and
nothing remembers that it happened.

With the blockchain layer, the economy becomes a **small, rule-bound marketplace**:

1. Every agent has a **wallet** holding **IEC tokens**.
2. Agents **register** on-chain, and so do the **services** they offer.
3. When someone needs a task done, they **lock the reward in escrow** at creation.
4. When the task finishes, the contract **pays the worker** (success) or **refunds the
   requester** (failure).
5. Every step of this is a **transaction**, and each produces **events** we can analyse.

**What stays exactly as it is:** movement, floor plan, battery physics, schedules, phases
and waypoints, failure probability, and the matching logic of *who* gets a task. The
blockchain records and enforces the *economic agreements*; it does not run the robots.

> **Why this split?** On a real blockchain, every computation costs gas and every byte stored
> is expensive. Running path-finding or battery drain on-chain would be absurdly costly and
> slow. Real-world projects (robot fleets, delivery networks) do exactly this: physical
> operations off-chain, payments and agreements on-chain.

---

## 2 · The six concepts

### 2.1 Agent

**What it is today:** a `HumanAgent` or `RobotAgent` object with an `agent_id` string
(`robot_1_0`) and a `wealth` float.

**What it becomes:** the same Python object, plus an **on-chain identity**.

| On-chain (AgentRegistry contract) | Off-chain (stays in `agents.py`) |
| --- | --- |
| wallet address | position, speed, target location |
| `agent_id` (`robot_1_0`) | battery, charging state |
| agent kind: `human` / `robot` | schedule, status (`idle`/`exec`/…) |
| registration step | current task phase / dwell timer |
| `active` flag | random walk counters |

**Functionalities**
- `registerAgent(agent_id, kind)` — called once at initialization, from the agent's wallet.
- `isRegistered(address)` — contracts check this before letting anyone create or take tasks.
- `deactivate(address)` — optional, for later (an agent leaves the market).

> **Why register agents at all?** So the contracts can refuse actions from unknown
> addresses. It's the "membership list" of the marketplace. It also lets us tell humans and
> robots apart on-chain (useful for metrics like *how much money flows robot → human*).

---

### 2.2 Wallet

**What it is today:** doesn't exist — `wealth` is a plain number on the agent.

**What it becomes:** a `Wallet` object attached to every agent.

```
Wallet
  address       – public, unique (e.g. 0x3f…a1)
  private_key   – secret, used to sign transactions (only the agent knows it)
  balance()     – reads IEC balance from the token contract (not stored locally!)
  nonce         – counter of transactions sent (prevents replaying the same tx twice)
```

A wallet holds **two currencies**: **IEC** (the market's money, what agents earn and
spend) and a little **test ETH** (only to pay gas — see D6).

**Functionalities**
- **Create** one wallet per agent at initialization.
- **Fund** it: the token contract mints `initial_wealth` IEC into each wallet.
- **Sign and send** transactions on behalf of the agent.
- **Read balance** — `agent.wealth` becomes a read of the wallet balance, so `metrics.py`
  (Gini, system wealth) keeps working unchanged.

> **Why is balance read from the chain and not stored on the agent?** Single source of truth.
> If the agent kept its own copy, the two could drift apart. On a blockchain, the
> balance *is* whatever the ledger says.

> **Why one wallet per agent and not per agent type?** Each robot earns and spends
> independently — that's the whole point of a "robopreneur". Wealth inequality (Gini) is
> measured per agent, so the wallet must be per agent too.

---

### 2.3 Servicio (Service)

**What it is today:** each agent holds a private list of `Service(name, category, skill)`.
To find who can do a task, `_get_eligible_agents` loops over every agent.

**What it becomes:** a public **ServiceRegistry** — a catalogue of *who offers what*.

| Stored on-chain per offer | Example |
| --- | --- |
| provider address | `0x3f…a1` (robot_1_0) |
| service name | `LabCleaning` |
| category | `cleaning` |
| skill (0–1, stored as integer 0–1000) | `950` |
| active | `true` |

The service *definitions* (reward median, phases, waypoints, durations) stay in
`config.yaml` — they describe the physical job, not the agreement.

**Functionalities**
- `registerService(name, category, skill)` — each agent registers each service it offers at
  init.
- `getProviders(name)` — list of addresses offering a service. The off-chain matcher reads
  this, then filters by the off-chain conditions (idle, battery, schedule).
- `deactivateService(name)` — optional, for later (e.g. a robot stops offering a service).

> **Why store skill as an integer?** Blockchains (Solidity) have no decimal numbers. The
> standard trick is to scale: `0.95 → 950`.

> **Why a registry instead of each agent's list?** It's the "yellow pages" of the
> marketplace — anyone can check who offers what, and a task can only be assigned to an
> address that actually registered that service. That check is enforced by the contract,
> not just trusted from Python.

---

### 2.4 Tarea (Task)

**What it is today:** a `Task` object with lifecycle `pending → in_progress →
completed | failed`, and the reward is paid only at the end, without checking funds.

**What it becomes:** a **job agreement** inside a **TaskEscrow** contract. The Python `Task`
object still exists (it holds waypoints, phase timers etc.) and gets a `chain_task_id`
linking it to its on-chain twin.

```mermaid
stateDiagram-v2
  direction LR
  [*] --> Open : createTask\n(assigner locks reward)
  Open --> Assigned : assignTask\n(assignee chosen)
  Assigned --> Open : requeueTask\n(interrupted: schedule / low battery)
  Assigned --> Completed : completeTask\n(reward → assignee)
  Assigned --> Failed : failTask\n(reward → back to assigner)
  Open --> Cancelled : cancelTask\n(reward → back to assigner)
  Completed --> [*]
  Failed --> [*]
  Cancelled --> [*]
```

| On-chain (TaskEscrow) | Off-chain (Python `Task`) |
| --- | --- |
| chain task id | resolved waypoints, phase index, dwell timers |
| assigner address, assignee address | location, durations |
| service name | agent skill used for fail roll |
| reward amount (locked) | |
| status | |
| created / assigned / closed time (→ simulation step) | |

#### 2.4.1 · What is escrow, and why does it need the amount at creation?

**Escrow = a neutral middle-man holds the money until the job is done.**
You already know it from everyday life:
- **Airbnb:** you pay when you *book*. Airbnb holds the money and only releases it to the
  host after you check in. If the booking is cancelled, you get it back.
- **Wallapop / Vinted protected payment:** the buyer pays, the platform holds the money,
  the seller gets it only when the buyer confirms the item arrived.

In our simulator the middle-man is the **TaskEscrow smart contract**. Since it's code on a
blockchain, nobody — not the assigner, not the worker, not even us — can take the money
out except by following its rules (complete → worker, fail/cancel → back to assigner).

**Why does it need the amount when the task is created, not when it's assigned?**

1. **You can't lock money if you don't know how much.** Locking *is* the creation step:
   "I post this job and put 140 IEC on the table".
2. **Otherwise the promise could be empty.** If we only charged at assignment, between
   creation and assignment the assigner keeps spending on other tasks. By the time a
   worker is found, the money might be gone. Today that's exactly what happens — and the
   assigner just goes negative, which a real currency can't do.
3. **Every task in the queue is guaranteed to be paid.** The task queue becomes a list of
   *fully funded* job offers. A worker who accepts one never works for nothing.
4. **The worker sees the price before accepting** — like a job posting that shows the
   salary. That also opens the door to future features (e.g. agents choosing tasks by
   reward).
5. **There's one clear moment to check "can you afford this?"** — at creation. If not,
   the task is simply never posted (D7), instead of hanging in the queue with no money
   behind it.

In the current code the reward doesn't depend on *who* does the task (`sample_reward` only
uses the service's config), so moving the draw from assignment to creation doesn't change
its meaning — only *when* it is drawn.

```
creation        assignment         execution              end
   │                │                  │                   │
assigner ──140──▶ [ ESCROW holds 140 ] ─────────────────▶ success: 140 → worker
                                                          failure: 140 → assigner
```

**Functionalities**
- `createTask(service, reward)` — sent by the **assigner**. Moves `reward` IEC from the
  assigner's wallet into the contract. **Fails if the assigner can't afford it.**
- `assignTask(taskId, assignee)` — sent by the **operator** (see D3). Checks the assignee is
  registered and offers that service.
- `requeueTask(taskId)` — operator; back to `Open`, money stays locked.
- `completeTask(taskId)` — operator (oracle); releases the reward to the assignee.
- `failTask(taskId)` — operator (oracle); refunds the assigner.
- `cancelTask(taskId)` — assigner; only while `Open`, full refund. (Not used by the sim at
  first, but a real marketplace needs it.)

> **Why lock the money at creation (escrow)?** It solves two problems of the current model:
> (1) the assigner can no longer go into negative wealth, and (2) the worker knows the
> money is guaranteed before starting. This is the classic use-case of smart contracts.

---

### 2.5 Transaction

**What it is today:** doesn't exist.

**What it becomes:** every action that changes on-chain state is a transaction, and the
simulator keeps the full list.

```
Transaction
  tx_hash       – unique id
  block         – Ganache block it was mined in (one per transaction)
  step          – simulation step, from the block timestamp (D2)
  sender        – wallet address that signed it
  contract      – Token / AgentRegistry / ServiceRegistry / TaskEscrow
  function      – e.g. createTask
  args          – e.g. {service: "LabCleaning", reward: 140}
  value_moved   – IEC moved (0 if none)
  gas_used      – real gas used, from the receipt (paid in test ETH, D6)
  status        – success / reverted (+ reason, e.g. "insufficient balance")
```

**Transaction types in the simulator**

| Transaction | Sender | Moves money? | When |
| --- | --- | --- | --- |
| ETH transfer (gas money) | operator | test ETH only, no IEC | init |
| `mint` (initial funding) | operator | yes → agent | init |
| `registerAgent` | agent | no | init |
| `registerService` | agent | no | init |
| `createTask` | assigner | yes → escrow | task generated / robot needs recharge |
| `assignTask` | operator | no | `assign_tasks()` |
| `requeueTask` | operator | no | schedule or battery interruption |
| `completeTask` | operator | yes escrow → assignee | `_finish_task(success=True)` |
| `failTask` | operator | yes escrow → assigner | `_finish_task(success=False)` |

**Functionalities**
- Send, sign, mined instantly by Ganache; the simulator gets the receipt back right away.
- **Revert** cleanly: if a rule is broken (not enough IEC, not registered…), the transaction
  is rejected and nothing changes. The simulator must handle this (e.g. task is not created).
- Export to `transactions.csv` alongside the existing CSVs.

> **What does "revert" mean?** All-or-nothing. If any check fails halfway, the whole
> transaction is undone as if it never happened. That's why money can never be "half
> transferred".

---

### 2.6 Event

**What it is today:** doesn't exist (the closest thing is the `task.created_step` /
`assigned_step` / `completed_step` fields).

**What it becomes:** contracts emit an event for every meaningful thing that happens.

| Event | Emitted by | Fields |
| --- | --- | --- |
| `Transfer` | Token | from, to, amount |
| `AgentRegistered` | AgentRegistry | address, agent_id, kind |
| `ServiceRegistered` | ServiceRegistry | provider, service, skill |
| `TaskCreated` | TaskEscrow | taskId, assigner, service, reward |
| `TaskAssigned` | TaskEscrow | taskId, assignee |
| `TaskRequeued` | TaskEscrow | taskId, previous assignee |
| `TaskCompleted` | TaskEscrow | taskId, assignee, reward |
| `TaskFailed` | TaskEscrow | taskId, assignee, refunded amount |

**Functionalities**
- **Logging** → `events.csv`: a full, ordered history of the market.
- **Metrics** → new reporters can be computed from events (money locked in escrow, payment
  flow robot→human, rejected tasks for lack of funds…).
- **Dashboard** → the Solara app can show a live event feed.

> **Transaction vs event — what's the difference?** A transaction is the *request*
> ("please complete task 42"). An event is the *announcement of the result* ("task 42
> completed, 140 IEC paid to robot_1_0"). One transaction can emit several events
> (e.g. `completeTask` emits `TaskCompleted` + `Transfer`).

---

## 3 · Smart contracts

Four contracts, each with one job:

| Contract | Job | Concepts it covers |
| --- | --- | --- |
| **IECToken** | The currency. Balances, transfers, minting at init. (Standard "ERC-20" token.) | Wallet, Transaction |
| **AgentRegistry** | Who is a member of the marketplace. | Agent |
| **ServiceRegistry** | Who offers which service, with what skill. | Servicio |
| **TaskEscrow** | Task agreements + holds and releases the money. | Tarea, Transaction, Event |

> **Why split into four and not one big contract?** Each is small, easy to read, easy to
> test. The token is a well-known standard (ERC-20), so we don't reinvent it.

---

## 4 · Design decisions

**D1 · Ganache, started fresh for every run.** ✅ *decided*
The contracts are written in **Solidity** and run on **Ganache**, a local Ethereum
blockchain. The simulator starts its own Ganache process at the beginning of each run and
stops it at the end:
- `--wallet.seed <simulation seed>` → the same pre-funded accounts every run;
- `--chain.time <fixed start date>` → the chain clock starts at the same moment every run;
- the first Ganache account (pre-loaded with test ETH) becomes the **operator** (D3).

All Python ↔ blockchain communication goes through one **chain client** module
(`blockchain/chain.py`, built on `web3.py`). It sends and signs transactions, waits for
receipts, turns reverts into Python errors the simulator can react to, decodes events, and
writes the transaction / event logs. The rest of the simulator calls simple functions like
`chain.create_task(wallet, service, reward)`.

*Why a fresh chain per run:* runs are independent (no leftover balances or tasks from a
previous run) and reproducible (same seed → same accounts, addresses and results).
*Why one chain client module:* web3 details stay in one place, and if we ever switch from
Ganache (it was sunset by Consensys in 2023; Hardhat and Anvil are maintained alternatives)
or move to a public testnet, only this module changes.
*Cost:* every economic action is a real transaction over JSON-RPC, so a 10 000-step run
takes minutes instead of seconds.

Config:

```yaml
blockchain:
  ganache_cmd: ganache      # command used to start Ganache (Node.js package)
  port: 8545
  gas_eth_per_agent: 10     # test ETH each agent wallet receives for gas
```

**D1b · The blockchain is always on.** ✅ *decided*
There is no `enabled` switch: every run uses wallets, registries and escrow. The old
`wealth -= / wealth +=` path in `economy.py` is removed; `economy.py` becomes the thin
"payments" module that talks to the TaskEscrow (`settle_task(task, success)` →
`completeTask` / `failTask`), so `agents.py` keeps calling the economy module as today.
*Why:* one code path is simpler to maintain and test than two, and the blockchain economy
*is* the simulator's economy from now on.

**D2 · Instant mining + simulation clock.** ✅ *decided*
Ganache mines every transaction immediately into its own block (its default "instamine"
mode). At the start of every `model.step()`, the simulator sets Ganache's clock to
`start + step × 60 s` (`evm_setTime`), so every block mined during that step carries that
step's timestamp. `step = (block.timestamp − start) / 60`.
*Why not one block per step?* That would mean pausing mining and only getting results at
the end of the step. But the simulator needs results right away: `createTask` must return
the new task's id (so it can be assigned in the same step), and a revert ("not enough
IEC") must be known immediately so the task is not queued. The clock gives us the same
"which minute did this happen" information without that problem — and 1 step = 1 minute =
60 s of chain time lines up naturally.

**D3 · The simulator is the operator and the oracle.**
The model has its own wallet (the "operator"). It is the only address allowed to call
`assignTask`, `completeTask`, `failTask`, `requeueTask`.
*Why:* the chain can't see the physical world, so someone trusted must report outcomes.
In a real deployment this could be replaced by sensors, the assigner confirming, or a
vote — but that's a later research question, not needed now.

**D4 · Matching stays off-chain.**
`assign_tasks()` still decides *who* gets the task (random among eligible). The contract
only checks the choice is valid (registered, offers the service).
*Why:* eligibility depends on battery, schedule and idle status, which live off-chain.

**D5 · Reward is sampled at task creation (not assignment).** ✅ *decided*
Escrow needs the amount up front (see [§ 2.4.1](#241--what-is-escrow-and-why-does-it-need-the-amount-at-creation)).
*Consequence:* moving the sampling changes the order of random draws, and since the
blockchain is always on (D1b), **runs with the same seed will not reproduce results
produced before the blockchain was added**. Together with D7 (unaffordable tasks are
rejected), the existing `experiments/` results must be re-run to serve as the new baseline.
Runs *after* the change are still fully reproducible with the same seed.

**D6 · Gas is paid in test ETH, not in IEC.** ✅ *decided*
On Ethereum every transaction must pay gas in ETH, Ganache included. At init the operator
sends each agent wallet some test ETH (`gas_eth_per_agent`) to cover its gas for the
whole run. Gas used is read from each transaction's receipt and recorded in the log, but
**no IEC is ever spent on gas**.
*Why:* charging fees in IEC changes the economy (wealth slowly leaks out of the system),
which is an interesting experiment on its own, not a default. Keeping fees in a separate
currency (ETH) leaves the IEC economy exactly as designed while still measuring the
on-chain cost of each action.

**D7 · Tasks the assigner can't afford are rejected.** ✅ *decided: option (a)*
`createTask` reverts, the task never enters the queue, and we count it in a new metric
`Rejected_Tasks`.
This includes **robots that can't afford a recharge**. We let that happen — it is a real
economic risk of a robot economy and an interesting result to measure:
- the robot stays `busy` / `awaiting_recharge` and its battery keeps draining to 0;
- it retries `createTask` every `recharge_max_wait` steps (not every step, so the
  transaction log isn't flooded with identical reverted transactions), in case its balance
  changed;
- a new metric `Stranded_Robots` counts robots that wanted a recharge but couldn't pay.

Note: robots are also *assigners* of random tasks (the assigner is picked among all
agents), so a robot can lock its money in other tasks' escrow and then be unable to pay for
its own recharge. That's a genuine emergent effect of the design, not a bug.

**D8 · Failed tasks refund the assigner.**
Same behaviour as today (no one gets paid on failure), but now explicit and logged.

---

## 5 · Example: one task, end to end

`robot_1_0` needs its battery charged, `human_2_0` does it. Reward = 120 IEC.

| Step | What happens in the sim | Transaction | Events | Balances (robot / escrow / human) |
| --- | --- | --- | --- | --- |
| 0 | init | `mint` ×2, `registerAgent` ×2, `registerService` ×… | `Transfer`, `AgentRegistered`, `ServiceRegistered` | 2000 / 0 / 2000 |
| 350 | battery ≤ 30 → recharge task | `createTask(BatteryCharging, 120)` from robot | `TaskCreated`, `Transfer(robot→escrow)` | 1880 / 120 / 2000 |
| 351 | `assign_tasks()` picks human_2_0 | `assignTask(7, human_2_0)` from operator | `TaskAssigned` | 1880 / 120 / 2000 |
| 351–370 | human walks, plugs in, dwells | — (off-chain) | — | unchanged |
| 371 | phase done, success | `completeTask(7)` from operator | `TaskCompleted`, `Transfer(escrow→human)` | 1880 / 0 / 2120 |

---

## 6 · What changes in the code (preview)

| File | Change |
| --- | --- |
| new `robopreneur/blockchain/` package | `ganache.py` (start / stop Ganache), `chain.py` (chain client on `web3.py`), `wallet.py`, `contracts/*.sol` (Solidity), compiled with `py-solc-x` |
| `core/model.py` | start Ganache, deploy contracts, operator wallet; set the chain clock every step |
| `behaviour/agents.py` | each agent gets a `wallet`; `wealth` reads the balance; `_finish_task` calls complete/fail |
| `tasks/services.py` | services registered in the registry at init |
| `tasks/task_assignation.py` | `createTask` on generation (handle revert); `assignTask` on assignment |
| `behaviour/battery.py` | recharge task goes through `createTask` (retry with cooldown if broke); `requeue` goes through `requeueTask` |
| `economy/economy.py` | `transfer_reward` removed; becomes `settle_task()` → escrow `completeTask` / `failTask` |
| `world/metrics.py` | new reporters: escrow locked, rejected tasks, stranded robots, tx count, gas |
| `scripts/run_experiment.py` | also writes `transactions.csv`, `events.csv` |
| `requirements.txt`, `Dockerfile` | `web3`, `py-solc-x`; Node.js + `ganache` + `@openzeppelin/contracts` in the image |
| `config.yaml`, `config/load_config.py` | new `blockchain:` section |
