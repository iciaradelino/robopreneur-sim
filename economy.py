def transfer_reward(model, task, assignee):
    """deduct reward from the assigner and credit it to the assignee"""
    assigner = next((a for a in model.agents if a.agent_id == task.assigner_id), None)
    if assigner is not None:
        assigner.wealth -= task.reward
    assignee.wealth += task.reward