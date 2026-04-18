import numpy as np

def sample_reward(reward_config, rng):
    """sample reward from lognormal distribution"""
    median = reward_config['median']
    sigma_g = reward_config['sigma_g']
    
    if sigma_g == 0:
        return median  # deterministic
    
    # lognormal parameters: mu = ln(median), sigma = sigma_g
    mu = np.log(median)
    return rng.lognormal(mu, sigma_g)

def sample_work_time(time_config, rng):
    """sample work time from normal distribution with minimum"""
    mean = time_config['mean']
    sd = time_config['sd']
    min_time = time_config['min']
    
    if sd == 0:
        return mean  # deterministic
    
    # sample from normal and apply minimum
    sampled_time = rng.normal(mean, sd)
    return max(sampled_time, min_time)

def sample_duration(duration_config, rng):
    """sample duration from scalar or normal distribution with minimum"""
    # scalar duration
    if isinstance(duration_config, (int, float)):
        return duration_config

    # normal distribution duration
    mean = duration_config["mean"]
    sd = duration_config["sd"]
    min_duration = duration_config["min"]
    if sd == 0:
        return mean
    sampled_duration = rng.normal(mean, sd)
    return max(sampled_duration, min_duration)

def resolve_waypoint(waypoint_config, model):
    """resolve a concrete waypoint from point config"""
    waypoint_type = waypoint_config["type"]
    if waypoint_type == "random_in_world":
        world_size = model.world_config["size"]
        return (
            model.random.random() * world_size,
            model.random.random() * world_size,
        )
    if waypoint_type == "charging_station":
        return tuple(model.world_config["charging_station"])
    raise ValueError(f"invalid waypoint type: {waypoint_type}")

def build_execution_details(service_config, model):
    """build runtime execution details from service phases in config"""

    # get phases config from service config
    phases_config = service_config.get("phases")
    if not phases_config:
        return None

    # get waypoints config from phases config, default to empty list
    waypoints_config = phases_config.get("waypoints", [])
    resolved_waypoints = []
    total_duration = 0

    # for each waypoint sample the duration, point and fail probability
    for idx, waypoint in enumerate(waypoints_config):
        duration = sample_duration(waypoint.get("duration", 0), model.random)
        resolved_point = resolve_waypoint(waypoint["point"], model)
        fail_cfg = waypoint.get("fail", 0.0)

        # this if statement is not necessary because there is ony going to be one way of defining failure
        if isinstance(fail_cfg, (int, float)):
            fail_model = {"model": "per_phase", "p": float(fail_cfg)}
        else:
            fail_model = {
                "model": fail_cfg.get("model", "per_phase"),
                "p": float(fail_cfg.get("p", 0.0)),
            }
            
        resolved_waypoints.append(
            {
                "id": waypoint.get("id", f"phase_{idx}"),
                "point": resolved_point,
                "duration": duration,
                "fail": fail_model,
            }
        )
        total_duration += duration

    # return one execution deatils dict with all the components
    return {
        "in_order": phases_config.get("in_order", True),
        "repeat": phases_config.get("repeat", 0),
        "phase_index": 0,
        "phase_remaining_time": resolved_waypoints[0]["duration"] if resolved_waypoints else 0,
        "resolved_waypoints": resolved_waypoints,
        "total_duration": total_duration,
    }
