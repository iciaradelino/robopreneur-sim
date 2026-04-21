import mesa
import numpy as np

from agents import HumanAgent, RobotAgent
from tasks import Task
from services import Service
from metrics import compute_gini, compute_total_tasks_completed, compute_total_system_wealth, compute_task_queue_size, compute_critical_battery_rate
from task_assignation import generate_tasks, assign_tasks

# load the config from the config.yaml file
from load_config import sim_config, world_config, humans_config, robots_config, battery_config, tasks_config, assignment_policy_config, pricing_model_config, services_config

class RobopreneurModel(mesa.Model):
    def __init__(self):
        super().__init__()

        # store config references for compatibility with dynamic loading
        self.sim_config = sim_config
        self.world_config = world_config
        self.humans_config = humans_config
        self.robots_config = robots_config
        self.battery_config = battery_config
        self.tasks_config = tasks_config
        self.services_config = services_config
        self.completed_tasks = []
        self.random = np.random.default_rng(sim_config['seed'])

        self.space = mesa.space.ContinuousSpace(
            world_config['size'], 
            world_config['size'], 
            torus=world_config['boundaries']
        )

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Gini": compute_gini,
                "Tasks_Completed": compute_total_tasks_completed,
                "System_Wealth": compute_total_system_wealth,
                "Queue_Size": compute_task_queue_size,
                "Critical_Battery": compute_critical_battery_rate
            },
            agent_reporters={"Wealth": "wealth", "Battery": lambda a: getattr(a, 'battery', None)}
        )

        self.task_queue = [] # task queue for unassigned tasks
        self.task_counter = 0 # to count how many tasks are completed during the simulation

        self.initialize_agents()
        self.running = True
        self.datacollector.collect(self)

    def initialize_agents(self):
        # create num agents for each human type
        for human_type, human_config in humans_config.items():
            num_agents = human_config.get('num', 1)
            for i in range(num_agents):
                # create unique agent id for each instance
                agent_id = f"{human_type}_{i}"
                # create the human agent, place it in the space, gets all the services appened at init
                human = HumanAgent(self, agent_id, human_config)
                pos = (self.random.random() * world_config['size'], self.random.random() * world_config['size'])
                self.space.place_agent(human, pos)
                human.location = pos
                human.target_location = pos

        # create num agents for each robot type
        for robot_type, robot_config in robots_config.items():
            num_agents = robot_config.get('num', 1)
            for i in range(num_agents):
                # create unique agent id for each instance
                agent_id = f"{robot_type}_{i}"
                # create the robot agent, place it in the space, gets all the services appened at init
                robot = RobotAgent(self, agent_id, robot_config)
                pos = (self.random.random() * world_config['size'], self.random.random() * world_config['size'])
                self.space.place_agent(robot, pos)
                robot.location = pos
                robot.target_location = pos

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
        if self.steps >= sim_config['duration']:
            self.running = False
