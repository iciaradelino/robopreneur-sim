# plotting and analysis script for experiment results
# usage: python scripts/plot_results.py <path_to_results_directory>

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)

def load_data(results_dir):
    """load model and agent data from csv files"""
    model_data_path = results_dir / "model_data.csv"
    agent_data_path = results_dir / "agent_data.csv"
    
    if not model_data_path.exists():
        raise FileNotFoundError(f"model data not found: {model_data_path}")
    if not agent_data_path.exists():
        raise FileNotFoundError(f"agent data not found: {agent_data_path}")
    
    model_data = pd.read_csv(model_data_path, index_col=0)
    agent_data = pd.read_csv(agent_data_path)
    
    return model_data, agent_data


def plot_common_metrics(model_data, output_dir):
    """generate common plots for all experiments"""
    print("generating common metric plots...")
    
    # 1. gini coefficient over time
    fig, ax = plt.subplots()
    ax.plot(model_data.index, model_data['Gini'], linewidth=2)
    ax.set_xlabel('step')
    ax.set_ylabel('gini coefficient')
    ax.set_title('wealth inequality over time')
    plt.tight_layout()
    plt.savefig(output_dir / 'gini_over_time.png', dpi=300)
    plt.close()
    print("  saved: gini_over_time.png")
    
    # 2. total system wealth over time
    fig, ax = plt.subplots()
    ax.plot(model_data.index, model_data['System_Wealth'], linewidth=2, color='green')
    ax.set_xlabel('step')
    ax.set_ylabel('total system wealth')
    ax.set_title('total system wealth over time')
    plt.tight_layout()
    plt.savefig(output_dir / 'system_wealth_over_time.png', dpi=300)
    plt.close()
    print("  saved: system_wealth_over_time.png")
    
    # 3. tasks completed (cumulative)
    fig, ax = plt.subplots()
    ax.plot(model_data.index, model_data['Tasks_Completed'], linewidth=2, color='orange')
    ax.set_xlabel('step')
    ax.set_ylabel('cumulative tasks completed')
    ax.set_title('task completion over time')
    plt.tight_layout()
    plt.savefig(output_dir / 'tasks_completed_over_time.png', dpi=300)
    plt.close()
    print("  saved: tasks_completed_over_time.png")
    
    # 4. task queue size over time
    fig, ax = plt.subplots()
    ax.plot(model_data.index, model_data['Queue_Size'], linewidth=2, color='red')
    ax.set_xlabel('step')
    ax.set_ylabel('queue size')
    ax.set_title('task queue size over time')
    plt.tight_layout()
    plt.savefig(output_dir / 'queue_size_over_time.png', dpi=300)
    plt.close()
    print("  saved: queue_size_over_time.png")


def plot_battery_metrics(model_data, agent_data, output_dir):
    """generate battery-specific plots (experiment 1)"""
    print("generating battery-specific plots...")
    
    # 1. critical battery rate over time
    fig, ax = plt.subplots()
    ax.plot(model_data.index, model_data['Critical_Battery'], linewidth=2, color='red')
    ax.set_xlabel('step')
    ax.set_ylabel('critical battery rate')
    ax.set_title('percentage of robots with critical battery (<20%)')
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(output_dir / 'critical_battery_over_time.png', dpi=300)
    plt.close()
    print("  saved: critical_battery_over_time.png")
    
    # 2. robot vs human wealth (final values)
    # get final step data
    final_step = agent_data['Step'].max()
    final_agent_data = agent_data[agent_data['Step'] == final_step]
    
    # separate by agent type
    robot_wealth = final_agent_data[final_agent_data['Agent_Type'] == 'robot']['Wealth']
    human_wealth = final_agent_data[final_agent_data['Agent_Type'] == 'human']['Wealth']
    
    fig, ax = plt.subplots()
    x = ['robots', 'humans']
    means = [robot_wealth.mean(), human_wealth.mean()]
    stds = [robot_wealth.std(), human_wealth.std()]
    
    ax.bar(x, means, yerr=stds, capsize=5, color=['blue', 'green'], alpha=0.7)
    ax.set_ylabel('final wealth (mean ± std)')
    ax.set_title('final wealth comparison: robots vs humans')
    plt.tight_layout()
    plt.savefig(output_dir / 'robot_vs_human_wealth.png', dpi=300)
    plt.close()
    print("  saved: robot_vs_human_wealth.png")
    
    # 3. individual robot battery levels over time
    robot_data = agent_data[agent_data['Agent_Type'] == 'robot']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # plot each robot's battery trajectory
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
    plt.savefig(output_dir / 'individual_battery_levels.png', dpi=300)
    plt.close()
    print("  saved: individual_battery_levels.png")


