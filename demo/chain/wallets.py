"""Deterministic agent wallets: the same seed + agent name always gives the same key.

These keys are for the local demo only - never use them on a real network.
"""

from eth_account import Account
from eth_utils import keccak


def derive_account(seed, agent_name):
    """Return an eth_account LocalAccount derived from the seed and the agent name."""
    private_key = keccak(text=f"robopreneur-demo:{seed}:{agent_name}")
    return Account.from_key(private_key)
