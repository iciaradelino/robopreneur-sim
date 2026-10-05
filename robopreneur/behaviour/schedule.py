# avoid magic numbers
def minutes_per_day():
    return 24 * 60

# which day are we on 0 indexed
def current_day(model):
    """return zero-indexed simulation day based on model steps."""
    return model.steps // minutes_per_day()

# which minute are we on
def minute_of_day(model):
    """return minute index within the current day."""
    return model.steps % minutes_per_day()

# convert a string like "10:00" to the number of minutes since midnight
def parse_hhmm(value):
    """parse a HH:MM string into minute-of-day."""
    if not isinstance(value, str):
        raise ValueError("time value must be a string in HH:MM format")
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError("time value must be in HH:MM format")
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("time value out of range")
    return hour * 60 + minute

# return the active from and until minutes
def parse_active_window(schedule_cfg):
    """
    parse schedule config and return (active_from_minute, active_until_minute).
    returns (None, None) when schedule is disabled.
    """
    if schedule_cfg is False or schedule_cfg is None:
        return None, None
    if isinstance(schedule_cfg, dict):
        active_from = parse_hhmm(schedule_cfg.get("active_from"))
        active_until = parse_hhmm(schedule_cfg.get("active_until"))
        return active_from, active_until
    raise ValueError("schedule must be false or {active_from, active_until}")

# current sim time is inside the agent's active window
def is_active(model, agent):
    """whether the agent should be active at the current time."""
    if agent.active_from_minute is None or agent.active_until_minute is None:
        return True
    now = minute_of_day(model)
    start = agent.active_from_minute
    end = agent.active_until_minute
    if start == end:
        return True
    if start < end:
        return start <= now < end
    return now >= start or now < end