def plot_agent_status_distribution(agent_data, output_dir):
    """plot agent status distribution over time"""
    print("generating agent status distribution plot...")
    
    # count status at each step
    status_counts = agent_data.groupby(['Step', 'Status']).size().unstack(fill_value=0)
    
    # normalize to percentages
    status_pct = status_counts.div(status_counts.sum(axis=1), axis=0) * 100
    
    fig, ax = plt.subplots()
    status_pct.plot.area(ax=ax, alpha=0.7, stacked=True)
    ax.set_xlabel('step')
    ax.set_ylabel('percentage of agents (%)')
    ax.set_title('agent status distribution over time')
    ax.legend(title='status', loc='upper right')
    plt.tight_layout()
    plt.savefig(output_dir / 'agent_status_distribution.png', dpi=300)
    plt.close()
    print("  saved: agent_status_distribution.png")


def plot_wealth_trajectories(agent_data, output_dir):
    """plot individual agent wealth trajectories"""
    print("generating wealth trajectory plot...")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # plot each agent
    for agent_id in agent_data['AgentID'].unique():
        agent_trajectory = agent_data[agent_data['AgentID'] == agent_id]
        agent_type = agent_trajectory['Agent_Type'].iloc[0]
        color = 'blue' if agent_type == 'robot' else 'green'
        alpha = 0.6
        ax.plot(agent_trajectory['Step'], agent_trajectory['Wealth'], 
                color=color, alpha=alpha, linewidth=1)
    
    # create legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='blue', linewidth=2, label='robots'),
        Line2D([0], [0], color='green', linewidth=2, label='humans')
    ]
    ax.legend(handles=legend_elements)
    
    ax.set_xlabel('step')
    ax.set_ylabel('wealth')
    ax.set_title('individual agent wealth trajectories')
    plt.tight_layout()
    plt.savefig(output_dir / 'wealth_trajectories.png', dpi=300)
    plt.close()
    print("  saved: wealth_trajectories.png")


def plot_wealth_distribution(agent_data, output_dir):
    """plot final wealth distribution"""
    print("generating wealth distribution plot...")
    
    # get final step data
    final_step = agent_data['Step'].max()
    final_agent_data = agent_data[agent_data['Step'] == final_step]
    
    fig, ax = plt.subplots()
    
    # separate histograms for robots and humans
    robot_wealth = final_agent_data[final_agent_data['Agent_Type'] == 'robot']['Wealth']
    human_wealth = final_agent_data[final_agent_data['Agent_Type'] == 'human']['Wealth']
    
    ax.hist(robot_wealth, bins=20, alpha=0.6, label='robots', color='blue')
    ax.hist(human_wealth, bins=20, alpha=0.6, label='humans', color='green')
    
    ax.set_xlabel('final wealth')
    ax.set_ylabel('number of agents')
    ax.set_title('final wealth distribution by agent type')
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'wealth_distribution.png', dpi=300)
    plt.close()
    print("  saved: wealth_distribution.png")


def plot_wealth_boxplot(agent_data, output_dir):
    """box plot of wealth by agent type"""
    print("generating wealth boxplot...")
    
    # get final step data
    final_step = agent_data['Step'].max()
    final_agent_data = agent_data[agent_data['Step'] == final_step]
    
    fig, ax = plt.subplots()
    
    data_to_plot = [
        final_agent_data[final_agent_data['Agent_Type'] == 'human']['Wealth'],
        final_agent_data[final_agent_data['Agent_Type'] == 'robot']['Wealth']
    ]
    
    bp = ax.boxplot(data_to_plot, labels=['humans', 'robots'], patch_artist=True)
    bp['boxes'][0].set_facecolor('green')
    bp['boxes'][1].set_facecolor('blue')
    
    ax.set_ylabel('final wealth')
    ax.set_title('final wealth distribution: humans vs robots')
    plt.tight_layout()
    plt.savefig(output_dir / 'wealth_boxplot.png', dpi=300)
    plt.close()
    print("  saved: wealth_boxplot.png")


