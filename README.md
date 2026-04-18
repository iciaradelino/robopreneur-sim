# robopreneur simulation

agent-based model simulating economic competition between humans and robots in a service-based economy. built with [mesa](https://mesa.readthedocs.io/) on a continuous 2d space.

## architecture

| module | role |
|---|---|
| `model.py` | mesa model — initializes agents, runs the step loop, collects metrics |
| `agents.py` | `HumanAgent` and `RobotAgent` — movement, task execution, phase traversal |
| `task_assignation.py` | poisson task generation, eligibility filtering, random assignment |
| `services.py` | service dataclass used by agents |
| `battery.py` | per-step battery drain/recharge logic for robots |
| `economy.py` | wealth transfer on task completion |
| `movement.py` | proximity check helper |
| `utils.py` | reward/duration sampling, waypoint resolution |
| `metrics.py` | gini, wealth, queue size, critical battery rate |
| `load_config.py` | loads `config.yaml` into module-level variables |
| `app.py` | solara real-time visualization |

## quick start

```bash
# interactive visualization
python -m solara run app.py

# headless run + plots (recommended)
python scripts/run_full_experiment.py experiments/exp-00/scenario-a/config.yaml

# simulation only
python scripts/run_experiment.py experiments/exp-00/scenario-a/config.yaml

# plots only (after simulation)
python scripts/plot_results.py experiments/exp-00/scenario-a
```

## config reference

all behaviour is controlled via a single `config.yaml`. the root-level keys are:

```
simulation    seed, duration (steps)
world         size, boundaries, charging_station
humans        one entry per agent type → num, initial_wealth, speed, schedule, services
robots        one entry per agent type → num, initial_wealth, initial_battery, speed,
              random_walk_interval, services
battery       recharge_rate, drain_rate, recharge_trigger, min_accept_task
tasks         arrival_rate (tasks/hour), proximity_threshold
assignment_policy   random
pricing_model       fixed
services      one entry per service type → category, reward {median, sigma_g},
              phases {waypoints [{id, point, duration, fail}], in_order, repeat}
```

rewards are sampled from a lognormal distribution (`sigma_g: 0` → deterministic). durations accept a scalar or `{mean, sd, min}`. point types: `random_in_world` | `charging_station`.

see `config.yaml` for a fully annotated example.

## scripts

| script | usage |
|---|---|
| `scripts/validate_config.py` | check a config before running |
| `scripts/run_experiment.py` | headless simulation → csv output |
| `scripts/run_full_experiment.py` | simulation + all plots |
| `scripts/plot_results.py` | generate all plots from csv |
| `scripts/plot_individual_battery.py` | battery plot for a single scenario |
| `scripts/plot_task_status.py` | task lifecycle plot |
| `scripts/compare_scenarios.py` | side-by-side scenario comparison |

## config validation

run before any simulation to catch errors early:

```bash
python scripts/validate_config.py experiments/exp-00/scenario-a/config.yaml
```

checks: required top-level keys, field types and value ranges for all sections, service names referenced by agents exist in `services`, skill/fail values in `[0, 1]`, valid `assignment_policy` and `pricing_model` values, and correct waypoint structure.

## experiments

each experiment lives in `experiments/exp-XX-name/` with scenario subfolders and an `EXPERIMENT_CARD.md`. see `experiments/README.md` for full details.

| experiment | variable | scenarios |
|---|---|---|
| `exp-01-battery` | `battery.recharge_trigger` (50 / 30 / 15) | a, b, c |
| `exp-02-taskload` | `tasks.arrival_rate` (3 / 8 / 15) | a, b, c |
| `exp-03-competition` | agent population ratio (6H:2R / 4H:4R / 2H:6R) | a, b, c |

## output files

each scenario folder contains after a run:

| file | contents |
|---|---|
| `model_data.csv` | per-step model metrics (gini, wealth, queue size, critical battery) |
| `agent_data.csv` | per-step per-agent wealth, battery, status, type |
| `task_data.csv` | task lifecycle — created/assigned/completed steps, status, phases |
| `summary.csv` | scalar summary statistics |
| `*.png` | all generated plots |
