import mesa
import numpy as np

from agents import HumanAgent, RobotAgent
from tasks import Task
from services import Service
from metrics import compute_gini, compute_avg_battery, compute_human_wealth, compute_robot_wealth, compute_idle_ratio, compute_exec_ratio, compute_busy_ratio
from task_assignation import generate_tasks, assign_tasks

# load the config from the config.yaml file
from load_config import sim_config, world_config, humans_config, robots_config, battery_config, tasks_config, assignment_policy_config, pricing_model_config, services_config

class RobopreneurModel(mesa.Model):
    def __init__(self):
        super().__init__()

        self.random = np.random.default_rng(sim_config['seed'])

        self.space = mesa.space.ContinuousSpace(
            world_config['size'], 
            world_config['size'], 
            torus=world_config['boundaries']
        )

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Gini": compute_gini,
                "Avg_Battery": compute_avg_battery,
                "Human_Wealth": compute_human_wealth,
                "Robot_Wealth": compute_robot_wealth,
                "Idle_Ratio": compute_idle_ratio,
                "Exec_Ratio": compute_exec_ratio,
                "Busy_Ratio": compute_busy_ratio
            },
            agent_reporters={"Wealth": "wealth", "Battery": lambda a: getattr(a, 'battery', None)}
        )

        self.task_queue = [] # task queue for unassigned tasks
        self.task_counter = 0 # to count how many tasks are completed during the simulation

        self.initialize_agents()
        self.running = True
        self.datacollector.collect(self)

    def initialize_agents(self):
        for human_id, human_config in humans_config.items():
            # create the human agent, place it in the space, gets all the services appened at init
            human = HumanAgent(self, human_id, human_config)
            pos = (self.random.random() * world_config['size'], self.random.random() * world_config['size'])
            self.space.place_agent(human, pos)
            human.location = pos
            human.target_location = pos

        for robot_id, robot_config in robots_config.items():
            # create the robot agent, place it in the space, gets all the services appened at init
            robot = RobotAgent(self, robot_id, robot_config)
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
        
        generate_tasks(self)

        # updates the status of agents and tasks
        self.agents.do("step") 

        assign_tasks(self)

        self.datacollector.collect(self)

        # check if simulation should stop 
        # (self.steps is auto-incremented by mesa)
        if self.steps >= sim_config['duration']:
            self.running = False
