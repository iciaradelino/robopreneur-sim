# the logic to assign tasks to agents

from agents import RobotAgent
from tasks import Task
from utils import build_execution_details

def generate_tasks(model):
    """generate tasks based on arrival rate and add them to the task queue using poisson"""

    arrival_rate = model.tasks_config['arrival_rate']  # tasks per hour
    steps_per_hour = 60  # 1 step = 1 minute
    tasks_per_step = arrival_rate / steps_per_hour
    num_tasks = model.random.poisson(tasks_per_step)
    
    # get available service names from agents (only services that agents can actually perform)
    available_services = set()
    for agent in model.agents:
        for service in agent.services:
            if service.name != "BatteryCharging":
                available_services.add(service.name)
    available_services = list(available_services)
    
    for _ in range(num_tasks):
        # randomly select an agent to request this task
        assigner_agent = model.random.choice(list(model.agents))
        
        # randomly select a service type
        service_name = model.random.choice(available_services)
        service_config = model.services_config[service_name]

        # build execution details first so we can use the first waypoint as location
        execution_details = build_execution_details(service_config, model)
        first_point = execution_details["resolved_waypoints"][0]["point"]

        # create task without reward, time, or completion probability (set when assigned)
        task = Task(
            task_id=model.task_counter,
            name=service_name,
            category=service_config['category'],
            location=first_point,
            assigner_id=assigner_agent.agent_id
        )

        task.execution_details = execution_details
        task.resolved_waypoints = execution_details["resolved_waypoints"]
        task.phase_index = execution_details["phase_index"]
        task.phase_remaining_time = execution_details["phase_remaining_time"]
        task.time = execution_details["total_duration"]
        task.remaining_time = task.time
        
        # lifecycle: record creation step
        task.created_step = model.steps
        model.task_queue.append(task)
        model.task_counter += 1

# find the available agents for a given task
def _get_eligible_agents(model, task):
    """
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
            if agent.battery < model.battery_config['min_accept_task']:
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
    agent.current_task = task

    # update agent target location to first waypoint
    agent.target_location = task.resolved_waypoints[task.phase_index]["point"]
    
    # update reward (we should explore more complex reward systems)
    task.reward = agent_service.reward

    # update total task duration from phase execution details
    task.time = task.execution_details["total_duration"]

    # store agent's skill on the task for use in failure probability calculation
    task.agent_skill = agent_service.skill
    task.status = "in_progress"
    task.assignee_id = agent.agent_id
    task.remaining_time = task.time if task.time is not None else 0
    # lifecycle: record assignment step
    task.assigned_step = model.steps

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

