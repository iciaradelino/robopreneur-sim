"""Master node terminal: deploys the contracts, registers the agents and assigns tasks.

The master is the operator: after `deploy` it holds the whole IEC supply, and it is the
only wallet allowed to assign and requeue tasks. `register` gives every agent its wallet
(derived from the seed) and sets it up for the market. `start` does both if needed and
then runs the market on its own (see chain/auto.py): the master assigns open tasks FIFO,
each to a random idle provider, like the simulator. Without `start` nothing happens until
you type a command; events from the agents' terminals are logged as they arrive.
"""

import threading

from eth_account import Account

from chain.client import TxReverted
from chain.compile import compile_contracts
from chain import auto
from chain.config import AUTO_PATH, DEPLOYMENTS_PATH, load_config
from chain.log import iec
from chain.node import Node, number
from chain.wallets import derive_account

KINDS = ["human", "robot"]


class Master(Node):
    def __init__(self, cfg):
        super().__init__(cfg, "master", Account.from_key(cfg["chain"]["master_key"]))
        self.book.add(self.address, "master")
        self.log.banner(f"MASTER · {self.address}")
        # what the FIFO assigner knows, kept up to date from the escrow's events
        self.queue = []  # open tasks, oldest first: (task id, service, assigner)
        self.busy = set()  # agents working on a task (assigned, not delivered yet)
        self.running = False
        self.rng = auto.rng(cfg, "master")
        self.lock = threading.Lock()  # the prompt and the event thread both assign

    # ── commands ───────────────────────────────────────────────────────

    def cmd_deploy(self):
        """compile and deploy the 4 contracts; the master gets the whole IEC supply"""
        if self.client.contracts:
            raise ValueError("already deployed - restart Ganache for a fresh chain")
        DEPLOYMENTS_PATH.unlink(missing_ok=True)
        AUTO_PATH.unlink(missing_ok=True)
        chain = self.cfg["chain"]
        compiled = compile_contracts(chain["solc_version"], chain["evm_version"])

        # foundations first: each contract is told where the ones it checks live
        c = self.client
        c.deploy("IECToken", compiled["IECToken"], self.cfg["token"]["total_supply"] * 100, self.address)
        c.deploy("AgentRegistry", compiled["AgentRegistry"])
        c.deploy("ServiceRegistry", compiled["ServiceRegistry"], c.contracts["AgentRegistry"].address)
        c.deploy("TaskEscrow", compiled["TaskEscrow"], c.contracts["IECToken"].address,
                 c.contracts["AgentRegistry"].address, c.contracts["ServiceRegistry"].address, self.address)
        self.book.add(c.contracts["TaskEscrow"].address, "escrow")
        c.save_deployments()
        self.log("deploy", f"master holds {iec(c.iec_balance(self.address))} · next: register")

        c.subscribe("TaskEscrow", "TaskCreated", self.on_task_created)
        c.subscribe("TaskEscrow", "TaskAssigned", self.on_task_assigned)
        c.subscribe("TaskEscrow", "TaskRequeued", self.on_task_requeued)
        c.subscribe("TaskEscrow", "TaskDelivered", self.on_task_delivered)
        c.subscribe("TaskEscrow", "TaskCompleted", self.on_task_completed)
        c.subscribe("TaskEscrow", "TaskCancelled", self.on_task_cancelled)
        c.listen()

    def cmd_register(self):
        """give every agent its wallet, gas ETH and initial_wealth; register it, approve the escrow, list its services"""
        c = self.client
        escrow = c.contract("TaskEscrow").address
        todo = self.unregistered()
        if not todo:
            raise ValueError("every agent is registered already")
        for name in todo:
            agent = self.cfg["agents"][name]
            # same seed + name as the agent terminal derives, so the master can sign its setup
            account = derive_account(self.cfg["chain"]["seed"], name)
            wallet = c.as_wallet(account, name)
            c.send_eth(account.address, self.cfg["chain"]["gas_eth_per_agent"])
            wallet.send_tx("AgentRegistry", "registerAgent", name, KINDS.index(agent["kind"]))
            c.send_tx("IECToken", "transfer", account.address, agent["initial_wealth"] * 100)
            wallet.send_tx("IECToken", "approve", escrow, 2**256 - 1)
            for service in agent["services"]:
                wallet.send_tx("ServiceRegistry", "registerService", service, self.cfg["services"][service]["category"])
            self.log("paid", f"{name} registered as {agent['kind']} · {account.address} · {iec(c.iec_balance(account.address))}"
                             f"\noffers {', '.join(agent['services'])}")

    def cmd_start(self):
        """run the market on its own: deploy and register if needed, then tasks arrive, get assigned and finish"""
        if not self.client.contracts:
            self.cmd_deploy()
        if self.unregistered():
            self.cmd_register()
        if self.running:
            raise ValueError("already running - `stop` pauses it")
        a = self.cfg["auto"]
        self.running = True
        auto.set_running(True)
        self.log("init", f"market running · 1 min = {a['step_s']} s · ~{a['arrival_rate']} tasks/h"
                         f" · open tasks go FIFO to a random idle provider · `stop` pauses")
        self.assign_open()

    def cmd_stop(self):
        """pause: no new tasks or assignments; work in progress still finishes"""
        if not self.running:
            raise ValueError("not running - `start` runs the market")
        self.running = False
        auto.set_running(False)
        self.log("init", f"market paused · {len(self.queue)} open task(s) wait · `start` resumes")

    def cmd_fund(self, agent, amount=None):
        """top up an agent or `all` with IEC (default: its initial_wealth)"""
        names = list(self.cfg["agents"]) if agent == "all" else [agent]
        for name in names:
            address = self.agent_address(name)
            if self.client.eth_balance(address) == 0:
                self.client.send_eth(address, self.cfg["chain"]["gas_eth_per_agent"])
            units = (number(amount, "amount") if amount else self.cfg["agents"][name]["initial_wealth"]) * 100
            self.client.send_tx("IECToken", "transfer", address, units)
            self.log("paid", f"{name} received {iec(units)}")

    def cmd_assign(self, task_id, agent):
        """give an open task to an agent that offers its service"""
        self.client.send_tx("TaskEscrow", "assignTask", number(task_id, "task id"), self.agent_address(agent))

    def cmd_requeue(self, task_id):
        """take an assigned task back; it is open again and its reward stays locked"""
        self.client.send_tx("TaskEscrow", "requeueTask", number(task_id, "task id"))

    def unregistered(self):
        return [name for name in self.cfg["agents"]
                if not self.client.call("AgentRegistry", "isRegistered", self.book.addresses[name])]

    def assign_open(self):
        """FIFO: walk the open tasks oldest first, give each to a random idle provider (not its poster)."""
        with self.lock:
            if not self.running:
                return
            for task in list(self.queue):
                task_id, service, assigner = task
                idle = [p for p in self.client.call("ServiceRegistry", "getProviders", service)
                        if p != assigner and p not in self.busy]
                if not idle:
                    continue  # stays at its place in the queue until a provider is free
                assignee = self.rng.choice(idle)
                try:
                    self.client.send_tx("TaskEscrow", "assignTask", task_id, assignee)
                except TxReverted:
                    continue  # e.g. cancelled meanwhile: its event takes it off the queue
                self.queue.remove(task)
                self.busy.add(assignee)

    # ── events ─────────────────────────────────────────────────────────

    def on_task_created(self, e):
        a = e.args
        with self.lock:
            self.queue.append((a.taskId, a.service, a.assigner))
        providers = [self.book.name(p) for p in self.client.call("ServiceRegistry", "getProviders", a.service)
                     if p != a.assigner]
        hint = f" → assign {a.taskId} {providers[0]}" if providers and not self.running else ""
        self.log("event", f"task #{a.taskId} · {self.book.name(a.assigner)} needs {a.service} · {iec(a.reward)} locked\n"
                          f"providers: {', '.join(providers) or 'nobody yet'}{hint}")
        self.assign_open()

    def on_task_assigned(self, e):
        a = e.args
        with self.lock:  # also covers a manual `assign`
            self.queue = [t for t in self.queue if t[0] != a.taskId]
            self.busy.add(a.assignee)
        self.log("event", f"task #{a.taskId} {a.service} → {self.book.name(a.assignee)}")

    def on_task_requeued(self, e):
        a = e.args
        assigner, _, service, *_ = self.client.call("TaskEscrow", "getTask", a.taskId)
        with self.lock:
            self.busy.discard(a.previousAssignee)
            self.queue.append((a.taskId, service, assigner))  # back of the queue, as in the simulator
        self.assign_open()

    def on_task_delivered(self, e):
        a = e.args
        with self.lock:
            self.busy.discard(a.assignee)
        self.log("event", f"task #{a.taskId} delivered by {self.book.name(a.assignee)}"
                          f" · waiting for {self.book.name(a.assigner)} to confirm")
        self.assign_open()

    def on_task_completed(self, e):
        a = e.args
        self.log("paid", f"task #{a.taskId} completed · {self.book.name(a.assignee)} paid {iec(a.reward)}"
                         f" by {self.book.name(a.assigner)}")

    def on_task_cancelled(self, e):
        with self.lock:
            self.queue = [t for t in self.queue if t[0] != e.args.taskId]
        self.log("refund", f"task #{e.args.taskId} cancelled · {iec(e.args.refunded)} back to"
                           f" {self.book.name(e.args.assigner)}")


if __name__ == "__main__":
    Master(load_config()).run()
