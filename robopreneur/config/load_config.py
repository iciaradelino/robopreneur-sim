import os

import yaml

# default config lives at the repo root (three levels up from this file), independent of the cwd
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CONFIG_PATH = os.path.join(REPO_ROOT, "config.yaml")


def load_config(path=None):
    """load a simulation config from a yaml file and return the full dict.

    when no path is given the default config.yaml at the repo root is used.
    """
    config_path = path or DEFAULT_CONFIG_PATH
    with open(config_path, "r") as file:
        return yaml.safe_load(file)
