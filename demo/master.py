"""Master node terminal: deploys the contracts and registers the agents.

The master owns the Organization contract: after `deploy` it holds the whole IEC supply.
It does not pick assignees: every task registered in TaskManager is assigned on-chain by
the Organization contract in the same transaction (see contracts/Organization.sol), and
the master only watches the events. Its one say over assignment is `requeue`, which asks
the Organization to take a task back and give it to someone else. `register` gives every
agent its wallet (derived from the seed) and sets it up for the market. `start` does both
if needed and then lets tasks arrive on their own (see chain/auto.py).
"""

from eth_account import Account

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
        self.running = False

    # ── commands ───────────────────────────────────────────────────────

    def cmd_deploy(self):
        """compile and deploy the 5 contracts and wire the Organization; the master gets the whole IEC supply"""
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
        c.deploy("TaskManager", compiled["TaskManager"], c.contracts["IECToken"].address,
                 c.contracts["AgentRegistry"].address, c.contracts["ServiceRegistry"].address)
        c.deploy("Organization", compiled["Organization"])
        # the Organization and the two contracts it drives need each other's address
        org = c.contracts["Organization"].address
        c.send_tx("Organization", "setTaskManager", c.contracts["TaskManager"].address)
        c.send_tx("Organization", "setServiceRegistry", c.contracts["ServiceRegistry"].address)
        c.send_tx("TaskManager", "setOrganization", org)
        c.send_tx("ServiceRegistry", "setOrganization", org)
        self.book.add(c.contracts["TaskManager"].address, "taskmanager")
        self.book.add(org, "organization")
        c.save_deployments()
        self.log("deploy", f"master holds {iec(c.iec_balance(self.address))} · next: register")

        c.subscribe("TaskManager", "TaskCreated", self.on_task_created)
        c.subscribe("TaskManager", "TaskAssigned", self.on_task_assigned)
        c.subscribe("Organization", "TaskQueued", self.on_task_queued)
        c.subscribe("TaskManager", "TaskRequeued", self.on_task_requeued)
        c.subscribe("TaskManager", "TaskDelivered", self.on_task_delivered)
        c.subscribe("TaskManager", "TaskCompleted", self.on_task_completed)
        c.subscribe("TaskManager", "TaskCancelled", self.on_task_cancelled)
        c.listen()

    def cmd_register(self):
        """give every agent its wallet, gas ETH and initial_wealth; register it, approve the TaskManager, list its services and prices"""
        c = self.client
        task_manager = c.contract("TaskManager").address
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
            wallet.send_tx("IECToken", "approve", task_manager, 2**256 - 1)
            for service, price in agent["services"].items():
                wallet.send_tx("ServiceRegistry", "registerService", service,
                               self.cfg["services"][service]["category"], price * 100)
            offers = ", ".join(f"{s} {iec(p * 100)}" for s, p in agent["services"].items())
            self.log("paid", f"{name} registered as {agent['kind']} · {account.address} · {iec(c.iec_balance(account.address))}"
                             f"\noffers {offers}")

    def cmd_start(self):
        """run the market on its own: deploy and register if needed, then tasks arrive and finish on their own"""
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
                         f" · the Organization contract assigns each task as it is registered · `stop` pauses")

    def cmd_stop(self):
        """pause: no new tasks arrive; work in progress (and assignment of waiting tasks) goes on"""
        if not self.running:
            raise ValueError("not running - `start` runs the market")
        self.running = False
        auto.set_running(False)
        waiting = len(self.client.call("Organization", "getWaitingTasks"))
        self.log("init", f"market paused · {waiting} task(s) waiting for a provider · `start` resumes")

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

    def cmd_requeue(self, task_id):
        """take a task back from its provider; the Organization gives it to another one (or queues it)"""
        self.client.send_tx("Organization", "unassignTask", number(task_id, "task id"))

    def unregistered(self):
        return [name for name in self.cfg["agents"]
                if not self.client.call("AgentRegistry", "isRegistered", self.book.addresses[name])]

    # ── events ─────────────────────────────────────────────────────────

    def on_task_created(self, e):
        a = e.args
        self.log("event", f"task #{a.taskId} registered · {self.book.name(a.assigner)} needs {a.service}"
                          f" ({a.category}) · {iec(a.reward)} locked")

    def on_task_assigned(self, e):
        a = e.args
        self.log("event", f"task #{a.taskId} {a.service} → {self.book.name(a.assignee)} at {iec(a.price)}"
                          f" (assigned on-chain by the Organization)")

    def on_task_queued(self, e):
        a = e.args
        self.log("warn", f"task #{a.taskId} {a.service} · {iec(a.reward)} · no idle provider at that price"
                         f" · waits in the Organization's queue")

    def on_task_requeued(self, e):
        self.log("event", f"task #{e.args.taskId} taken back from {self.book.name(e.args.previousAssignee)}")

    def on_task_delivered(self, e):
        a = e.args
        self.log("event", f"task #{a.taskId} delivered by {self.book.name(a.assignee)}"
                          f" · waiting for {self.book.name(a.assigner)} to confirm")

    def on_task_completed(self, e):
        a = e.args
        refund = f" · {iec(a.refunded)} back to {self.book.name(a.assigner)}" if a.refunded else ""
        self.log("paid", f"task #{a.taskId} completed · {self.book.name(a.assignee)} paid {iec(a.paid)}"
                         f" by {self.book.name(a.assigner)}{refund}")

    def on_task_cancelled(self, e):
        self.log("refund", f"task #{e.args.taskId} cancelled · {iec(e.args.refunded)} back to"
                           f" {self.book.name(e.args.assigner)}")


if __name__ == "__main__":
    Master(load_config()).run()
