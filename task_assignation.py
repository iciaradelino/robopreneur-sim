# the logic to assign tasks to agents

from agents import RobotAgent
from tasks import Task
from utils import build_execution_details
from schedule import current_day, minute_of_day, parse_hhmm, minutes_per_day

# add all the details to the task
def _create_task(model, service_name):
    """create and enqueue a single task for the given service."""
    service_config = model.services_config[service_name]
    assigner_agent = model.random.choice(list(model.agents))

    # build execution details first so we can use the first waypoint as location
    execution_details = build_execution_details(service_config, model)
    if execution_details is None or not execution_details["resolved_waypoints"]:
        return
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

# available services for random generation
def _random_services(model):
    """services available for random generation."""
    available_services = set()
    for agent in model.agents:
        for service in agent.services:
            if service.name != "BatteryCharging":
                available_services.add(service.name)
    return list(available_services)

# dictionary of tasks by absolute step
def _build_deterministic_index(model):
    """precompute deterministic task schedule keyed by absolute step."""
    if hasattr(model, "_deterministic_task_index"):
        return model._deterministic_task_index

    index = {}
    for entry in model.tasks_config.get("deterministic_schedule", []):
        day = entry["day"]
        minute = parse_hhmm(entry["time"])
        abs_step = day * minutes_per_day() + minute

        if abs_step not in index:
            index[abs_step] = {}

        for service_name, count in entry["counts"].items():
            index[abs_step][service_name] = index[abs_step].get(service_name, 0) + int(count)

    model._deterministic_task_index = index
    return index

# random task arrival schedule
def _generate_random_tasks(model):
    """random mode: poisson arrivals from executable services."""
    arrival_rate = model.tasks_config['arrival_rate']  # tasks per hour
    steps_per_hour = 60  # 1 step = 1 minute
    tasks_per_step = arrival_rate / steps_per_hour
    num_tasks = model.random.poisson(tasks_per_step)

    available_services = _random_services(model)
    if not available_services:
        return

    for _ in range(num_tasks):
        service_name = model.random.choice(available_services)
        _create_task(model, service_name)

# fixed task arrival schedule
def _generate_deterministic_tasks(model):
    """deterministic mode: inject exact counts at exact day+time."""
    current_step = current_day(model) * 1440 + minute_of_day(model)
    task_index = _build_deterministic_index(model)
    counts = task_index.get(current_step, {})
    for service_name, count in counts.items():
        for _ in range(int(count)):
            _create_task(model, service_name)

# depends on task mode
def generate_tasks(model):
    """generate tasks according to tasks.mode."""
    mode = model.tasks_config.get("mode", "random")
    if mode == "deterministic":
        _generate_deterministic_tasks(model)
        return
    _generate_random_tasks(model)

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
        if agent.status == "inactive":
            continue

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

    # reset phase state so re-assigned tasks always start from the beginning
    task.phase_index = 0
    task.phase_remaining_time = task.resolved_waypoints[0].get("duration", 0) if task.resolved_waypoints else 0
    task.time = task.execution_details["total_duration"]
    task.remaining_time = task.time

    # update agent target location to first waypoint
    agent.target_location = task.resolved_waypoints[0]["point"]

    # update reward (we should explore more complex reward systems)
    task.reward = agent_service.reward

    # store agent's skill on the task for use in failure probability calculation
    task.agent_skill = agent_service.skill
    task.status = "in_progress"
    task.assignee_id = agent.agent_id
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

