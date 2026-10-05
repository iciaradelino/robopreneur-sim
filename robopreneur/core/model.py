import mesa
import numpy as np

from agents import HumanAgent, RobotAgent
from metrics import compute_gini, compute_total_tasks_completed, compute_total_system_wealth, compute_task_queue_size, compute_critical_battery_rate
from task_assignation import generate_tasks, assign_tasks
from floor_plan import FloorPlan
from load_config import load_config

class RobopreneurModel(mesa.Model):
    def __init__(self, config=None):
        super().__init__()

        # single source of truth: a config dict drives the whole model.
        # when none is passed (e.g. the solara app) we fall back to config.yaml.
        if config is None:
            config = load_config()
        self.config = config
        self.sim_config = config['simulation']
        self.world_config = config['world']
        self.humans_config = config['humans']
        self.robots_config = config['robots']
        self.battery_config = config['battery']
        self.tasks_config = config['tasks']
        self.services_config = config['services']
        self.completed_tasks = []
        self.random = np.random.default_rng(self.sim_config['seed'])
        self.world_mode = self.world_config.get("mode", "square")

        self.floor_plan = None
        if self.world_mode == "floor_plan":
            floor_plan_config = self.world_config.get("floor_plan", {})
            self.floor_plan = FloorPlan(floor_plan_config)
            self.space = mesa.space.ContinuousSpace(
                self.floor_plan.width,
                self.floor_plan.height,
                torus=False,
            )
            charging_station = tuple(self.world_config.get("charging_station", (0, 0)))
            self.world_config["charging_station"] = list(
                self.floor_plan.normalize_point(charging_station)
            )
        else:
            self.space = mesa.space.ContinuousSpace(
                self.world_config['size'],
                self.world_config['size'],
                torus=self.world_config['boundaries']
            )

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Gini": compute_gini,
                "Tasks_Completed": compute_total_tasks_completed,
                "System_Wealth": compute_total_system_wealth,
                "Queue_Size": compute_task_queue_size,
                "Critical_Battery": compute_critical_battery_rate
            },
            agent_reporters={
                "Wealth": "wealth",
                "Battery": lambda a: getattr(a, "battery", None),
                "Status": "status",
                "Agent_Type": lambda a: "robot" if hasattr(a, "battery") else "human",
            }
        )

        self.task_queue = [] # task queue for unassigned tasks
        self.task_counter = 0 # running id / created-task counter
        self.completed_task_count = 0 # cumulative successfully completed tasks
        self.failed_task_count = 0 # cumulative failed tasks

        self.initialize_agents()
        self.running = True
        self.datacollector.collect(self)

    def initialize_agents(self):
        # create num agents for each human type
        for human_type, human_config in self.humans_config.items():
            num_agents = human_config.get('num', 1)
            for i in range(num_agents):
                # create unique agent id for each instance
                agent_id = f"{human_type}_{i}"
                # create the human agent, place it in the space, gets all the services appened at init
                human = HumanAgent(self, agent_id, human_config)
                pos = self._random_world_position()
                self.space.place_agent(human, pos)
                human.target_location = pos

        # create num agents for each robot type
        for robot_type, robot_config in self.robots_config.items():
            num_agents = robot_config.get('num', 1)
            for i in range(num_agents):
                # create unique agent id for each instance
                agent_id = f"{robot_type}_{i}"
                # create the robot agent, place it in the space, gets all the services appened at init
                robot = RobotAgent(self, agent_id, robot_config)
                pos = self._random_world_position()
                self.space.place_agent(robot, pos)
                robot.target_location = pos

    def _random_world_position(self):
        if self.floor_plan:
            return self.floor_plan.random_point(self.random)
        return (
            self.random.random() * self.world_config['size'],
            self.random.random() * self.world_config['size'],
        )

    def step(self):
        '''
        1. Generate tasks
        2. Step all agents 
        3. Check task completions
        4. Assign tasks from queue
        5. Record data  
        '''
        # create tasks
        generate_tasks(self)

        # updates the status of agents and tasks
        self.agents.do("step") 

        # assign tasks to agents
        assign_tasks(self)

        # record data
        self.datacollector.collect(self)

        # check if simulation should stop 
        # (self.steps is auto-incremented by mesa)
        if self.steps >= self.sim_config['duration']:
            self.running = False
