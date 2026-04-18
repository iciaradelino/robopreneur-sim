# validates a config.yaml file against the expected simulation format
# usage: python scripts/validate_config.py <path_to_config.yaml>
# exits with code 0 on success, 1 on failure

import sys
import os
from pathlib import Path

import yaml

# ── helpers ──────────────────────────────────────────────────────────────────

ERRORS = []
WARNINGS = []

def err(msg):
    ERRORS.append(f"  [error]   {msg}")

def warn(msg):
    WARNINGS.append(f"  [warning] {msg}")

def check(condition, msg):
    if not condition:
        err(msg)
    return condition

def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def is_positive_number(v):
    return is_number(v) and v > 0

def is_fraction(v):
    return is_number(v) and 0.0 <= v <= 1.0


# ── section validators ────────────────────────────────────────────────────────

def validate_simulation(cfg):
    s = cfg.get("simulation")
    if not check(isinstance(s, dict), "simulation: section missing or not a mapping"):
        return
    check(isinstance(s.get("seed"), int), "simulation.seed: must be an integer")
    check(isinstance(s.get("duration"), int) and s.get("duration", 0) > 0,
          "simulation.duration: must be a positive integer")


def validate_world(cfg):
    w = cfg.get("world")
    if not check(isinstance(w, dict), "world: section missing or not a mapping"):
        return
    check(is_positive_number(w.get("size")), "world.size: must be a positive number")
    check(isinstance(w.get("boundaries"), bool), "world.boundaries: must be a boolean")
    cs = w.get("charging_station")
    check(
        isinstance(cs, list) and len(cs) == 2 and all(is_number(v) for v in cs),
        "world.charging_station: must be a list of two numbers, e.g. [50, 50]",
    )


def validate_duration_field(duration, path):
    """duration can be a plain number or {mean, sd, min}."""
    if is_positive_number(duration):
        return
    if isinstance(duration, dict):
        check(is_positive_number(duration.get("mean")), f"{path}.duration.mean: must be a positive number")
        check(is_number(duration.get("sd")) and duration.get("sd", -1) >= 0,
              f"{path}.duration.sd: must be a non-negative number")
        check(is_positive_number(duration.get("min")), f"{path}.duration.min: must be a positive number")
    else:
        err(f"{path}.duration: must be a positive number or {{mean, sd, min}} mapping")


def validate_service_def(name, svc):
    path = f"services.{name}"
    if not check(isinstance(svc, dict), f"{path}: must be a mapping"):
        return

    valid_categories = {"maintenance", "cleaning", "transport", "security"}
    cat = svc.get("category")
    check(cat in valid_categories,
          f"{path}.category: '{cat}' is not valid, expected one of {sorted(valid_categories)}")

    reward = svc.get("reward")
    if check(isinstance(reward, dict), f"{path}.reward: must be a mapping {{median, sigma_g}}"):
        check(is_number(reward.get("median")), f"{path}.reward.median: must be a number")
        check(is_number(reward.get("sigma_g")) and reward.get("sigma_g", -1) >= 0,
              f"{path}.reward.sigma_g: must be a non-negative number")

    phases = svc.get("phases")
    if not check(isinstance(phases, dict), f"{path}.phases: must be a mapping"):
        return

    waypoints = phases.get("waypoints")
    if check(isinstance(waypoints, list) and len(waypoints) > 0,
             f"{path}.phases.waypoints: must be a non-empty list"):
        valid_point_types = {"charging_station", "random_in_world"}
        for i, wp in enumerate(waypoints):
            wp_path = f"{path}.phases.waypoints[{i}]"
            if not check(isinstance(wp, dict), f"{wp_path}: must be a mapping"):
                continue
            check(isinstance(wp.get("id"), str) and wp.get("id"),
                  f"{wp_path}.id: must be a non-empty string")
            point = wp.get("point")
            if check(isinstance(point, dict), f"{wp_path}.point: must be a mapping {{type: ...}}"):
                check(point.get("type") in valid_point_types,
                      f"{wp_path}.point.type: '{point.get('type')}' not in {sorted(valid_point_types)}")
            validate_duration_field(wp.get("duration"), wp_path)
            check(is_fraction(wp.get("fail")), f"{wp_path}.fail: must be a number between 0 and 1")

    check(isinstance(phases.get("in_order"), bool), f"{path}.phases.in_order: must be a boolean")
    check(isinstance(phases.get("repeat"), int) and phases.get("repeat", -1) >= 0,
          f"{path}.phases.repeat: must be a non-negative integer")


def validate_services_section(cfg):
    svcs = cfg.get("services")
    if not check(isinstance(svcs, dict), "services: section missing or not a mapping"):
        return {}
    for name, svc in svcs.items():
        validate_service_def(name, svc)
    return set(svcs.keys())


def validate_agent_services(agent_services, agent_path, known_services):
    if not check(isinstance(agent_services, list) and len(agent_services) > 0,
                 f"{agent_path}.services: must be a non-empty list"):
        return
    for i, entry in enumerate(agent_services):
        ep = f"{agent_path}.services[{i}]"
        if not check(isinstance(entry, dict) and len(entry) == 1,
                     f"{ep}: each entry must be a single-key mapping {{ServiceName: {{skill: ...}}}}"):
            continue
        svc_name, svc_opts = next(iter(entry.items()))
        if known_services:
            check(svc_name in known_services,
                  f"{ep}: service '{svc_name}' is not defined in the services section")
        if check(isinstance(svc_opts, dict), f"{ep}.{svc_name}: value must be a mapping {{skill: ...}}"):
            check(is_fraction(svc_opts.get("skill")),
                  f"{ep}.{svc_name}.skill: must be a number between 0 and 1")


