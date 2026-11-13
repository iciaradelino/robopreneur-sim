# Blockchain in Robopreneur Sim

## 1. Architecture

```mermaid
flowchart TD
  classDef sim      fill:#1e3a5f,stroke:#3b82f6,color:#bfdbfe
  classDef changed  fill:#1e3a5f,stroke:#3b82f6,color:#bfdbfe,stroke-width:3px,stroke-dasharray:6 4
  classDef chain    fill:#3d3000,stroke:#facc15,color:#fef08a,stroke-width:2px
  classDef contract fill:#4a3500,stroke:#f59e0b,color:#fde68a,stroke-width:2px
  classDef out      fill:#252525,stroke:#94a3b8,color:#e2e8f0

  subgraph SIM["Simulator  (existing, Python + Mesa)"]
    direction TB
    CONFIG[("config.yaml\n+ ganache settings")]:::changed
    MODEL["Model\nstep loop · 1 step = 1 minute"]:::changed

    subgraph TASKFLOW["Tasks"]
      direction LR
      TGEN["Task generation\nrandom requester\n+ locks reward"]:::changed
      QUEUE["Task queue\nmirror of on-chain\nassignments & waiting list"]:::changed
      TASSIGN["Availability\nidle · schedule · battery ok\n→ told to the chain"]:::changed
    end

    subgraph AGENTS["Agents"]
      direction LR
      HUMANS["Humans\nmove · do tasks\n+ wallet"]:::changed
      ROBOTS["Robots\nmove · battery · do tasks\n+ wallet · pay own recharge"]:::changed
    end

    WORLD["World\nspace · floor plan · routing"]:::sim
    EXEC["Task execution\nwaypoints · dwell · failure roll"]:::sim
    ECO["Economy\npayments"]:::changed
    METRICS["Metrics & dashboard\ngini · wealth · queue · battery\n+ escrow · rejected · stranded"]:::changed

    CONFIG --> MODEL
    MODEL --> TGEN
    TGEN --> QUEUE
    QUEUE --> TASSIGN
    TASSIGN --> HUMANS
    TASSIGN --> ROBOTS
    ROBOTS -->|low battery:\nrecharge task| QUEUE
    HUMANS --> EXEC
    ROBOTS --> EXEC
    HUMANS -.-> WORLD
    ROBOTS -.-> WORLD
    EXEC -->|task ends| ECO
    MODEL --> METRICS
  end

  subgraph BC["Blockchain layer  (new)"]
    direction TB
    WALLET["Wallet\none per agent\nsigns transactions"]:::chain
    CHAIN["Chain client\nweb3.py · one module for\nall blockchain calls · tx & event log"]:::chain
    subgraph GAN["Ganache  —  local Ethereum blockchain, fresh for every run"]
      direction LR
      TOKEN["IECToken\ncurrency"]:::contract
      AREG["AgentRegistry\nmembers"]:::contract
      SREG["ServiceRegistry\nwho offers what, at what price"]:::contract
      TM["TaskManager\ntask registry · locks & releases rewards"]:::contract
      ORG["Organization\nassigns tasks on-chain"]:::contract
    end
  end

  OUT["Outputs\ntransactions.csv · events.csv"]:::out

  MODEL ==>|start Ganache · deploy · sync clock| CHAIN
  HUMANS ==>|owns| WALLET
  ROBOTS ==>|owns| WALLET
  AGENTS ==>|register agent & services| CHAIN
  TGEN ==>|create task| CHAIN
  ROBOTS ==>|create recharge task| CHAIN
  TASSIGN ==>|set availability| CHAIN
  ECO ==>|complete / fail task| CHAIN
  METRICS ==>|reads balances & events| CHAIN
  WALLET ==>|signs| CHAIN
  CHAIN ==>|JSON-RPC| GAN
  TM --> TOKEN
  TM --> SREG
  TM -->|task registered / ended| ORG
  ORG -->|assigns| TM
  ORG -->|reads offers| SREG
  SREG --> AREG
  CHAIN -->|logs| OUT
```

Dashed blue = existing modules that get small changes. 
Plain blue = unchanged. 
Gold = new.

