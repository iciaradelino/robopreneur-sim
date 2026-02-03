# the logic to do all the calculations for the metrics

def compute_gini(model):
    """
    compute the gini coefficient of the model.
    """
    agent_wealths = [agent.wealth for agent in model.agents]
    if not agent_wealths or sum(agent_wealths) == 0:
        return 0
    agent_wealths.sort()
    total_wealth = sum(agent_wealths)
    gini = 0
    for i, wealth in enumerate(agent_wealths):
        gini += (i + 1) * wealth
    gini = 1 - 2 * gini / (total_wealth * len(agent_wealths))
    return gini


def compute_avg_battery(model):
    """
    compute the average battery level across all robot agents.
    """
    robots = [agent for agent in model.agents if hasattr(agent, 'battery')]
    if not robots:
        return 0
    return sum(robot.battery for robot in robots) / len(robots)


def compute_human_wealth(model):
    """
    compute the average wealth of human agents.
    """
    humans = [agent for agent in model.agents if not hasattr(agent, 'battery')]
    if not humans:
        return 0
    return sum(human.wealth for human in humans) / len(humans)


def compute_robot_wealth(model):
    """
    compute the average wealth of robot agents.
    """
    robots = [agent for agent in model.agents if hasattr(agent, 'battery')]
    if not robots:
        return 0
    return sum(robot.wealth for robot in robots) / len(robots)


def compute_idle_ratio(model):
    """
    compute the ratio of agents currently idle.
    """
    if not model.agents:
        return 0
    idle_count = sum(1 for agent in model.agents if agent.status == "idle")
    return idle_count / len(model.agents)


def compute_exec_ratio(model):
    """
    compute the ratio of agents currently executing tasks.
    """
    if not model.agents:
        return 0
    exec_count = sum(1 for agent in model.agents if agent.status == "exec")
    return exec_count / len(model.agents)


def compute_busy_ratio(model):
    """
    compute the ratio of agents currently busy (e.g., recharging).
    """
    if not model.agents:
        return 0
    busy_count = sum(1 for agent in model.agents if agent.status == "busy")
    return busy_count / len(model.agents)
