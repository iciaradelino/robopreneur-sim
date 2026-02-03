# this is for when the task is created by someone 
# and then assigned to an agent

class Task:
    def __init__(self, task_id, name, category, location, reward=None, time=None, prob_completion=None, assigner_id=None):
        self.id = task_id
        self.name = name
        self.category = category
        self.location = location
        self.reward = reward  # set when assigned to agent
        self.time = time  # set when assigned to agent
        self.prob_completion = prob_completion  # set when assigned to agent
        self.assigner_id = assigner_id  # agent who created/requested the task
        self.assignee_id = None  # who is performing the task
        self.remaining_time = time if time is not None else 0
        self.status = "pending"  # pending, in_progress, completed, failed
