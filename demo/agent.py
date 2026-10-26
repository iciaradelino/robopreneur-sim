"""Agent node terminal: one robot or human with its own wallet.

The agent does nothing on its own: you join the market (register, approve, offer), post
tasks (create), finish the ones assigned to you (complete) and confirm the work done on
your own tasks (confirm) by typing commands.
Every command is a transaction signed by this agent's wallet; events that concern this
agent are logged as they arrive.
"""

import sys

from chain.config import load_config
from chain.log import iec
from chain.node import Node, number
from chain.wallets import derive_account

KINDS = {"human": 0, "robot": 1}


class Agent(Node):
    def __init__(self, cfg, name):
        super().__init__(cfg, name, derive_account(cfg["chain"]["seed"], name))
        self.me = cfg["agents"][name]
        self.log.banner(f"{name.upper()} · {self.me['kind']} · {self.address}")

        c = self.client
        deployments = c.load_deployments()
        self.book.add(deployments["master"], "master")
        self.book.add(c.contracts["TaskEscrow"].address, "escrow")
        self.log("init", f"contracts loaded · offers {', '.join(self.me['services'])}")

        me, master = self.address, deployments["master"]
        c.subscribe("IECToken", "Transfer", self.on_funded, **{"from": master, "to": me})
        c.subscribe("TaskEscrow", "TaskCreated", self.on_task_created)
        c.subscribe("TaskEscrow", "TaskAssigned", self.on_assigned_to_me, assignee=me)
        c.subscribe("TaskEscrow", "TaskAssigned", self.on_my_task_assigned, assigner=me)
        c.subscribe("TaskEscrow", "TaskDelivered", self.on_my_task_delivered, assigner=me)
        c.subscribe("TaskEscrow", "TaskCompleted", self.on_my_work_confirmed, assignee=me)
        c.subscribe("TaskEscrow", "TaskRequeued", self.on_requeued_from_me, previousAssignee=me)
        c.listen()

    def balance(self):
        return iec(self.client.iec_balance(self.address))

    # ── commands ───────────────────────────────────────────────────────

    def cmd_register(self):
        """join the market (AgentRegistry)"""
        self.client.send_tx("AgentRegistry", "registerAgent", self.name, KINDS[self.me["kind"]])

    def cmd_approve(self):
        """allow the escrow to lock rewards from my wallet"""
        self.client.send_tx("IECToken", "approve", self.client.contract("TaskEscrow").address, 2**256 - 1)

    def cmd_offer(self, service=None):
        """list my services in the ServiceRegistry (default: all of them)"""
        services = [service] if service else self.me["services"]
        for s in services:
            if s not in self.me["services"]:
                raise ValueError(f"{s!r} is not one of my services: {', '.join(self.me['services'])}")
            self.client.send_tx("ServiceRegistry", "registerService", s, self.cfg["services"][s])

    def cmd_create(self, service, reward):
        """post a task and lock its reward (IEC) in escrow"""
        if service not in self.cfg["services"]:
            raise ValueError(f"unknown service {service!r}; services: {', '.join(self.cfg['services'])}")
        receipt = self.client.send_tx("TaskEscrow", "createTask", service, number(reward, "reward") * 100)
        task_id = self.client.events_in(receipt, "TaskEscrow", "TaskCreated")[0].args.taskId
        self.log("task", f"posted task #{task_id} · reward locked in escrow · balance {self.balance()}")

    def cmd_complete(self, task_id):
        """mark a task assigned to me as done - its poster then confirms it"""
        self.client.send_tx("TaskEscrow", "completeTask", number(task_id, "task id"))
        self.log("task", f"task #{task_id} delivered · waiting for its poster to confirm")

    def cmd_confirm(self, task_id):
        """confirm the work on one of my tasks - the reward goes to the worker"""
        self.client.send_tx("TaskEscrow", "confirmTask", number(task_id, "task id"))
        self.log("paid", f"task #{task_id} completed · reward released to the worker")

    def cmd_cancel(self, task_id):
        """withdraw one of my tasks nobody has taken yet - full refund"""
        self.client.send_tx("TaskEscrow", "cancelTask", number(task_id, "task id"))
        self.log("refund", f"task #{task_id} cancelled · balance {self.balance()}")

    # ── events ─────────────────────────────────────────────────────────

    def on_funded(self, e):
        self.log("paid", f"received {iec(e.args.value)} from the master · balance {self.balance()}")

    def on_task_created(self, e):
        a = e.args
        if a.assigner != self.address and a.service in self.me["services"]:
            self.log("event", f"task #{a.taskId} · {self.book.name(a.assigner)} needs {a.service}"
                              f" · {iec(a.reward)} - I offer this")

    def on_assigned_to_me(self, e):
        a = e.args
        self.log("event", f"task #{a.taskId} {a.service} assigned to me (posted by {self.book.name(a.assigner)})"
                          f"\n→ complete {a.taskId}")

    def on_my_task_assigned(self, e):
        self.log("event", f"my task #{e.args.taskId} {e.args.service} → {self.book.name(e.args.assignee)}")

    def on_my_task_delivered(self, e):
        a = e.args
        self.log("event", f"my task #{a.taskId} delivered by {self.book.name(a.assignee)}"
                          f"\n→ confirm {a.taskId}")

    def on_my_work_confirmed(self, e):
        a = e.args
        self.log("paid", f"task #{a.taskId} confirmed by {self.book.name(a.assigner)} · paid {iec(a.reward)}"
                         f" · balance {self.balance()}")

    def on_requeued_from_me(self, e):
        self.log("warn", f"the master took task #{e.args.taskId} back")


if __name__ == "__main__":
    config = load_config()
    if len(sys.argv) != 2 or sys.argv[1] not in config["agents"]:
        sys.exit(f"usage: python agent.py <name>   names: {', '.join(config['agents'])}")
    Agent(config, sys.argv[1]).run()
