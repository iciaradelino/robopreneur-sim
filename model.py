import mesa
import numpy as np

from agents import HumanAgent, RobotAgent
from tasks import Task
from services import Service
from metrics import compute_gini
from task_assignation import generate_tasks, update_task_status, assign_tasks

# load the config from the config.yaml file
from load_config import sim_config, world_config, humans_config, robots_config, battery_config, tasks_config, assignemnt_policy_config, pricing_model_config, services_config

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
            model_reporters={"Gini": compute_gini},
            agent_reporters={"Wealth": "wealth"}
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

        for robot_id, robot_config in robots_config.items():
            # create the robot agent, place it in the space, gets all the services appened at init
            robot = RobotAgent(self, robot_id, robot_config)
            pos = (self.random.random() * world_config['size'], self.random.random() * world_config['size'])
            self.space.place_agent(robot, pos)

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
