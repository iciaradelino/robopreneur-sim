# the logic to assign tasks to agents

from load_config import assignment_policy_config, battery_config, tasks_config, services_config, world_config, humans_config
from agents import HumanAgent, RobotAgent
from tasks import Task
from utils import sample_reward, sample_work_time

# generate tasks based on arrival rate and add them to the task queue using poisson 
def generate_tasks(model):

    arrival_rate = tasks_config['arrival_rate']  # tasks per hour
    steps_per_hour = 60  # 1 step = 1 minute
    tasks_per_step = arrival_rate / steps_per_hour
    num_tasks = model.random.poisson(tasks_per_step)
    
    # get available service names from agents (only services that agents can actually perform)
    available_services = set()
    for agent in model.agents:
        for service in agent.services:
            available_services.add(service.name)
    available_services = list(available_services)
    
    for _ in range(num_tasks):
        # randomly select an agent to request this task
        assigner_agent = model.random.choice(list(model.agents))
        
        # randomly select a service type
        service_name = model.random.choice(available_services)
        service_config = services_config[service_name]
        
        # generate random location in world space
        location = (
            model.random.random() * world_config['size'],
            model.random.random() * world_config['size']
        )
        
        # create task without reward, time, or completion probability
        # these will be set when the task is assigned to an agent
        task = Task(
            task_id=model.task_counter,
            name=service_name,
            category=service_config['category'],
            location=location,
            assigner_id=assigner_agent.agent_id
        )
        
        # add to queue
        model.task_queue.append(task)
        model.task_counter += 1

# find the available agents for a given task
def _get_eligible_agents(model, task):
    """
    find all agents eligible for a given task
    eligibility criteria:
    1. agent.status == "idle"
    2. agent has a service matching task.name
    3. if robot: battery >= min_accept_task
    """
    eligible_agents = []
    
    for agent in model.agents:
        # check if agent is idle
        if agent.status != "idle":
            continue
        
        # check if agent has capability (service matching task name)
        has_capability = False
        for service in agent.services:
            if service.name == task.name:
                has_capability = True
                break
        
        if not has_capability:
            continue
        
        # check battery constraint for robots
        if isinstance(agent, RobotAgent):
            if agent.battery < battery_config['min_accept_task']:
                continue
        
        # agent is eligible
        eligible_agents.append(agent)
    
    return eligible_agents

# assign a single task to an agent
def _assign_task_to_agent(model, task, agent):
    """
    assign a task to an agent and update both task and agent properties
    sets task reward, time, and completion probability from the agent's service
    """
    # find the agent's service matching this task
    # this is kind of inefficient, maybe find a better way to do this
    # we know the agent has this service because they were filtered in _get_eligible_agents
    agent_service = None
    for service in agent.services:
        if service.name == task.name:
            agent_service = service
            break
    
    # update agent properties
    agent.status = "exec"
    agent.curent_task = task
    agent.target_location = task.location
    
    # update task properties with agent-specific values
    task.reward = agent_service.reward
    task.time = agent_service.time
    task.prob_completion = agent.completion_probability
    task.status = "in_progress"
    task.assignee_id = agent.agent_id
    task.remaining_time = task.time

# assign all tasks in the queue to available agents
def assign_tasks(model):
    """
    assign tasks from queue to available agents using random selection
    processes entire queue once per step, can assign multiple tasks
    if no eligible agents found, task is requeued at the end
    """
    # if no tasks in queue, return
    if not model.task_queue:
        return
    
    # to prevent infinite loops
    max_iterations = len(model.task_queue)
    iterations = 0
    
    while model.task_queue and iterations < max_iterations:
        task = model.task_queue.pop(0)
        eligible_agents = _get_eligible_agents(model, task)
        
        if not eligible_agents:
            # no one can do this task right now - requeue at end
            model.task_queue.append(task)
        else:
            # randomly select an agent from eligible pool
            selected_agent = model.random.choice(eligible_agents)
            
            # assign the task
            _assign_task_to_agent(model, task, selected_agent)
            # task is already removed from queue (popped above)
        
        iterations += 1

