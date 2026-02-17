# all-in-one experiment runner: runs simulation + generates plots
# usage: python scripts/run_full_experiment.py <path_to_config.yaml>

import sys
import os
from pathlib import Path

# add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# import the individual scripts
from scripts.run_experiment import run_simulation
from scripts.plot_results import generate_all_plots

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/run_full_experiment.py <path_to_config.yaml>")
        print("\nexample:")
        print("  python scripts/run_full_experiment.py experiments/exp-01-battery/scenario-a/config.yaml")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if not os.path.exists(config_path):
        print(f"error: config file not found: {config_path}")
        sys.exit(1)
    
    print("="*60)
    print("STEP 1: RUNNING SIMULATION")
    print("="*60)
    output_dir = run_simulation(config_path)
    
    print("\n" + "="*60)
    print("STEP 2: GENERATING PLOTS")
    print("="*60)
    generate_all_plots(output_dir)
    
    print("\n" + "="*60)
    print("EXPERIMENT COMPLETE!")
    print("="*60)
    print(f"all results saved to: {output_dir}")
