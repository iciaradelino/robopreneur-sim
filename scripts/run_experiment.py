# headless experiment runner
# usage: python scripts/run_experiment.py <path_to_config.yaml>

import sys
import os
from pathlib import Path

# add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# single shared model and config loader (no duplicate model definition)
from model import RobopreneurModel
from load_config import load_config


def run_simulation(config_path):
    """run simulation with given config and save results"""
    print(f"loading config from: {config_path}")
    config = load_config(config_path)
    
    # get output directory (same as config directory)
    output_dir = Path(config_path).parent
    print(f"results will be saved to: {output_dir}")
    
    # create model
    print("initializing model...")
    model = RobopreneurModel(config)
    
    # run simulation
    print(f"running simulation for {config['simulation']['duration']} steps...")
    step_count = 0
    while model.running:
        model.step()
        step_count += 1
        if step_count % 100 == 0:
            print(f"  step {step_count}/{config['simulation']['duration']}")
    
    print("simulation complete!")
    
    # save model-level data
    print("saving model data...")
    model_data = model.datacollector.get_model_vars_dataframe()
    model_data.to_csv(output_dir / "model_data.csv")
    print(f"  saved: {output_dir / 'model_data.csv'}")
    
    # save agent-level data
    print("saving agent data...")
    agent_data = model.datacollector.get_agent_vars_dataframe()
    agent_data.to_csv(output_dir / "agent_data.csv")
    print(f"  saved: {output_dir / 'agent_data.csv'}")

    # save task lifecycle data (for task status graph)
    if model.completed_tasks:
        print("saving task lifecycle data...")
        rows = []
        for t in model.completed_tasks:
            if t.assigned_step is not None and t.completed_step is not None:
                total_phases = len(t.resolved_waypoints) if getattr(t, "resolved_waypoints", None) else 0
                failed_phase_id = None
                if t.status == "failed" and getattr(t, "resolved_waypoints", None):
                    phase_idx = min(max(getattr(t, "phase_index", 0), 0), len(t.resolved_waypoints) - 1)
                    failed_phase_id = t.resolved_waypoints[phase_idx].get("id")
                rows.append({
                    'task_id': t.id,
                    'task_name': t.name,
                    'created_step': t.created_step,
                    'assigned_step': t.assigned_step,
                    'completed_step': t.completed_step,
                    'status': t.status,
                    'time_unassigned': t.assigned_step - t.created_step if t.created_step is not None else None,
                    'time_in_progress': t.completed_step - t.assigned_step,
                    'total_phases': total_phases,
                    'phases_completed': getattr(t, "phase_index", 0),
                    'failed_phase_id': failed_phase_id,
                })
        if rows:
            task_df = pd.DataFrame(rows)
            task_df.to_csv(output_dir / "task_data.csv", index=False)
            print(f"  saved: {output_dir / 'task_data.csv'}")
    
    # create summary stats
    print("generating summary statistics...")
    summary = {
        'total_steps': step_count,
        'seed': config['simulation']['seed'],
        'final_gini': model_data['Gini'].iloc[-1],
        'final_system_wealth': model_data['System_Wealth'].iloc[-1],
        'total_tasks_completed': model_data['Tasks_Completed'].iloc[-1],
        'avg_queue_size': model_data['Queue_Size'].mean(),
        'max_queue_size': model_data['Queue_Size'].max(),
        'avg_critical_battery_rate': model_data['Critical_Battery'].mean(),
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(output_dir / "summary.csv", index=False)
    print(f"  saved: {output_dir / 'summary.csv'}")
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    for key, value in summary.items():
        print(f"{key}: {value}")
    print("="*50)
    
    return output_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/run_experiment.py <path_to_config.yaml>")
        print("\nexample:")
        print("  python scripts/run_experiment.py experiments/no_map/exp-01-battery/scenario-a/config.yaml")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if not os.path.exists(config_path):
        print(f"error: config file not found: {config_path}")
        sys.exit(1)
    
    output_dir = run_simulation(config_path)
    
    print("\nnext step: generate plots with:")
    print(f"  python scripts/plot_results.py {output_dir}")
