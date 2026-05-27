import mesa
import numpy as np
from services import Service
from utils import sample_reward
from battery import update_battery
from movement import check_if_at_location
from economy import transfer_reward
from schedule import parse_active_window, is_active

def _pick_random_target(agent):
    ''' pick a random target for the agent '''
    floor_plan = getattr(agent.model, "floor_plan", None)
    if floor_plan:
        return floor_plan.random_point(agent.model.random)
    world_size = agent.model.world_config['size']
    return (
        agent.model.random.random() * world_size,
        agent.model.random.random() * world_size,
    )

def _resolve_step_target(agent):
    '''which point to steer toward this step: final target (square) or next path vertex (floor_plan).'''
    # already at final target move() should not advance further
    if check_if_at_location(agent, agent.target_location):
        return None

    floor_plan = getattr(agent.model, "floor_plan", None)
    # if in square mode steer straight at target_location
    if floor_plan is None:
        return agent.target_location

    # floor_plan mode: if the assignment changed the final goal, recompute the polyline once
    if agent._nav_target != agent.target_location:
        agent._nav_path = floor_plan.compute_path(agent.pos, agent.target_location) or []
        agent._nav_target = agent.target_location

    # drop vertices we have already reached (within proximity_threshold)
    while agent._nav_path and check_if_at_location(agent, agent._nav_path[0]):
        agent._nav_path.pop(0)

    # steer at the next corner on the route, or at the goal if the path is empty / degenerate
    if agent._nav_path:
        return agent._nav_path[0]
    return agent.target_location

def _move_towards_target(agent, step_target):
    '''one timestep of motion: same speed-limited vector step as before; mesa stores the new position.'''
    # nothing to do (like already at target)
    if step_target is None:
        return

    # get current position 
    current_pos = np.array(agent.pos)
    target_pos = np.array(step_target)

    # calculate the direction and distance to the target
    direction = target_pos - current_pos
    distance = np.linalg.norm(direction)
    if distance == 0:
        return

    # if the distance is less than the speed, move to the target
    if distance <= agent.speed:
        new_pos = tuple(target_pos)
    # otherwise, move towards the target at the speed
    else:
        # normalize the direction to unit length
        direction_normalized = direction / distance
        new_pos = tuple(current_pos + direction_normalized * agent.speed)

    # move the agent to the new position
    agent.model.space.move_agent(agent, new_pos)
    agent.location = new_pos

# helper function to avoid code duplication
def _finish_task(agent, task, success):
    """finalize task lifecycle, release agent and transfer reward"""

    # record completion step
    task.completed_step = agent.model.steps
    # update task status
    task.status = "completed" if success else "failed"
    # add to completed tasks list
    agent.model.completed_tasks.append(task)
    if task.status == "completed" and hasattr(agent.model, "completed_task_count"):
        agent.model.completed_task_count += 1
    if task.status == "failed" and hasattr(agent.model, "failed_task_count"):
        agent.model.failed_task_count += 1
    # transfer reward if task is successful
    if success:
        transfer_reward(agent.model, task, agent)
    # release agent
    agent.status = "idle"
    agent.current_task = None

def _execute_phase_task(agent, task):
    """phase-based execution: travel -> dwell -> next phase"""

    # if it has no phase data, don't execute
    if not task.resolved_waypoints:
        return False

    # guard for edge cases where task is already completed
    if task.phase_index >= len(task.resolved_waypoints):
        _finish_task(agent, task, True)
        return True

    # get current phase and location of that phase  
    phase = task.resolved_waypoints[task.phase_index]
    phase_point = phase["point"]

    # check if agent is at the location of that current phase, if not move there
    if not check_if_at_location(agent, phase_point):
        agent.target_location = phase_point
        return True

    # decrement phase remaining time
    if task.phase_remaining_time > 0:
        task.phase_remaining_time -= 1
        task.remaining_time = max(task.remaining_time - 1, 0)

    # still dwelling — nothing more to do this step
    if task.phase_remaining_time > 0:
        return True

    # phase just finished: evaluate fail once per phase completion
    # effective_p = base_fail_p * (1 - skill); higher skill lowers failure risk
    fail_cfg = phase.get("fail", {"model": "per_phase", "p": 0.0})
    base_fail_p = fail_cfg.get("p", 0.0)
    skill = task.agent_skill if task.agent_skill is not None else 0.0
    effective_p = base_fail_p * (1.0 - skill)
    if agent.model.random.random() < effective_p:
        _finish_task(agent, task, False)
        return True

    # increment phase index to move to the next phase
    task.phase_index += 1

    # check if all phases are completed after the increment 
    if task.phase_index >= len(task.resolved_waypoints):
        _finish_task(agent, task, True)
        return True

    # get next phase
    next_phase = task.resolved_waypoints[task.phase_index]
    # update phase remaining time
    task.phase_remaining_time = next_phase.get("duration", 0)
    # update agent target location
    agent.target_location = next_phase["point"]
    # return True to continue execution
    return True

