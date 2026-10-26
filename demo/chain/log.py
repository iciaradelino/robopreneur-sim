"""Coloured, prefixed terminal logger, mirrored to out/logs/<node>.log."""

import sys
import time

from colorama import Fore, Style, just_fix_windows_console

from chain.config import OUT_DIR

NODE_COLORS = {
    "master": Fore.LIGHTWHITE_EX,
    "robot_1": Fore.CYAN,
    "robot_2": Fore.LIGHTBLUE_EX,
    "human_1": Fore.YELLOW,
    "human_2": Fore.LIGHTGREEN_EX,
}
TAG_COLORS = {
    "init": Fore.WHITE,
    "deploy": Fore.LIGHTYELLOW_EX,
    "tx": Fore.GREEN,
    "revert": Fore.LIGHTRED_EX,
    "event": Fore.CYAN,
    "task": Fore.LIGHTWHITE_EX,
    "paid": Fore.LIGHTGREEN_EX,
    "refund": Fore.LIGHTRED_EX,
    "status": Fore.LIGHTBLUE_EX,
    "warn": Fore.RED,
}
NODE_WIDTH, TAG_WIDTH = 8, 7
INDENT = " " * (8 + NODE_WIDTH + TAG_WIDTH + 3)  # timestamp + node + tag + spaces


def iec(units):
    """Format token base units (2 decimals) as IEC."""
    return f"{units / 100:,.2f} IEC"


def short(address):
    return f"{address[:6]}…{address[-4:]}"


class Logger:
    def __init__(self, node):
        just_fix_windows_console()
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        self.node = node
        self.color = NODE_COLORS.get(node, Fore.WHITE)
        (OUT_DIR / "logs").mkdir(parents=True, exist_ok=True)
        self.file = open(OUT_DIR / "logs" / f"{node}.log", "w", encoding="utf-8")

    def __call__(self, tag, message):
        ts = time.strftime("%H:%M:%S")
        first, *rest = str(message).split("\n")
        print(f"{Style.DIM}{ts}{Style.RESET_ALL} "
              f"{self.color}{self.node:<{NODE_WIDTH}}{Style.RESET_ALL} "
              f"{TAG_COLORS.get(tag, Fore.WHITE)}{tag:<{TAG_WIDTH}}{Style.RESET_ALL} {first}", flush=True)
        for line in rest:
            print(INDENT + line, flush=True)
        self.file.write(f"[{ts}][{self.node}][{tag}] " + f"\n{INDENT}".join([first, *rest]) + "\n")
        self.file.flush()

    def banner(self, title):
        text = f"{'═' * 60}\n  {title}\n{'═' * 60}"
        print(f"{self.color}{text}{Style.RESET_ALL}", flush=True)
        self.file.write(text + "\n")
        self.file.flush()
