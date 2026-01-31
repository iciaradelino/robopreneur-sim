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