# to avoid duplicated logic in robot and human 
def _apply_schedule_state(agent):
    """toggle active/inactive state based on configured schedule."""
    if is_active(agent.model, agent):
        if agent.status == "inactive":
            agent.status = "idle"
        return True

    if agent.status == "exec" and agent.current_task is not None:
        # return interrupted task to queue so it can be reassigned later
        agent.current_task.status = "pending"
        agent.current_task.assignee_id = None
        agent.model.task_queue.append(agent.current_task)
        agent.current_task = None

    agent.status = "inactive"
    return False

class HumanAgent(mesa.Agent):
    def __init__(self, model, agent_id, agent_config):
        super().__init__(model)
        self.agent_id = agent_id
        self.wealth = agent_config.get('initial_wealth') 
        self.status = "idle"
        self.current_task = None
        self.speed = agent_config.get('speed')
        self.schedule = agent_config.get('schedule', False)
        self.active_from_minute, self.active_until_minute = parse_active_window(self.schedule)
        self.location = (0, 0) # this should be initialized randomly 
        self.target_location = (0, 0) # this should be optional 
        self._nav_path = []  # list of tuples with the path to the target so that it doesn't walk through holes
        self._nav_target = None  # tuple | None: last target_location we built _nav_path for so that it doesn't recompute the path

        # extract the services it offers from the config and 
        # create an instance of that service following the services.py template
        # expected format: services: [- ServiceName: {skill: 0.95}]
        raw_services = agent_config.get('services', [])
        self.services = []
        for entry in raw_services:
            service_name = next(iter(entry))
            skill = entry[service_name].get('skill', 0.0)
            service_config = model.services_config[service_name]
            reward_value = sample_reward(service_config['reward'], model.random)

            service = Service(
                id=service_name,
                category=service_config['category'],
                name=service_name,
                reward=reward_value,
                skill=skill,
            )
            self.services.append(service)

    def step(self):
        if not _apply_schedule_state(self):
            return

        # task execution
        if self.status == "exec" and self.current_task is not None:
            self.execute_task()

        # movement (move() checks if already at target)
        self.move()


    def move(self):
        step_target = _resolve_step_target(self)
        _move_towards_target(self, step_target)

    def execute_task(self):
        _execute_phase_task(self, self.current_task)

class RobotAgent(mesa.Agent):
    def __init__(self, model, agent_id, agent_config):
        super().__init__(model)
        self.agent_id = agent_id
        self.wealth = agent_config.get('initial_wealth')
        self.status = "idle"
        self.current_task = None
        self.battery = agent_config.get('initial_battery')
        self.speed = agent_config.get('speed', 1.5)
        self.random_walk_interval = agent_config.get('random_walk_interval')
        self.schedule = agent_config.get('schedule', False)
        self.active_from_minute, self.active_until_minute = parse_active_window(self.schedule)
        self.location = (0, 0) # this should be initialized randomly 
        self.target_location = (0, 0) # this should be optional
        self._nav_path = []  # list[tuple[float, float]]: jupedsim route corners when world.mode=floor_plan
        self._nav_target = None  # tuple | None: last target_location we built _nav_path for (cache key)
        self.awaiting_recharge = False # tracks if robot is waiting for recharge
        self.is_charging = False      # latches true once human and robot are both at the station
        self.recharge_task = None     # reference to the current recharge task 
        
        # extract the services it offers from the config and create instances
        # expected format: services: [- ServiceName: {skill: 0.80}]
        raw_services = agent_config.get('services', [])
        self.services = []
        for entry in raw_services:
            service_name = next(iter(entry))
            skill = entry[service_name].get('skill', 0.0)
            service_config = model.services_config[service_name]
            reward_value = sample_reward(service_config['reward'], model.random)

            service = Service(
                id=service_name,
                category=service_config['category'],
                name=service_name,
                reward=reward_value,
                skill=skill,
            )
            self.services.append(service)

        # initialize target location randomly so idle robots start walking immediately
        self.target_location = _pick_random_target(self)
        self.walk_counter = 0  # counts steps since last random target pick

    def step(self):
        if not _apply_schedule_state(self):
            return

        # update battery
        update_battery(self)
        
        # task execution (only if not waiting for recharge)
        if self.status == "exec" and self.current_task is not None:
            self.execute_task()

        # random walk: when idle, pick a new target every random_walk_interval steps
        if self.status == "idle":
            self.walk_counter += 1
            if self.walk_counter >= self.random_walk_interval:
                self.target_location = _pick_random_target(self)
                self.walk_counter = 0

        # movement (checks if already at target)
        self.move()

    def move(self):
        step_target = _resolve_step_target(self)
        _move_towards_target(self, step_target)


    def execute_task(self):
        _execute_phase_task(self, self.current_task)