1. Wallet (one per agent). Each human and robot gets a blockchain account: a public address, like a bank account number, and a secret key. The wallet signs every request the agent sends. That signature is how the blockchain knows who is asking, and stops one agent from spending another's money.
2. Chain client. A single Python module (built on web3.py, the standard Python library for Ethereum) that does all the talking to the blockchain. The rest of the simulator never deals with blockchain details. It calls simple functions like "create task", and the chain client sends the request, waits for the answer, turns errors such as "not enough money" into something the simulator can react to, and keeps a log of every transaction and event.
Why it matters: if you ever replace Ganache, only this module changes.
3. Ganache, with the five smart contracts inside. Ganache is the blockchain itself, running on your computer and started fresh for each run. Inside it live the five contracts (small programs whose rules can't be changed once installed). They follow the structure of RODEO's [`Organization.sol`](https://github.com/IERoboticsAILab/RODEO/blob/main/blockchain-network/smart-contracts/contracts/Organization.sol), with TaskManager and ServiceRegistry in the roles of RODEO's TaskManager and ServiceManager:
- IECToken: the money. It holds everyone's balances and moves IEC between accounts.
- AgentRegistry: the member list. Only registered agents can take part in the market.
- ServiceRegistry: the "yellow pages" of who offers which service, at what price, and who is available right now. The arrow to AgentRegistry means it checks the member list before accepting a listing.
- TaskManager: the task registry. Every task is recorded here, so its whole history (who asked, who got it, at what price, how it ended) is immutable and traceable. It also holds each task's reward in escrow until the task ends: it uses IECToken to lock and release money, and checks ServiceRegistry so a task only goes to someone who actually offers that service.
- Organization: the matchmaker. As soon as a task is registered, TaskManager calls it and it assigns the task in the same transaction to the cheapest available provider whose price fits the reward. A task nobody can take yet waits on-chain, and an agent that frees up gets the best-paid waiting task it can do.

### Smart contract functions

**IECToken** — ERC-20 (OpenZeppelin), 2 decimals so rewards like 140.37 IEC are exact.

| Function | Caller | Does | Event |
| --- | --- | --- | --- |
| `mint(to, amount)` | operator | create IEC in a wallet; only while minting is open | `Transfer` |
| `finishMinting()` | operator | close minting forever → fixed supply | `MintingFinished` |
| `approve(spender, amount)` | agent | let TaskManager pull IEC from this wallet *(standard)* | `Approval` |
| `transfer` / `transferFrom` | TaskManager | move IEC *(standard, used by TaskManager)* | `Transfer` |
| `balanceOf(address)` | anyone · view | IEC balance *(standard)* | — |

**AgentRegistry**

| Function | Caller | Does | Event |
| --- | --- | --- | --- |
| `registerAgent(agentId, kind)` | agent | add caller as `human` / `robot`; fails if already registered | `AgentRegistered` |
| `isRegistered(address)` | anyone · view | is this address a member? | — |
| `getAgent(address)` | anyone · view | agentId, kind | — |

**ServiceRegistry** — knows AgentRegistry.

| Function | Caller | Does | Event |
| --- | --- | --- | --- |
| `registerService(name, category, skill, price)` | agent | publish an offer; caller must be registered, `skill` 0–1000 | `ServiceRegistered` |
| `setAvailable(provider, available)` | operator | the simulator says whether an agent can take work now (schedule, battery, charging); becoming available makes the Organization look for a waiting task for it | `ProviderAvailable` |
| `setBusy(provider, busy)` | Organization | set on assignment, cleared when the task ends | `ProviderBusy` |
| `offers(provider, name)` | anyone · view | does this provider offer this service? | — |
| `getProviders(name)` | anyone · view | all providers of a service | — |

**TaskManager** — the task registry and its escrow. Knows IECToken, both registries, the operator and the Organization.

| Function | Caller | Rules | Does | Event |
| --- | --- | --- | --- | --- |
| `createTask(service, category, reward) → taskId` | assigner (agent) | registered · enough IEC | reward: wallet → escrow; status `Open`; **calls the Organization, which assigns it in the same transaction or queues it** | `TaskCreated` (+ `TaskAssigned` or `TaskQueued`) |
| `assignTask(taskId, assignee, price)` | Organization | `Open` · assignee registered, offers service, ≠ assigner · price ≤ reward | status `Assigned` | `TaskAssigned` |
| `requeueTask(taskId)` | Organization | `Assigned` | back to `Open`, money stays locked | `TaskRequeued` |
| `completeTask(taskId)` | operator | `Assigned` | price: escrow → assignee, rest → assigner; status `Completed`; frees the assignee | `TaskCompleted` |
| `failTask(taskId)` | operator | `Assigned` | reward: escrow → assigner; status `Failed`; frees the assignee | `TaskFailed` |
| `cancelTask(taskId)` | assigner | `Open` | refund assigner; status `Cancelled` *(not used by the sim yet)* | `TaskCancelled` |
| `getTask(taskId)` | anyone · view | — | assigner, assignee, service, category, reward, price, status | — |
| `totalLocked()` | anyone · view | — | IEC currently held in escrow (for metrics) | — |

**Organization** — on-chain assignment, adapted from RODEO's `Organization.sol`. Owned by the operator.

| Function | Caller | Does | Event |
| --- | --- | --- | --- |
| `onTaskRegistered(taskId)` | TaskManager | assign to the **cheapest available, idle provider** offering the service with `price ≤ reward` (never the assigner); if none, add to the waiting list | `TaskMatched` or `TaskQueued` |
| `onTaskEnded(taskId)` | TaskManager | free the provider, then give it the **highest-reward waiting task** it can do (oldest first on a tie) | `TaskMatched` |
| `onProviderAvailable(provider)` / `onServiceRegistered(id)` | ServiceRegistry | same as above for that provider | `TaskMatched` |
| `unassignTask(taskId)` | operator | interruption: requeue the task, reassign it to another provider or put it back on the waiting list | `TaskMatched` or `TaskQueued` |
| `getWaitingTasks()` | anyone · view | tasks nobody could take yet | — |


## 2. Flow and initialization

```mermaid
flowchart LR
  classDef init  fill:#1e3a5f,stroke:#3b82f6,color:#bfdbfe
  classDef chain fill:#3d3000,stroke:#facc15,color:#fef08a,stroke-width:2px
  classDef loop  fill:#1a2e1a,stroke:#22c55e,color:#bbf7d0

  subgraph INIT["Initialization  —  once, at step 0"]
    direction TB
    P1["1 · System & config\nseed · world"]:::init
    P2["2 · Start Ganache & deploy contracts\nToken → AgentRegistry → ServiceRegistry\n→ TaskManager → Organization"]:::chain
    P3["3 · Create agents\nhumans · robots"]:::init
    P4["4 · Create wallets\ngas ETH · register ·\nfund 2000 IEC · authorize TaskManager"]:::chain
    P5["5 · Register services\nwith prices"]:::chain
    P6["6 · Finish setup\nmoney supply fixed"]:::chain
    P1 --> P2 --> P3 --> P4 --> P5 --> P6
  end

  subgraph LOOP["Every step  —  chain clock = step × 60 s"]
    direction TB
    L1["Task registered\nrequester locks reward\nin escrow"]:::chain
    L2["Task assigned on-chain\nsame transaction:\nOrganization picks worker"]:::chain
    L3["Task executed\noff-chain: move · dwell"]:::loop
    L4["Task ends\nsuccess → worker paid\nfailure → requester refunded"]:::chain
    L1 --> L2 --> L3 --> L4
  end

  P6 --> L1
```

Startup happens once, at step 0:

1. System and config. Read config.yaml, set the random seed and build the world. Same as today, plus reading the blockchain: settings (Ganache port and start options).
2. Start Ganache and deploy the contracts. The simulator starts a fresh Ganache blockchain for this run (same seed → same accounts every time) and connects to it. Ganache's first account, which comes pre-loaded with test ETH, becomes the simulator's own wallet (the "operator"). Then it installs the five contracts in order: Token → AgentRegistry → ServiceRegistry → TaskManager → Organization, and connects the Organization with TaskManager and ServiceRegistry (they call each other, so each is told the other's address once both exist). The order matters because each contract must be told where the contracts it checks live, so those must exist first (foundations before walls before roof). This comes before the agents because you can't open an account at a bank that doesn't exist yet.
3. Create the agents. Same as today: humans and robots placed in the world. At this point they have no money and no market identity.
4. Create the wallets. For each agent:
- (a) generate its wallet from the seed plus its name, so it gets the same address every run;
- (b) receive some test ETH from the operator to pay for gas (the blockchain's transaction fee — separate from IEC, the market's money);
- (c) join the member list;
- (d) receive 2000 IEC;
- (e) authorize the TaskManager to take payments from it (into escrow), like setting up a domiciliación bancaria. Without this, a contract can't touch anyone's money.
5. Register services. Each agent publishes what it offers and its price, e.g. "robot_1_0 offers LabCleaning, skill 950, 110 IEC". Skill is stored ×1000 because blockchains don't handle decimals. The registry rejects anyone not on the member list, which is why step 4 comes first.
6. Finish setup. The simulator gives up its power to create money, so the economy is fixed at 8000 IEC for the whole run. All 46 setup transactions (default config) are recorded at step 0, and the first metrics snapshot is taken.

Every step:

1. Sync the clock: the simulator sets Ganache's clock to step × 60 seconds, so every transaction in this step carries this step's time.
2. Task registered: a random agent requests a service and its reward is moved from its wallet into escrow. **In the same transaction the Organization contract assigns it** to the cheapest available provider whose price fits, or puts it on the on-chain waiting list. The simulator reads who got it from the transaction's events and starts that agent on it. If the requester can't afford it, the request is rejected and counted. A robot with low battery does the same for its own recharge; if it's broke, it becomes "stranded" and tries again later.
3. Agents act: they move and work (normal Python). When a task ends, the economy module tells the TaskManager to pay the worker (its price; the rest goes back to the requester) or refund the requester. The worker is free again and the Organization hands it the best waiting task in that same transaction. If a task is interrupted, the Organization takes it back and reassigns it, with its money still locked.
4. Availability: when an agent's off-chain state changes (its schedule starts or ends, a robot needs or finishes a recharge), the simulator tells the ServiceRegistry, so the Organization only assigns to agents that can actually work.
5. Metrics collected.

---

## 3. Decisions 

| # | Decision | Why |
| --- | --- | --- |
| 4 | **One chain client module** (`chain.py`, on `web3.py`) | All blockchain calls, signing, error handling and logging live in one place. The rest of the simulator calls simple functions like `create_task()`. If we ever move from Ganache to another chain, only this module changes. |
| 5 | **On-chain vs off-chain split** — money, identity, service offers and task agreements on-chain; movement, battery, schedules, execution off-chain | Running physics on-chain would be slow and pointless; this is how real robot/IoT marketplaces split it. |
| 6 | **Five small contracts**: IECToken, AgentRegistry, ServiceRegistry, TaskManager, Organization (RODEO's structure) | One job each, easy to read and test. TaskManager is the task registry, so every task is immutable and traceable. |
| 7 | **Escrow:** reward locked at task creation, released on completion, refunded on failure | Every task in the queue is guaranteed to be paid; nobody's balance can go negative (today it can). |
| 8 | **Reward decided at creation**, not at assignment; the worker is paid **its price** (≤ reward) | Escrow needs the amount up front, so the reward is the requester's budget. As in RODEO, the Organization picks the cheapest provider and the agreed price is what gets paid; the rest goes back to the requester. |
| 9 | **Unaffordable tasks are rejected** — including robots that can't pay their recharge (they become "stranded") | Realistic economic constraint, and a new result to measure. Robots retry periodically. |
| 10 | **The simulator is the operator / oracle**: it reports task outcomes, interruptions and agent availability | The chain can't see the physical world. Replacing this with sensors or assigner confirmation is a possible future research direction. |
| 11 | **Assignment is on-chain** (Organization contract, as in RODEO): a task is assigned the moment it is registered, to the cheapest available provider with `price ≤ reward` | The assignment itself becomes traceable, not just its result. Battery, schedule and idle state stay off-chain; the simulator only reports *available / unavailable* when they change. |
| 12 | **Instant mining + simulation clock**: every transaction is mined right away in its own block; Ganache's clock is set to step × 60 s | The simulator needs each result immediately (the new task's id, or "rejected: not enough money") to continue the same step. The clock keeps every transaction tied to its simulation minute. |
| 13 | **Gas paid in test ETH, not IEC** | On Ethereum every transaction needs ETH for fees. Ganache provides free test ETH, so the IEC economy is unaffected. Gas used is still recorded per transaction; charging fees in IEC could be a later experiment. |
| 14 | **Fixed money supply**: minted once at init (2000 IEC per agent in default config), then minting is disabled | Money is conserved; we can verify no IEC is created or lost. |
| 15 | **Reproducible wallets**: keys derived from seed + agent id | Same seed → same addresses → comparable runs. Simulation-only keys. |


## 4. On-chain vs off-chain

On-chain = money, identity and agreements between agents (things that must be trusted and auditable). 
Off-chain = physical state and anything that changes every step
(writing it on-chain would cost a transaction each time).

| Data | On-chain (Ganache) | Off-chain (Python) |
| --- | --- | --- |
| **Agent** | address, `agent_id`, human / robot → AgentRegistry | position, speed, status, schedule, route |
| **Robot battery** | — | battery level, charging state |
| **Money** | IEC balances → IECToken (`agent.wealth` just reads it); test ETH for gas | — |
| **Services** | who offers what, category, skill, price, available → ServiceRegistry | definition: reward median, waypoints, durations, failure probability (`config.yaml`) |
| **Task** | requester, worker, service, locked reward, price, status → TaskManager | waypoints, current phase, dwell timer, location |
| **Task queue & matching** | who is picked (Organization), the waiting list, busy flags | the reasons an agent is unavailable (battery, schedule, charging); a mirror of the queue for the dashboard |
| **Task outcome** | recorded: `completeTask` / `failTask` + payment | decided: execution and failure roll |
| **Time** | block timestamp = step × 60 s | step counter, day / minute clock |
| **History** | every transaction and event | exported to `transactions.csv`, `events.csv` |
| **Metrics** | source data (balances, TaskManager escrow) | computed: Gini, throughput, queue, battery |

Each on-chain record has a Python "twin" linked by an id: agent ↔ wallet address,
service ↔ provider + name, task ↔ `chain_task_id`.


## 5 · Questions

- Que hacemos con los gas fees?
- Precio por servicio: ¿qué valor le damos a cada agente en `config.yaml`? Con on-chain assignment el worker cobra su precio (no la reward), así que cambia la economía respecto al simulador actual.
- 