import os

import yaml

# default config lives next to this file (repo root), independent of the cwd
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def load_config(path=None):
    """load a simulation config from a yaml file and return the full dict.

    when no path is given the default config.yaml at the repo root is used.
    """
    config_path = path or DEFAULT_CONFIG_PATH
    with open(config_path, "r") as file:
        return yaml.safe_load(file)
