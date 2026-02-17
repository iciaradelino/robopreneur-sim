def check_if_at_location(agent, location):
    pos = agent.pos
    distance = agent.model.space.get_distance(pos, location)
    tasks_config = agent.model.tasks_config if hasattr(agent.model, 'tasks_config') else agent.model.config['tasks']
    return distance <= tasks_config['proximity_threshold']