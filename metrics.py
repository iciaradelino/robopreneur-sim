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


def compute_total_tasks_completed(model):
    """
    compute the cumulative number of tasks completed during the simulation.
    """
    return model.task_counter


def compute_total_system_wealth(model):
    """
    compute the total wealth across all agents in the system.
    """
    return sum(agent.wealth for agent in model.agents)


def compute_task_queue_size(model):
    """
    compute the current number of unassigned tasks in the queue.
    """
    return len(model.task_queue)


def compute_critical_battery_rate(model):
    """
    compute the percentage of robots with critically low battery (<20%).
    """
    robots = [agent for agent in model.agents if hasattr(agent, 'battery')]
    if not robots:
        return 0
    critical_count = sum(1 for robot in robots if robot.battery < 20)
    return critical_count / len(robots)
