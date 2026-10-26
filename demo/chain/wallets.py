"""Deterministic agent wallets: the same seed + agent name always gives the same key.

These keys are for the local demo only - never use them on a real network.
"""

from eth_account import Account
from eth_utils import keccak

from chain.log import short


def derive_account(seed, agent_name):
    """Return an eth_account LocalAccount derived from the seed and the agent name."""
    private_key = keccak(text=f"robopreneur-demo:{seed}:{agent_name}")
    return Account.from_key(private_key)


class AddressBook:
    """Address -> readable name, so logs say `robot_1` instead of `0x3f…a1`.

    Every process can build it on its own: agent addresses are derived from the config.
    """

    def __init__(self, cfg):
        seed = cfg["chain"]["seed"]
        self.addresses = {name: derive_account(seed, name).address for name in cfg["agents"]}
        self.names = {addr: name for name, addr in self.addresses.items()}

    def add(self, address, name):
        self.addresses[name] = address
        self.names[address] = name

    def name(self, address):
        return self.names.get(address, short(address))
