# generate only task_status.png for one or more scenario folders
# requires task_data.csv (produced by run_experiment.py)
# usage:
#   python scripts/plot_task_status.py experiments/exp-02-taskload/scenario-a
#   python scripts/plot_task_status.py experiments/exp-02-taskload

import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)


def plot_task_status(results_dir):
    """generate task_status.png for a single scenario folder"""
    results_dir = Path(results_dir)
    task_data_path = results_dir / "task_data.csv"

    if not task_data_path.exists():
        raise FileNotFoundError(f"task_data.csv not found: {task_data_path} (re-run simulation to generate)")

    task_data = pd.read_csv(task_data_path)
    if task_data.empty or 'time_unassigned' not in task_data.columns:
        print(f"  skip {results_dir}: task_data empty or missing columns")
        return

    avg_unassigned = task_data['time_unassigned'].dropna().mean()
    avg_in_progress = task_data['time_in_progress'].dropna().mean()

    fig, ax = plt.subplots(figsize=(8, 5))
    states = ['unassigned\n(queue)', 'in progress\n(execution)', 'completed\n(terminal)']
    values = [avg_unassigned, avg_in_progress, 0]
    colors = ['#ff7f0e', '#2ca02c', '#1f77b4']

    bars = ax.bar(states, values, color=colors, alpha=0.8)
    ax.set_ylabel('average time (steps)')
    ax.set_title('average time each task spends in each state')
    ax.grid(axis='y', alpha=0.3)

    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.1f}',
                    ha='center', va='bottom', fontsize=10)
    ax.text(bars[2].get_x() + bars[2].get_width()/2., 0, '0',
            ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    out_path = results_dir / 'task_status.png'
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"  saved: {out_path}")


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/plot_task_status.py <path>")
        print("  path = single scenario folder, or experiment folder (e.g. exp-02-taskload)")
        print("")
        print("examples:")
        print("  python scripts/plot_task_status.py experiments/exp-02-taskload/scenario-a")
        print("  python scripts/plot_task_status.py experiments/exp-02-taskload")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"error: path not found: {path}")
        sys.exit(1)

    # single scenario folder (contains task_data.csv)
    if (path / "task_data.csv").exists():
        print(f"generating task_status.png for: {path}")
        plot_task_status(path)
        return

    # experiment folder: run for all scenario-a, scenario-b, scenario-c
    scenarios = ["scenario-a", "scenario-b", "scenario-c"]
    for scenario in scenarios:
        scenario_dir = path / scenario
        if (scenario_dir / "task_data.csv").exists():
            print(f"generating for: {scenario_dir}")
            plot_task_status(scenario_dir)
        else:
            print(f"skip {scenario_dir}: no task_data.csv (re-run simulation)")

    print("done.")


if __name__ == "__main__":
    main()
