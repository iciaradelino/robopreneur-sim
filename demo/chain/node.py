"""Base for the master and agent terminals: a wallet, a chain client and a command prompt.

Every `cmd_<name>` method is a command: its parameters are the arguments and its
docstring is the help text. Events from other terminals are printed above the prompt.
"""

import inspect
import shlex

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import patch_stdout

from chain.client import ChainClient, TxReverted
from chain.log import Logger, iec
from chain.wallets import AddressBook

STATUS = ["-", "open", "assigned", "delivered", "completed", "cancelled"]
NO_ADDRESS = "0x" + "0" * 40


def number(value, what):
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{what} must be a whole number, got {value!r}") from None


def usage(fn):
    return " ".join(f"<{p.name}>" if p.default is p.empty else f"[{p.name}]"
                    for p in inspect.signature(fn).parameters.values())


class Node:
    def __init__(self, cfg, name, account):
        self.cfg = cfg
        self.name = name
        self.log = Logger(name)
        self.book = AddressBook(cfg)
        self.client = ChainClient(cfg, account, self.log, self.book)
        self.address = self.client.address

    def agent_address(self, agent):
        if agent not in self.cfg["agents"]:
            raise ValueError(f"unknown agent {agent!r}; agents: {', '.join(self.cfg['agents'])}")
        return self.book.addresses[agent]

    # ── commands every terminal has ────────────────────────────────────

    def cmd_tasks(self):
        """list every task in the escrow"""
        count = self.client.call("TaskEscrow", "taskCount")
        rows = []
        for task_id in range(1, count + 1):
            assigner, assignee, service, reward, status, *_ = self.client.call("TaskEscrow", "getTask", task_id)
            worker = self.book.name(assignee) if assignee != NO_ADDRESS else "-"
            rows.append(f"#{task_id:<3} {STATUS[status]:<10} {service:<19} {iec(reward):>12}"
                        f"  {self.book.name(assigner)} → {worker}")
        self.log("task", "tasks\n" + "\n".join(rows) if rows else "no tasks yet")

    def cmd_balances(self):
        """IEC and gas ETH of every wallet, and the total supply check"""
        c = self.client
        supply = c.call("IECToken", "totalSupply")
        total = 0
        lines = []
        for name in ["master", *self.cfg["agents"], "escrow"]:
            address = self.book.addresses[name]
            balance = c.iec_balance(address)
            total += balance
            lines.append(f"{name:<9} {iec(balance):>16}  {c.eth_balance(address):>7.2f} ETH")
        ok ="✓ conserved" if total == supply else f"✗ supply is {iec(supply)}"
        self.log("status", "balances\n" + "\n".join(lines) + f"\n{'total':<9} {iec(total):>16}  {ok}")

    def cmd_providers(self, service):
        """who offers a service"""
        providers = self.client.call("ServiceRegistry", "getProviders", service)
        self.log("status", f"{service}: {', '.join(map(self.book.name, providers)) or 'nobody'}")

    # ── prompt ─────────────────────────────────────────────────────────

    def commands(self):
        found = {}
        for cls in type(self).__mro__:  # own commands first, then the shared ones
            for attr in vars(cls):
                if attr.startswith("cmd_"):
                    found.setdefault(attr[4:], getattr(self, attr))
        return found

    def print_help(self, commands):
        lines = [f"{name} {usage(fn)}".ljust(28) + fn.__doc__ for name, fn in commands.items()]
        self.log("init", "commands\n" + "\n".join(lines + ["help".ljust(28) + "this list",
                                                            "exit".ljust(28) + "leave"]))

    def run(self):
        commands = self.commands()
        session = PromptSession(completer=WordCompleter([*commands, "help", "exit"]))
        self.log("init", "ready - type `help` for commands")
        with patch_stdout(raw=True):
            while True:
                try:
                    line = session.prompt(f"{self.name}> ")
                except (EOFError, KeyboardInterrupt):
                    return
                try:
                    name, *args = shlex.split(line) or [""]
                    if not name:
                        continue
                    if name in ("exit", "quit"):
                        return
                    if name == "help":
                        self.print_help(commands)
                    elif name not in commands:
                        self.log("warn", f"unknown command {name!r} - type `help`")
                    else:
                        fn = commands[name]
                        try:
                            inspect.signature(fn).bind(*args)
                        except TypeError:
                            self.log("warn", f"usage: {name} {usage(fn)}")
                            continue
                        fn(*args)
                except TxReverted:
                    pass  # the client already logged why
                except ValueError as e:
                    self.log("warn", str(e))
                except Exception as e:
                    self.log("warn", f"{type(e).__name__}: {e}")
