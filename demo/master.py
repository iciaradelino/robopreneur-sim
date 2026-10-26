"""Master node terminal: deploys the contracts, funds the agents and assigns tasks.

The master is the operator: after `deploy` it holds the whole IEC supply, and it is the
only wallet allowed to assign and requeue tasks. Nothing happens until you type a command;
events from the agents' terminals are logged as they arrive.
"""

from eth_account import Account

from chain.compile import compile_contracts
from chain.config import DEPLOYMENTS_PATH, load_config
from chain.log import iec
from chain.node import Node, number

KINDS = ["human", "robot"]


class Master(Node):
    def __init__(self, cfg):
        super().__init__(cfg, "master", Account.from_key(cfg["chain"]["master_key"]))
        self.book.add(self.address, "master")
        self.log.banner(f"MASTER · {self.address}")

    # ── commands ───────────────────────────────────────────────────────

    def cmd_deploy(self):
        """compile and deploy the 4 contracts; the master gets the whole IEC supply"""
        if self.client.contracts:
            raise ValueError("already deployed - restart Ganache for a fresh chain")
        DEPLOYMENTS_PATH.unlink(missing_ok=True)
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
        self.log("deploy", f"agents can connect now · master holds {iec(c.iec_balance(self.address))}")

        c.subscribe("AgentRegistry", "AgentRegistered", self.on_agent_registered)
        c.subscribe("ServiceRegistry", "ServiceRegistered", self.on_service_registered)
        c.subscribe("TaskEscrow", "TaskCreated", self.on_task_created)
        c.subscribe("TaskEscrow", "TaskDelivered", self.on_task_delivered)
        c.subscribe("TaskEscrow", "TaskCompleted", self.on_task_completed)
        c.subscribe("TaskEscrow", "TaskCancelled", self.on_task_cancelled)
        c.listen()

    def cmd_fund(self, agent, amount=None):
        """send gas ETH (if needed) and IEC to an agent or `all` (default: its initial_wealth)"""
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

    # ── events ─────────────────────────────────────────────────────────

    def on_agent_registered(self, e):
        self.log("event", f"{e.args.agentId} joined as {KINDS[e.args.kind]}")

    def on_service_registered(self, e):
        self.log("event", f"{self.book.name(e.args.provider)} offers {e.args.service}")

    def on_task_created(self, e):
        a = e.args
        providers = [self.book.name(p) for p in self.client.call("ServiceRegistry", "getProviders", a.service)
                     if p != a.assigner]
        self.log("event", f"task #{a.taskId} · {self.book.name(a.assigner)} needs {a.service} · {iec(a.reward)} locked\n"
                          f"providers: {', '.join(providers) or 'nobody yet'}"
                          + (f" → assign {a.taskId} {providers[0]}" if providers else ""))

    def on_task_delivered(self, e):
        a = e.args
        self.log("event", f"task #{a.taskId} delivered by {self.book.name(a.assignee)}"
                          f" · waiting for {self.book.name(a.assigner)} to confirm")

    def on_task_completed(self, e):
        a = e.args
        self.log("paid", f"task #{a.taskId} completed · {self.book.name(a.assignee)} paid {iec(a.reward)}"
                         f" by {self.book.name(a.assigner)}")

    def on_task_cancelled(self, e):
        self.log("refund", f"task #{e.args.taskId} cancelled · {iec(e.args.refunded)} back to"
                           f" {self.book.name(e.args.assigner)}")


if __name__ == "__main__":
    Master(load_config()).run()