def plot_task_completion_rate(model_data, output_dir):
    """plot task completion rate (tasks/step)"""
    print("generating task completion rate plot...")
    
    # calculate rate as difference between consecutive steps
    completion_rate = model_data['Tasks_Completed'].diff().fillna(0)
    
    # smooth with rolling average
    window_size = 20
    completion_rate_smooth = completion_rate.rolling(window=window_size, center=True).mean()
    
    fig, ax = plt.subplots()
    ax.plot(model_data.index, completion_rate_smooth, linewidth=2, color='orange')
    ax.set_xlabel('step')
    ax.set_ylabel('tasks completed per step (20-step moving avg)')
    ax.set_title('task completion rate over time')
    plt.tight_layout()
    plt.savefig(output_dir / 'task_completion_rate.png', dpi=300)
    plt.close()
    print("  saved: task_completion_rate.png")


def plot_wealth_growth_rate(model_data, output_dir):
    """plot wealth growth rate over time"""
    print("generating wealth growth rate plot...")
    
    # calculate growth rate
    growth_rate = model_data['System_Wealth'].diff().fillna(0)
    
    # smooth with rolling average
    window_size = 20
    growth_rate_smooth = growth_rate.rolling(window=window_size, center=True).mean()
    
    fig, ax = plt.subplots()
    ax.plot(model_data.index, growth_rate_smooth, linewidth=2, color='green')
    ax.set_xlabel('step')
    ax.set_ylabel('wealth growth per step (20-step moving avg)')
    ax.set_title('system wealth growth rate over time')
    plt.tight_layout()
    plt.savefig(output_dir / 'wealth_growth_rate.png', dpi=300)
    plt.close()
    print("  saved: wealth_growth_rate.png")


def plot_task_status(results_dir):
    """plot average time (steps) each task spends in each state: unassigned, in progress, completed (0)"""
    results_dir = Path(results_dir)
    task_data_path = results_dir / "task_data.csv"

    if not task_data_path.exists():
        print("  skip task_status: no task_data.csv (re-run simulation to generate)")
        return

    task_data = pd.read_csv(task_data_path)
    if task_data.empty or 'time_unassigned' not in task_data.columns:
        print("  skip task_status: task_data empty or missing columns")
        return

    # average steps in each state (completed is terminal, so 0 or N/A)
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
    plt.savefig(results_dir / 'task_status.png', dpi=300)
    plt.close()
    print("  saved: task_status.png")


def generate_all_plots(results_dir):
    """generate all plots for a given experiment"""
    results_dir = Path(results_dir)
    print(f"\nloading data from: {results_dir}")
    
    model_data, agent_data = load_data(results_dir)
    
    print(f"model data: {len(model_data)} steps")
    print(f"agent data: {len(agent_data)} records")
    
    # generate all plots
    plot_common_metrics(model_data, results_dir)
    plot_battery_metrics(model_data, agent_data, results_dir)
    plot_agent_status_distribution(agent_data, results_dir)
    plot_wealth_trajectories(agent_data, results_dir)
    plot_wealth_distribution(agent_data, results_dir)
    plot_wealth_boxplot(agent_data, results_dir)
    plot_task_completion_rate(model_data, results_dir)
    plot_wealth_growth_rate(model_data, results_dir)
    plot_task_status(results_dir)
    
    print(f"\nall plots saved to: {results_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/plot_results.py <path_to_results_directory>")
        print("\nexample:")
        print("  python scripts/plot_results.py experiments/exp-01-battery/scenario-a")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    
    if not os.path.exists(results_dir):
        print(f"error: results directory not found: {results_dir}")
        sys.exit(1)
    
    generate_all_plots(results_dir)
