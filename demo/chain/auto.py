"""Automatic mode, started by the master's `start`: the market runs like the simulator.

Time runs in simulated minutes (`auto.step_s` real seconds each). Every agent posts its own
tasks (Poisson arrivals, a share of `auto.arrival_rate` each), the master assigns the open
tasks FIFO, and agents complete and confirm their work on their own. Everything still goes
through transactions and events; out/auto.json only tells the terminals the mode is on.
"""

import json
import math
import random

from chain.config import AUTO_PATH

# not generated at random, as in the simulator: robots ask for it when their battery is low
NOT_RANDOM = {"BatteryCharging"}


def set_running(running):
    tmp = AUTO_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({"running": running}), encoding="utf-8")
    tmp.replace(AUTO_PATH)  # atomic, so terminals never read a half-written file


def state():
    """None before the first `start`, else {"running": bool}."""
    try:
        return json.loads(AUTO_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rng(cfg, name):
    """A random stream per terminal, reproducible from the seed."""
    return random.Random(f"{cfg['chain']['seed']}:{name}")


def poisson(rng, lam):
    """Number of arrivals in one step (Knuth's method; lam is small)."""
    k, p, limit = 0, rng.random(), math.exp(-lam)
    while p > limit:
        k += 1
        p *= rng.random()
    return k


def sample_reward(reward, rng):
    """IEC, lognormal around the median like the simulator's sample_reward."""
    if reward["sigma_g"] == 0:
        return reward["median"]
    return rng.lognormvariate(math.log(reward["median"]), reward["sigma_g"])


def sample_duration(duration, rng):
    """Simulated minutes: a scalar, or a normal with a minimum like the simulator's sample_duration."""
    if isinstance(duration, (int, float)):
        return int(round(duration))
    if duration["sd"] == 0:
        return int(round(duration["mean"]))
    return int(round(max(rng.gauss(duration["mean"], duration["sd"]), duration["min"])))
