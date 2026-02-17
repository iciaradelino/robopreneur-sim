# Robopreneur Simulation - Experiments

This folder contains systematic experiments to validate the simulator's correctness and behavior.

## Experiment Structure

Each experiment has:
- **EXPERIMENT_CARD.md**: Detailed description, expectations, and results tracking
- **scenario-a/**, **scenario-b/**, **scenario-c/**: Individual scenario configurations and results

## Available Experiments

### Experiment 01: Battery Constraint Impact Test
**Location**: `exp-01-battery/`  
**Objective**: Validate that battery mechanics correctly constrain robot economic performance  
**Variable**: `battery.recharge_trigger` (50, 30, 15)  
**Tests**: Battery management, robot constraints, economic trade-offs

### Experiment 02: Task Load Stress Test
**Location**: `exp-02-taskload/`  
**Objective**: Validate task queue management and system saturation behavior  
**Variable**: `tasks.arrival_rate` (3, 8, 15 tasks/hour)  
**Tests**: Task generation, queuing, assignment, system capacity

### Experiment 03: Agent Competition Dynamics
**Location**: `exp-03-competition/`  
**Objective**: Validate economic competition between humans and robots  
**Variable**: Population ratio (6H:2R, 4H:4R, 2H:6R)  
**Tests**: Agent competition, wealth distribution, task allocation

## How to Run Experiments

### Option 1: Run Simulation + Generate Plots (Recommended)
```bash
python scripts/run_full_experiment.py <path_to_config.yaml>
```

**Examples:**
```bash
# experiment 1, scenario a
python scripts/run_full_experiment.py experiments/exp-01-battery/scenario-a/config.yaml

# experiment 2, scenario c
python scripts/run_full_experiment.py experiments/exp-02-taskload/scenario-c/config.yaml

# experiment 3, scenario b
python scripts/run_full_experiment.py experiments/exp-03-competition/scenario-a/config.yaml
python scripts/run_full_experiment.py experiments/exp-03-competition/scenario-b/config.yaml
python scripts/run_full_experiment.py experiments/exp-03-competition/scenario-c/config.yaml
```

### Option 2: Run Simulation Only
```bash
python scripts/run_experiment.py <path_to_config.yaml>
```

Then generate plots separately:
```bash
python scripts/plot_results.py <path_to_results_directory>
```

## Output Files

After running an experiment, each scenario folder will contain:

### Data Files
- `config.yaml` - Configuration used
- `model_data.csv` - Model-level metrics (gini, system wealth, queue size, etc.)
- `agent_data.csv` - Agent-level data (wealth, battery, status per step)
- `summary.csv` - Key summary statistics

### Plots
- `gini_over_time.png` - Wealth inequality
- `system_wealth_over_time.png` - Total system wealth
- `tasks_completed_over_time.png` - Task completion
- `queue_size_over_time.png` - Queue dynamics
- `critical_battery_over_time.png` - Battery criticality
- `robot_vs_human_wealth.png` - Wealth comparison
- `avg_battery_over_time.png` - Battery levels
- `agent_status_distribution.png` - Agent states
- `wealth_trajectories.png` - Individual trajectories
- `wealth_distribution.png` - Final wealth histogram
- `wealth_boxplot.png` - Wealth box plot
- `task_completion_rate.png` - Completion rate
- `wealth_growth_rate.png` - Growth rate

## Running All Scenarios

To run a complete experiment (all 3 scenarios):

```bash
# experiment 1
python scripts/run_full_experiment.py experiments/exp-01-battery/scenario-a/config.yaml
python scripts/run_full_experiment.py experiments/exp-01-battery/scenario-b/config.yaml
python scripts/run_full_experiment.py experiments/exp-01-battery/scenario-c/config.yaml

# experiment 2
python scripts/run_full_experiment.py experiments/exp-02-taskload/scenario-a/config.yaml
python scripts/run_full_experiment.py experiments/exp-02-taskload/scenario-b/config.yaml
python scripts/run_full_experiment.py experiments/exp-02-taskload/scenario-c/config.yaml

# experiment 3
python scripts/run_full_experiment.py experiments/exp-03-competition/scenario-a/config.yaml
python scripts/run_full_experiment.py experiments/exp-03-competition/scenario-b/config.yaml
python scripts/run_full_experiment.py experiments/exp-03-competition/scenario-c/config.yaml
```

## Analyzing Results

1. **Check summary.csv** for quick metrics
2. **Review plots** to visualize trends
3. **Compare scenarios** by looking at corresponding plots side-by-side
4. **Update EXPERIMENT_CARD.md** with actual results
5. **Fill in conclusions** and validation checkboxes

## Key Metrics to Compare

### Experiment 1 (Battery)
- Critical battery rate vs recharge trigger
- Robot wealth vs charging frequency
- Task completion vs battery strategy

### Experiment 2 (Task Load)
- Queue size vs arrival rate
- Agent utilization vs load
- System saturation point

### Experiment 3 (Competition)
- Wealth inequality vs population ratio
- Per-capita wealth by agent type
- Task allocation fairness

## Troubleshooting

**Simulation runs slowly:**
- Reduce `simulation.duration` for testing
- Use fewer agents initially

**Plots look wrong:**
- Check CSV files are generated correctly
- Verify agent_data has 'Agent_Type' column

**Config not loading:**
- Check YAML syntax
- Ensure all required fields present

## Next Steps

After running all experiments:
1. Fill in ACTUAL RESULTS in each EXPERIMENT_CARD.md
2. Mark validation criteria as Pass/Fail
3. Document any bugs or unexpected behavior
4. Compare results across scenarios
5. Update conclusions with findings
