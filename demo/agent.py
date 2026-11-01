"""Agent node terminal: one robot or human with its own wallet.

The agent's wallet is derived from the seed and its name, but it stays unused until the
master's `register` funds and registers it, approves the escrow and lists its services;
the terminal waits for that. Then you
post tasks (create), finish the ones assigned to you (complete) and confirm the work done
on your own tasks (confirm) by typing commands - or, once the master has typed `start`,
the agent does all three on its own (see chain/auto.py).
Every command is a transaction signed by this agent's wallet; events that concern this
agent are logged as they arrive.
"""

import sys
import threading
import time

from chain import auto
from chain.client import TxReverted
from chain.config import load_config
from chain.log import iec
from chain.node import Node, number
from chain.wallets import derive_account


class Agent(Node):
    def __init__(self, cfg, name):
        super().__init__(cfg, name, derive_account(cfg["chain"]["seed"], name))
        self.me = cfg["agents"][name]
        self.rng = auto.rng(cfg, name)
        self.working = set()  # tasks assigned to me that I have not delivered yet
        # in automatic mode I post tasks other agents can do (as in the simulator, never BatteryCharging)
        self.postable = sorted({s for other, a in cfg["agents"].items() if other != name
                                for s in a["services"]} - auto.NOT_RANDOM)

        c = self.client
        deployments = c.load_deployments()
        self.book.add(deployments["master"], "master")
        self.book.add(c.contracts["TaskEscrow"].address, "escrow")
        self.log("init", "contracts loaded")

        c.wait_until(lambda: c.call("AgentRegistry", "isRegistered", self.address),
                     "not registered yet - waiting for the master to `register` the agents …")
        self.log.banner(f"{name.upper()} · {self.me['kind']} · {self.address}")
        self.log("init", f"registered by the master · balance {self.balance()} · offers {', '.join(self.me['services'])}")

        me, master = self.address, deployments["master"]
        c.subscribe("IECToken", "Transfer", self.on_funded, **{"from": master, "to": me})
        c.subscribe("TaskEscrow", "TaskCreated", self.on_task_created)
        c.subscribe("TaskEscrow", "TaskAssigned", self.on_assigned_to_me, assignee=me)
        c.subscribe("TaskEscrow", "TaskAssigned", self.on_my_task_assigned, assigner=me)
        c.subscribe("TaskEscrow", "TaskDelivered", self.on_my_task_delivered, assigner=me)
        c.subscribe("TaskEscrow", "TaskCompleted", self.on_my_work_confirmed, assignee=me)
        c.subscribe("TaskEscrow", "TaskRequeued", self.on_requeued_from_me, previousAssignee=me)
        c.listen()
        threading.Thread(target=self.post_tasks, daemon=True).start()

    def balance(self):
        return iec(self.client.iec_balance(self.address))

    # ── commands ───────────────────────────────────────────────────────

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
        self.working.discard(number(task_id, "task id"))
        self.log("task", f"task #{task_id} delivered · waiting for its poster to confirm")

    def cmd_confirm(self, task_id):
        """confirm the work on one of my tasks - the reward goes to the worker"""
        self.client.send_tx("TaskEscrow", "confirmTask", number(task_id, "task id"))
        self.log("paid", f"task #{task_id} completed · reward released to the worker")

    def cmd_cancel(self, task_id):
        """withdraw one of my tasks nobody has taken yet - full refund"""
        self.client.send_tx("TaskEscrow", "cancelTask", number(task_id, "task id"))
        self.log("refund", f"task #{task_id} cancelled · balance {self.balance()}")

    # ── automatic mode ─────────────────────────────────────────────────

    def post_tasks(self):
        """Each simulated minute while running: Poisson arrivals, my share of the market's rate."""
        a = self.cfg["auto"]
        rate = a["arrival_rate"] / 60 / len(self.cfg["agents"])
        while True:
            time.sleep(a["step_s"])
            state = auto.state()
            if state and state["running"]:
                for _ in range(auto.poisson(self.rng, rate)):
                    self.attempt(self.post_random_task)

    def post_random_task(self):
        service = self.rng.choice(self.postable)
        reward = max(1, round(auto.sample_reward(self.cfg["services"][service]["reward"], self.rng) * 100))
        if self.client.iec_balance(self.address) < reward:
            self.log("warn", f"wanted {service} for {iec(reward)} but cannot afford it · balance {self.balance()}")
            return
        receipt = self.client.send_tx("TaskEscrow", "createTask", service, reward)
        task_id = self.client.events_in(receipt, "TaskEscrow", "TaskCreated")[0].args.taskId
        self.log("task", f"posted task #{task_id} {service} · {iec(reward)} locked · balance {self.balance()}")

    def finish(self, task_id):
        if task_id in self.working:  # not requeued in the meantime
            self.cmd_complete(task_id)

    def attempt(self, fn, *args):
        """Run an automatic action from a background thread; a revert is already logged."""
        try:
            fn(*args)
        except TxReverted:
            pass
        except Exception as e:
            self.log("warn", f"{type(e).__name__}: {e}")

    # ── events ─────────────────────────────────────────────────────────

    def on_funded(self, e):
        self.log("paid", f"received {iec(e.args.value)} from the master · balance {self.balance()}")

    def on_task_created(self, e):
        a = e.args
        if auto.state():
            return  # too many to list once the market runs on its own
        if a.assigner != self.address and a.service in self.me["services"]:
            self.log("event", f"task #{a.taskId} · {self.book.name(a.assigner)} needs {a.service}"
                              f" · {iec(a.reward)} - I offer this")

    def on_assigned_to_me(self, e):
        a = e.args
        self.working.add(a.taskId)
        if not auto.state():
            self.log("event", f"task #{a.taskId} {a.service} assigned to me (posted by {self.book.name(a.assigner)})"
                              f"\n→ complete {a.taskId}")
            return
        minutes = auto.sample_duration(self.cfg["services"][a.service]["duration"], self.rng)
        self.log("event", f"task #{a.taskId} {a.service} assigned to me (posted by {self.book.name(a.assigner)})"
                          f" · working on it for {minutes} min")
        timer = threading.Timer(minutes * self.cfg["auto"]["step_s"], self.attempt, [self.finish, a.taskId])
        timer.daemon = True
        timer.start()

    def on_my_task_assigned(self, e):
        self.log("event", f"my task #{e.args.taskId} {e.args.service} → {self.book.name(e.args.assignee)}")

    def on_my_task_delivered(self, e):
        a = e.args
        if auto.state():
            self.attempt(self.cmd_confirm, a.taskId)
            return
        self.log("event", f"my task #{a.taskId} delivered by {self.book.name(a.assignee)}"
                          f"\n→ confirm {a.taskId}")

    def on_my_work_confirmed(self, e):
        a = e.args
        self.log("paid", f"task #{a.taskId} confirmed by {self.book.name(a.assigner)} · paid {iec(a.reward)}"
                         f" · balance {self.balance()}")

    def on_requeued_from_me(self, e):
        self.working.discard(e.args.taskId)
        self.log("warn", f"the master took task #{e.args.taskId} back")


if __name__ == "__main__":
    config = load_config()
    if len(sys.argv) != 2 or sys.argv[1] not in config["agents"]:
        sys.exit(f"usage: python agent.py <name>   names: {', '.join(config['agents'])}")
    Agent(config, sys.argv[1]).run()
