"""Smoke test for the 4 contracts against a running Ganache.

Usage (from demo/, with Ganache running: npm run ganache):
    python smoke_test.py

Deploys the contracts, funds two agents from the master, registers them and their
services, then runs one task that completes, one that fails, and checks that every
rule that should revert does. Exits non-zero on the first broken expectation.
"""

import sys

from web3 import Web3
from web3.exceptions import ContractLogicError, Web3RPCError

from chain.compile import compile_contracts, load_config
from chain.wallets import derive_account

HUMAN, ROBOT = 0, 1


def check(condition, message):
    if not condition:
        print(f"  FAIL  {message}")
        sys.exit(1)
    print(f"  ok    {message}")


class Node:
    """A wallet that signs its own transactions (like a separate agent process would)."""

    def __init__(self, w3, account, name):
        self.w3, self.account, self.name = w3, account, name
        self.address = account.address

    def send(self, fn, value=0):
        tx = fn.build_transaction({
            "from": self.address,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "value": value,
        })
        signed = self.account.sign_transaction(tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(
            self.w3.eth.send_raw_transaction(signed.raw_transaction))
        if receipt.status != 1:
            raise RuntimeError(f"{self.name}: tx reverted")
        return receipt

    def send_eth(self, to, amount_eth):
        tx = {
            "to": to, "value": Web3.to_wei(amount_eth, "ether"), "gas": 21000,
            "gasPrice": self.w3.eth.gas_price, "chainId": self.w3.eth.chain_id,
            "nonce": self.w3.eth.get_transaction_count(self.address),
        }
        signed = self.account.sign_transaction(tx)
        self.w3.eth.wait_for_transaction_receipt(self.w3.eth.send_raw_transaction(signed.raw_transaction))


def expect_revert(fn, sender, reason):
    """The call must revert with `reason` (checked with eth_call, so nothing is mined)."""
    try:
        fn.call({"from": sender})
    # Ganache reports reverts as a generic RPC error, other nodes as ContractLogicError
    except (ContractLogicError, Web3RPCError) as e:
        check(reason in str(e), f"reverts: {reason}")
        return
    check(False, f"reverts: {reason} (it did not revert)")


def deploy(w3, master, compiled, name, *args):
    artifact = compiled[name]
    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    receipt = master.send(contract.constructor(*args))
    print(f"  deployed {name:<16} {receipt.contractAddress}  gas {receipt.gasUsed}")
    return w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])


