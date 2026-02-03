from load_config import tasks_config

def check_if_at_location(agent, location):
    pos = agent.model.space.get_pos(agent)
    distance = agent.model.space.get_distance(pos, location)
    return distance <= tasks_config['proximity_threshold']