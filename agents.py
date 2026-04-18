import mesa
import numpy as np
from services import Service
from utils import sample_reward
from battery import update_battery
from movement import check_if_at_location
from economy import transfer_reward

# helper function to avoid code duplication
def _finish_task(agent, task, success):
    """finalize task lifecycle, release agent and transfer reward"""

    # record completion step
    task.completed_step = agent.model.steps
    # add to completed tasks list
    agent.model.completed_tasks.append(task)
    # update task status
    task.status = "completed" if success else "failed"
    # transfer reward if task is successful
    if success:
        transfer_reward(agent.model, task, agent)
    # release agent
    agent.status = "idle"
    agent.current_task = None

def _execute_phase_task(agent, task):
    """phase-based execution: travel -> dwell -> fail check -> next phase"""

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

    # per-step fail check: effective_p = base_fail_p * (1 - skill)
    # higher skill lowers failure risk; base_fail_p captures task difficulty
    fail_cfg = phase.get("fail", {"model": "per_phase", "p": 0.0})
    base_fail_p = fail_cfg.get("p", 0.0)
    skill = task.prob_completion if task.prob_completion is not None else 0.0
    effective_p = base_fail_p * (1.0 - skill)
    if agent.model.random.random() < effective_p:
        _finish_task(agent, task, False)
        return True

    # check if phase is completed
    if task.phase_remaining_time > 0:
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


class HumanAgent(mesa.Agent):
    def __init__(self, model, agent_id, agent_config):
        super().__init__(model)
        self.agent_id = agent_id
        self.wealth = agent_config.get('initial_wealth') 
        self.status = "idle"
        self.current_task = None
        self.speed = agent_config.get('speed')
        self.schedule = agent_config.get('schedule', False)
        self.location = (0, 0) # this should be initialized randomly 
        self.target_location = (0, 0) # this should be optional 

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
        # task execution
        if self.status == "exec" and self.current_task is not None:
            self.execute_task()

        # movement (move() checks if already at target)
        self.move()


    def move(self):
        # get current position from mesa space
        current_pos = np.array(self.pos)
        target_pos = np.array(self.target_location)

        if check_if_at_location(self, self.target_location):
            return
        
        # calculate direction vector and distance
        direction = target_pos - current_pos
        distance = np.linalg.norm(direction)
        
        # move at most self.speed units toward target
        if distance <= self.speed:
            # can reach target this step
            new_pos = tuple(target_pos)
        else:
            # normalize so we move exactly self.speed units (direction has length distance, not 1)
            direction_normalized = direction / distance
            new_pos = tuple(current_pos + direction_normalized * self.speed)
        
        # update position in mesa space
        self.model.space.move_agent(self, new_pos)
        self.location = new_pos

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
        self.location = (0, 0) # this should be initialized randomly 
        self.target_location = (0, 0) # this should be optional
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
        world_size = self.model.world_config['size']
        self.target_location = (self.model.random.random() * world_size, self.model.random.random() * world_size)
        self.walk_counter = 0  # counts steps since last random target pick

    def step(self):
        # update battery
        update_battery(self)
        
        # task execution (only if not waiting for recharge)
        if self.status == "exec" and self.current_task is not None:
            self.execute_task()

        # random walk: when idle, pick a new target every random_walk_interval steps
        if self.status == "idle":
            self.walk_counter += 1
            if self.walk_counter >= self.random_walk_interval:
                world_size = self.model.world_config['size']
                self.target_location = (
                    self.model.random.random() * world_size,
                    self.model.random.random() * world_size
                )
                self.walk_counter = 0

        # movement (checks if already at target)
        self.move()

    def move(self):
        # if already at target (within proximity threshold), do nothing
        if check_if_at_location(self, self.target_location):
            return
        
        # get current position from mesa space
        current_pos = np.array(self.pos)
        target_pos = np.array(self.target_location)
        
        # calculate direction vector and distance
        direction = target_pos - current_pos
        distance = np.linalg.norm(direction)
        
        # if within reach moves to exact target
        if distance <= self.speed:
            new_pos = tuple(target_pos)
        # if not within reach moves towards target at speed
        else:
            direction_normalized = direction / distance
            new_pos = tuple(current_pos + direction_normalized * self.speed)
        
        # update position in mesa space
        self.model.space.move_agent(self, new_pos)
        self.location = new_pos


    def execute_task(self):
        _execute_phase_task(self, self.current_task)