def validate_humans(cfg, known_services):
    humans = cfg.get("humans")
    if not check(isinstance(humans, dict), "humans: section missing or not a mapping"):
        return
    for hname, h in humans.items():
        path = f"humans.{hname}"
        if not check(isinstance(h, dict), f"{path}: must be a mapping"):
            continue
        check(isinstance(h.get("num"), int) and h.get("num", 0) > 0,
              f"{path}.num: must be a positive integer")
        check(is_number(h.get("initial_wealth")),
              f"{path}.initial_wealth: must be a number")
        check(isinstance(h.get("schedule"), bool),
              f"{path}.schedule: must be a boolean")
        check(is_positive_number(h.get("speed")), f"{path}.speed: must be a positive number")
        validate_agent_services(h.get("services"), path, known_services)


def validate_robots(cfg, known_services):
    robots = cfg.get("robots")
    if not check(isinstance(robots, dict), "robots: section missing or not a mapping"):
        return
    for rname, r in robots.items():
        path = f"robots.{rname}"
        if not check(isinstance(r, dict), f"{path}: must be a mapping"):
            continue
        check(isinstance(r.get("num"), int) and r.get("num", 0) > 0,
              f"{path}.num: must be a positive integer")
        check(is_number(r.get("initial_wealth")), f"{path}.initial_wealth: must be a number")
        ib = r.get("initial_battery")
        check(is_number(ib) and 0 < ib <= 100,
              f"{path}.initial_battery: must be a number between 0 and 100")
        check(is_positive_number(r.get("speed")), f"{path}.speed: must be a positive number")
        check(isinstance(r.get("random_walk_interval"), int) and r.get("random_walk_interval", 0) > 0,
              f"{path}.random_walk_interval: must be a positive integer")
        validate_agent_services(r.get("services"), path, known_services)


def validate_battery(cfg):
    b = cfg.get("battery")
    if not check(isinstance(b, dict), "battery: section missing or not a mapping"):
        return
    for key in ("recharge_rate", "drain_rate", "recharge_trigger", "min_accept_task"):
        check(is_positive_number(b.get(key)), f"battery.{key}: must be a positive number")


def validate_tasks(cfg):
    t = cfg.get("tasks")
    if not check(isinstance(t, dict), "tasks: section missing or not a mapping"):
        return
    check(is_positive_number(t.get("arrival_rate")), "tasks.arrival_rate: must be a positive number")
    check(is_positive_number(t.get("proximity_threshold")),
          "tasks.proximity_threshold: must be a positive number")


def validate_top_level_scalars(cfg):
    valid_policies = {"random"}
    valid_pricing = {"fixed"}
    ap = cfg.get("assignment_policy")
    check(ap in valid_policies,
          f"assignment_policy: '{ap}' is not valid, expected one of {sorted(valid_policies)}")
    pm = cfg.get("pricing_model")
    check(pm in valid_pricing,
          f"pricing_model: '{pm}' is not valid, expected one of {sorted(valid_pricing)}")


def validate_required_top_level_keys(cfg):
    required = {"simulation", "world", "humans", "robots", "battery",
                "tasks", "assignment_policy", "pricing_model", "services"}
    missing = required - set(cfg.keys())
    if missing:
        for k in sorted(missing):
            err(f"missing required top-level key: '{k}'")
        return False
    return True


# ── main ──────────────────────────────────────────────────────────────────────

def validate(config_path: str) -> bool:
    if not os.path.exists(config_path):
        print(f"error: file not found: {config_path}")
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"error: failed to parse yaml: {e}")
            return False

    if not check(isinstance(cfg, dict), "config must be a yaml mapping at the top level"):
        print("\n".join(ERRORS))
        return False

    if not validate_required_top_level_keys(cfg):
        print("\n".join(ERRORS))
        return False

    known_services = validate_services_section(cfg)
    validate_simulation(cfg)
    validate_world(cfg)
    validate_battery(cfg)
    validate_tasks(cfg)
    validate_top_level_scalars(cfg)
    validate_humans(cfg, known_services)
    validate_robots(cfg, known_services)

    return len(ERRORS) == 0


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/validate_config.py <path_to_config.yaml>")
        print("\nexample:")
        print("  python scripts/validate_config.py experiments/exp-00/scenario-a/config.yaml")
        sys.exit(1)

    config_path = sys.argv[1]
    print(f"validating: {config_path}")
    print("-" * 60)

    ok = validate(config_path)

    if WARNINGS:
        print("warnings:")
        for w in WARNINGS:
            print(w)

    if ERRORS:
        print("errors:")
        for e in ERRORS:
            print(e)
        print("-" * 60)
        print(f"validation failed — {len(ERRORS)} error(s) found.")
        sys.exit(1)
    else:
        print("validation passed — config looks good.")
        sys.exit(0)


if __name__ == "__main__":
    main()
