from pathlib import Path

import yaml

DEMO_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = DEMO_DIR / "out"
DEPLOYMENTS_PATH = OUT_DIR / "deployments.json"


def load_config(path=DEMO_DIR / "demo_config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
