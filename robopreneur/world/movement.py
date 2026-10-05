def check_if_at_location(agent, location):
    pos = agent.pos
    distance = agent.model.space.get_distance(pos, location)
    return distance <= agent.model.tasks_config['proximity_threshold']