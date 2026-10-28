"""Chain client: the only module that talks to the blockchain.

Each process (master or agent) owns one ChainClient with its own key, so every
transaction it sends is signed by that wallet and nonces never collide between terminals.
"""

import json
import re
import threading
import time

from web3 import Web3
from web3.exceptions import ContractLogicError, Web3RPCError
from web3.logs import DISCARD

from chain.config import DEPLOYMENTS_PATH
from chain.log import short


class TxReverted(Exception):
    """The transaction was rejected (a contract rule or the node); nothing changed on-chain."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def revert_reason(error):
    text = str(error)
    # Ganache: "...processing transaction: revert not registered" -> "not registered".
    # Node errors (e.g. no gas money) only carry a message.
    match = re.search(r"revert\s+([^'\"\\]+)", text) or re.search(r"'message': '([^']+)'", text)
    return match.group(1) if match else text


def fmt_arg(value):
    if isinstance(value, str) and Web3.is_address(value):
        return short(value)
    if isinstance(value, int) and value >= 2**255:
        return "max"
    return repr(value)


class ChainClient:
    def __init__(self, cfg, account, log, book):
        self.cfg = cfg
        self.account = account
        self.address = account.address
        self.log = log
        self.book = book
        self.contracts = {}
        self.subscriptions = []
        self.nonce = None  # tracked locally: Ganache's "pending" count can lag behind

        self.w3 = Web3(Web3.HTTPProvider(cfg["chain"]["rpc"], request_kwargs={"timeout": 10}))
        self.wait_until(self.w3.is_connected, f"waiting for the chain at {cfg['chain']['rpc']} …", 1)
        self.log("init", f"connected to chain {self.w3.eth.chain_id} · block {self.w3.eth.block_number}")

    def wait_until(self, condition, message, interval=0.5):
        """Block until condition() is true, logging `message` once while waiting."""
        if not condition():
            self.log("init", message)
            while not condition():
                time.sleep(interval)

    # ── contracts ──────────────────────────────────────────────────────

    def contract(self, name):
        if name not in self.contracts:
            raise ValueError("contracts not deployed yet - run `deploy` in the master terminal")
        return self.contracts[name]

    def deploy(self, name, artifact, *args):
        factory = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        receipt = self._sign_and_send(factory.constructor(*args).build_transaction(self._tx_base()))
        self.contracts[name] = self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])
        self.log("deploy", f"{name:<16} {receipt.contractAddress} · block {receipt.blockNumber}"
                           f" · gas {receipt.gasUsed:,}")

    def save_deployments(self):
        data = {"master": self.address,
                "contracts": {name: {"address": c.address, "abi": c.abi} for name, c in self.contracts.items()}}
        tmp = DEPLOYMENTS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(DEPLOYMENTS_PATH)  # atomic, so agents never read a half-written file

    def load_deployments(self):
        """Wait until the master has deployed on *this* chain, then load the contracts."""
        data = {}

        def deployed():
            try:
                data.update(json.loads(DEPLOYMENTS_PATH.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                return False
            # a file left from an earlier run points at addresses with no code on a fresh chain
            return all(self.w3.eth.get_code(c["address"]) for c in data["contracts"].values())

        self.wait_until(deployed, "waiting for the master to deploy the contracts …")
        for name, c in data["contracts"].items():
            self.contracts[name] = self.w3.eth.contract(address=c["address"], abi=c["abi"])
        return data

    # ── transactions ───────────────────────────────────────────────────

    def _tx_base(self):
        # only this process signs with this key, so the next nonce is always our own count
        if self.nonce is None:
            self.nonce = self.w3.eth.get_transaction_count(self.address, "latest")
        return {"from": self.address, "nonce": self.nonce}

    def _sign_and_send(self, tx):
        signed = self.account.sign_transaction(tx)
        try:
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        except Web3RPCError:
            self.nonce = None  # e.g. a nonce mismatch: resync from the chain next time
            raise
        self.nonce += 1
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise TxReverted("reverted on-chain")
        return receipt

    def send_tx(self, contract, fn_name, *args):
        """Sign and send contract.fn_name(*args) from this wallet. Raises TxReverted."""
        call = f"{contract}.{fn_name}({', '.join(fmt_arg(a) for a in args)})"
        fn = self.contract(contract).functions[fn_name](*args)
        try:
            # gas estimation runs the call first, so a broken rule is caught before sending
            receipt = self._sign_and_send(fn.build_transaction(self._tx_base()))
        except (ContractLogicError, Web3RPCError, TxReverted) as e:
            reason = e.reason if isinstance(e, TxReverted) else revert_reason(e)
            self.log("revert", f"✗ {call} → {reason}")
            raise TxReverted(reason) from None
        self.log("tx", f"✓ {call} · block {receipt.blockNumber} · gas {receipt.gasUsed:,}"
                       f" · {receipt.transactionHash.hex()[:10]}…")
        return receipt

    def send_eth(self, to, amount_eth):
        tx = self._tx_base() | {
            "to": to, "value": Web3.to_wei(amount_eth, "ether"), "gas": 21000,
            "gasPrice": self.w3.eth.gas_price, "chainId": self.w3.eth.chain_id,
        }
        receipt = self._sign_and_send(tx)
        self.log("tx", f"✓ send {amount_eth} ETH → {self.book.name(to)} (gas money) · block {receipt.blockNumber}")

    def call(self, contract, fn_name, *args):
        """Read-only view call: free, no transaction."""
        return self.contract(contract).functions[fn_name](*args).call()

    def events_in(self, receipt, contract, event):
        # DISCARD: the receipt also holds other contracts' logs (e.g. the token's Transfer)
        return getattr(self.contract(contract).events, event)().process_receipt(receipt, errors=DISCARD)

    def iec_balance(self, address):
        return self.call("IECToken", "balanceOf", address)

    def eth_balance(self, address):
        return Web3.from_wei(self.w3.eth.get_balance(address), "ether")

    # ── events ─────────────────────────────────────────────────────────

    def subscribe(self, contract, event, handler, **argument_filters):
        """Call handler(event) for every new `event` matching the indexed filters."""
        self.subscriptions.append((self.contract(contract), event, handler, argument_filters or None))

    def listen(self):
        """Deliver subscribed events from the next block on, from a background thread."""
        last_block = self.w3.eth.block_number

        def loop():
            nonlocal last_block
            while True:
                try:
                    latest = self.w3.eth.block_number
                    if latest > last_block:
                        found = []
                        for contract, event, handler, filters in self.subscriptions:
                            logs = getattr(contract.events, event)().get_logs(
                                from_block=last_block + 1, to_block=latest, argument_filters=filters)
                            found += [(e.blockNumber, e.logIndex, handler, e) for e in logs]
                        last_block = latest
                        # deliver in chain order, whatever subscription they came from
                        for *_, handler, e in sorted(found, key=lambda f: f[:2]):
                            handler(e)
                except Exception as e:  # keep listening whatever one poll does
                    self.log("warn", f"event polling failed: {e}")
                time.sleep(self.cfg["chain"]["poll_interval_s"])

        threading.Thread(target=loop, daemon=True).start()