def main():
    cfg = load_config()
    chain_cfg = cfg["chain"]
    w3 = Web3(Web3.HTTPProvider(chain_cfg["rpc"]))
    if not w3.is_connected():
        print(f"cannot reach Ganache at {chain_cfg['rpc']} - start it with: npm run ganache")
        sys.exit(1)

    print("compile")
    compiled = compile_contracts(chain_cfg["solc_version"], chain_cfg["evm_version"])

    # Ganache --wallet.deterministic: account 0 is the master
    master_key = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
    master = Node(w3, w3.eth.account.from_key(master_key), "master")
    supply = cfg["token"]["total_supply"] * 100  # 2 decimals

    print("deploy")
    token = deploy(w3, master, compiled, "IECToken", supply, master.address)
    agent_reg = deploy(w3, master, compiled, "AgentRegistry")
    service_reg = deploy(w3, master, compiled, "ServiceRegistry", agent_reg.address)
    escrow = deploy(w3, master, compiled, "TaskEscrow",
                    token.address, agent_reg.address, service_reg.address, master.address)
    check(token.functions.balanceOf(master.address).call() == supply, "master holds the whole supply")

    print("fund and register agents")
    robot = Node(w3, derive_account(chain_cfg["seed"], "robot_1"), "robot_1")
    human = Node(w3, derive_account(chain_cfg["seed"], "human_1"), "human_1")
    outsider = Node(w3, derive_account(chain_cfg["seed"], "outsider"), "outsider")
    wealth = 2000 * 100
    for node in (robot, human, outsider):
        master.send_eth(node.address, chain_cfg["gas_eth_per_agent"])
    for node in (robot, human):
        master.send(token.functions.transfer(node.address, wealth))
        check(token.functions.balanceOf(node.address).call() == wealth, f"{node.name} has 2000 IEC")

    expect_revert(service_reg.functions.registerService("LabCleaning", "cleaning", 950),
                  robot.address, "not registered")
    robot.send(agent_reg.functions.registerAgent("robot_1", ROBOT))
    human.send(agent_reg.functions.registerAgent("human_1", HUMAN))
    expect_revert(agent_reg.functions.registerAgent("robot_1", ROBOT), robot.address, "already registered")
    check(tuple(agent_reg.functions.getAgent(robot.address).call()) == ("robot_1", ROBOT),
          "getAgent returns id and kind")

    robot.send(service_reg.functions.registerService("ItemTransport", "logistics", 950))
    human.send(service_reg.functions.registerService("LabCleaning", "cleaning", 950))
    expect_revert(service_reg.functions.registerService("LabCleaning", "cleaning", 1001),
                  human.address, "skill must be 0-1000")
    check(service_reg.functions.getProviders("LabCleaning").call() == [human.address],
          "LabCleaning providers = [human_1]")

    expect_revert(escrow.functions.createTask("LabCleaning", 140_00), robot.address, "escrow not approved")
    for node in (robot, human):
        node.send(token.functions.approve(escrow.address, 2**256 - 1))

    print("task 1: robot posts LabCleaning, human completes it")
    expect_revert(escrow.functions.createTask("LabCleaning", 140_00), outsider.address, "not registered")
    expect_revert(escrow.functions.createTask("LabCleaning", wealth + 1), robot.address, "insufficient balance")
    robot.send(escrow.functions.createTask("LabCleaning", 140_00))
    check(token.functions.balanceOf(robot.address).call() == wealth - 140_00, "robot paid 140 into escrow")
    check(escrow.functions.totalLocked().call() == 140_00, "escrow locks 140")

    expect_revert(escrow.functions.assignTask(1, human.address), robot.address, "only operator")
    expect_revert(escrow.functions.assignTask(1, robot.address), master.address, "assignee is the assigner")
    master.send(escrow.functions.assignTask(1, human.address))
    expect_revert(escrow.functions.completeTask(1), robot.address, "not assignee")
    human.send(escrow.functions.completeTask(1))
    check(token.functions.balanceOf(human.address).call() == wealth + 140_00, "human earned 140")
    check(escrow.functions.totalLocked().call() == 0, "escrow empty again")
    expect_revert(escrow.functions.completeTask(1), human.address, "task not assigned")

    print("task 2: human posts ItemTransport, robot fails it -> refund")
    human.send(escrow.functions.createTask("ItemTransport", 80_00))
    expect_revert(escrow.functions.assignTask(2, outsider.address), master.address, "assignee not registered")
    robot_only = Node(w3, derive_account(chain_cfg["seed"], "robot_2"), "robot_2")
    master.send_eth(robot_only.address, chain_cfg["gas_eth_per_agent"])
    robot_only.send(agent_reg.functions.registerAgent("robot_2", ROBOT))
    expect_revert(escrow.functions.assignTask(2, robot_only.address), master.address,
                  "assignee does not offer service")
    master.send(escrow.functions.assignTask(2, robot.address))
    master.send(escrow.functions.requeueTask(2))
    master.send(escrow.functions.assignTask(2, robot.address))
    robot.send(escrow.functions.failTask(2))
    check(token.functions.balanceOf(human.address).call() == wealth + 140_00, "human refunded 80")

    print("task 3: robot posts, then cancels")
    robot.send(escrow.functions.createTask("LabCleaning", 50_00))
    expect_revert(escrow.functions.cancelTask(3), human.address, "not assigner")
    robot.send(escrow.functions.cancelTask(3))
    check(token.functions.balanceOf(robot.address).call() == wealth - 140_00, "robot refunded 50")

    print("conservation")
    total = sum(token.functions.balanceOf(a).call() for a in (master.address, robot.address, human.address))
    total += token.functions.balanceOf(escrow.address).call()
    check(total == supply, "master + agents + escrow = total supply")

    events = escrow.events.TaskCompleted().get_logs(from_block=0)
    check(len(events) == 1 and events[0].args.taskId == 1, "TaskCompleted event readable via logs")

    print("\nall checks passed")


if __name__ == "__main__":
    main()
