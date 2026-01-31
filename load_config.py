import yaml

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

sim_config = config['simulation']
world_config = config['world']
humans_config = config['humans']
robots_config = config['robots']
battery_config = config['battery']
tasks_config = config['tasks']
assignemnt_policy_config = config['assignemnt_policy']
pricing_model_config = config['pricing_model']
services_config = config['services']
