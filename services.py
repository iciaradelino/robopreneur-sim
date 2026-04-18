# the service is initialized at the begining of the simulation and 
# matched to the agents that provide it

class Service:
    def __init__(self, id, category, name, reward, skill=0.0):
        self.id = id # unique identifier
        self.category = category # category of the service
        self.name = name # name of the service
        self.reward = reward # for how much money they offer the task
        self.skill = skill # agent's proficiency [0, 1]; scales down base failure probability

