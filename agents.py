import mesa
from services import Service
from utils import sample_reward, sample_work_time
from model import RobopreneurModel

from load_config import sim_config, world_config, humans_config, robots_config, battery_config, tasks_config, assignemnt_policy_config, pricing_model_config, services_config
# no backup values for the config, if it doesn't load give an error

class HumanAgent(mesa.Agent):
    def __init__(self, model, agent_id, agent_config):
        super().__init__(model)
        self.agent_id = agent_id
        self.wealth = agent_config.get('initial_wealth') 
        self.status = "idle"
        self.curent_task = None
        self.speed = agent_config.get('speed')
        self.completion_probability = agent_config.get('completion_probability')
        self.schedule = agent_config.get('schedule', False)
        self.location = (0, 0) # this should be initialized randomly 
        self.target_location = (0, 0) # this should be optional 

        # extract the services it offers from the config and 
        # create an instance of that service following the services.py template
        service_names = agent_config.get('services')  # list like ['BatteryCharging', 'LabCleaning', ...]
        self.services = []
        for service_name in service_names:
            service_config = services_config[service_name]
            
            # sample specific values from distributions
            reward_value = sample_reward(service_config['reward'], model.random)
            time_value = sample_work_time(service_config['work_time'], model.random)
            
            service = Service(
                id=service_name,
                category=service_config['category'],
                name=service_name,
                reward=reward_value,
                time=time_value  
            )
            self.services.append(service)

    def step(self):
        # movement
        if self.location != self.target_location:
            self.move()

        # task execution
        if self.status == "exec" and self.curent_task is not None:
            self.execute_task()


    def move(self):
        # implement the moving logic here
        # TODO: implement move logic
        pass

    def execute_task(self):
        task = self.curent_task

        # decrement remaining time
        task.remaining_time -= 1
        
        # check if task is complete
        if task.remaining_time <= 0:
            # check completion probability
            if RobopreneurModel.random.random() < self.completion_probability:
                # task completed successfully
                task.status = "completed"
                self.wealth += task.reward
            else:
                # task failed
                task.status = "failed"

            # agent is now idle and no longer has a task
            self.status = "idle"
            self.curent_task = None


class RobotAgent(mesa.Agent):
    def __init__(self, model, agent_id, agent_config):
        super().__init__(model)
        self.agent_id = agent_id
        self.wealth = agent_config.get('initial_wealth')
        self.status = "idle"
        self.curent_task = None
        self.battery = agent_config.get('initial_battery')
        self.speed = agent_config.get('speed', 1.5)
        self.completion_probability = agent_config.get('completion_probability')
        self.random_walk_interval = agent_config.get('random_walk_interval')
        self.location = (0, 0) # this should be initialized randomly 
        self.target_location = (0, 0) # this should be optional 
        
        # extract the services it offers from the config and create instances
        self.services = []
        service_names = agent_config.get('services')  # list like ['LabCleaning', 'ItemTransport', ...]
        
        for service_name in service_names:
            service_config = services_config[service_name]

            # sample specific values from distributions
            reward_value = sample_reward(service_config['reward'], model.random)
            time_value = sample_work_time(service_config['work_time'], model.random)
            
            service = Service(
                id=service_name,
                category=service_config['category'],
                name=service_name,
                reward=reward_value,  # sampled number
                time=time_value  # sampled number
            )
            self.services.append(service)

    def step(self):
        # battery management
        drain_rate = battery_config['drain_rate']
        self.battery -= drain_rate
        if self.battery < 0:
            self.battery = 0
        if self.battery <= battery_config['recharge_trigger']:
            self.recharge()

        # task execution
        if self.status == "exec" and self.curent_task is not None:
            self.execute_task()

        # movement
        if self.location != self.target_location:
            self.move()

    def move(self):
        # move towards the target location
        # TODO: implement move logic
        pass


    def execute_task(self):
        task = self.curent_task

        # decrement remaining time
        task.remaining_time -= 1
        
        # check if task is complete
        if task.remaining_time <= 0:
            # check completion probability
            if RobopreneurModel.random.random() < self.completion_probability:
                # task completed successfully
                task.status = "completed"
                self.wealth += task.reward
            else:
                # task failed
                task.status = "failed"
            
            # agent is now idle and no longer has a task
            self.status = "idle"
            self.curent_task = None


    # check if this is right 
    def recharge(self):
        charging_station = world_config['charging_station']
        if self.location != charging_station:
            self.move()
        else:
            # gradually increment the battery levels 
            self.battery += battery_config['recharge_rate']
            if self.battery > battery_config['max_battery']:
                self.battery = battery_config['max_battery']
            