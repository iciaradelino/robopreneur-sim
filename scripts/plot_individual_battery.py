# generate only individual_battery_levels.png for one or more scenario folders
# usage:
#   python scripts/plot_individual_battery.py experiments/exp-01-battery/scenario-a
#   python scripts/plot_individual_battery.py experiments/exp-01-battery

import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)


def plot_individual_battery(results_dir):
    """generate individual_battery_levels.png for a single scenario folder"""
    results_dir = Path(results_dir)
    agent_data_path = results_dir / "agent_data.csv"

    if not agent_data_path.exists():
        raise FileNotFoundError(f"agent data not found: {agent_data_path}")

    agent_data = pd.read_csv(agent_data_path)
    robot_data = agent_data[agent_data['Agent_Type'] == 'robot']

    if robot_data.empty:
        print(f"  skip {results_dir}: no robot agents")
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    for agent_id in robot_data['AgentID'].unique():
        robot_trajectory = robot_data[robot_data['AgentID'] == agent_id]
        ax.plot(robot_trajectory['Step'], robot_trajectory['Battery'],
                alpha=0.7, linewidth=1.5, label=agent_id)

    ax.set_xlabel('step')
    ax.set_ylabel('battery level (%)')
    ax.set_title('individual robot battery levels over time')
    ax.legend(loc='best', fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    out_path = results_dir / 'individual_battery_levels.png'
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"  saved: {out_path}")


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/plot_individual_battery.py <path>")
        print("  path = single scenario folder, or experiment folder (exp-01-battery)")
        print("")
        print("examples:")
        print("  python scripts/plot_individual_battery.py experiments/exp-01-battery/scenario-a")
        print("  python scripts/plot_individual_battery.py experiments/exp-01-battery")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"error: path not found: {path}")
        sys.exit(1)

    # single scenario folder (contains agent_data.csv)
    if (path / "agent_data.csv").exists():
        print(f"generating individual_battery_levels.png for: {path}")
        plot_individual_battery(path)
        return

    # experiment folder: run for all scenario-a, scenario-b, scenario-c
    scenarios = ["scenario-a", "scenario-b", "scenario-c"]
    for scenario in scenarios:
        scenario_dir = path / scenario
        if (scenario_dir / "agent_data.csv").exists():
            print(f"generating for: {scenario_dir}")
            plot_individual_battery(scenario_dir)
        else:
            print(f"skip {scenario_dir}: no agent_data.csv")

    print("done.")


if __name__ == "__main__":
    main()
