# the service is initialized at the begining of the simulation and 
# matched to the agents that provide it

class Service:
    def __init__(self, id, category, name, reward, time=None):
        self.id = id # unique identifier
        self.category = category # category of the service
        self.name = name # name of the service
        self.reward = reward # for how much money they offer the task
        self.time = time # legacy duration, optional for phase-based services

