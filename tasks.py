# this is for when the task is created by someone 
# and then assigned to an agent

class Task:
    def __init__(self, task_id, name, category, location, reward=None, time=None, agent_skill=None, assigner_id=None):
        self.id = task_id
        self.name = name
        self.category = category
        self.location = location
        self.reward = reward  # set when assigned to agent
        self.time = time  # set when assigned to agent
        self.agent_skill = agent_skill  # agent's skill level [0,1]; set when assigned
        self.assigner_id = assigner_id  # agent who created/requested the task
        self.assignee_id = None  # who is performing the task
        self.remaining_time = time if time is not None else 0
        self.status = "pending"  # pending, in_progress, completed, failed

        # lifecycle tracking (for experiment analysis)
        self.created_step = None
        self.assigned_step = None
        self.completed_step = None

        # task phase details 
        self.execution_details = None
        self.phase_index = 0
        self.phase_remaining_time = 0
        self.resolved_waypoints = []