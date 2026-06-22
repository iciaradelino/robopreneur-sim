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
| `load_config.py` | `load_config(path)` helper that parses a config yaml into a dict |
| `app.py` | solara real-time visualization |

## quick start

```bash
# interactive visualization (uses the default config.yaml at the repo root)
python -m solara run app.py

# interactive visualization with a specific config
# set ROBOPRENEUR_CONFIG to any config.yaml path before launching
ROBOPRENEUR_CONFIG=experiments/milan/config.yaml python -m solara run app.py

# headless run + plots (recommended)
python scripts/run_full_experiment.py experiments/no_map/exp-01-battery/scenario-a/config.yaml

# simulation only
python scripts/run_experiment.py experiments/no_map/exp-01-battery/scenario-a/config.yaml

# plots only (after simulation)
python scripts/plot_results.py experiments/no_map/exp-01-battery/scenario-a
```

> on windows powershell, set the env var with `$env:ROBOPRENEUR_CONFIG="experiments/milan/config.yaml"` before running solara.

## config reference

all behaviour is controlled via a single `config.yaml`. the root-level keys are:

```
simulation    seed, duration (steps)
world         mode (square | floor_plan), charging_station,
              [square]     size, boundaries (torus wrap-around)
              [floor_plan] floor_plan {exterior [[x,y]...], holes [[[x,y]...]...]}
humans        one entry per agent type → num, initial_wealth, speed, schedule, services
robots        one entry per agent type → num, initial_wealth, initial_battery, speed,
              random_walk_interval, schedule, services
battery       recharge_rate, drain_rate, recharge_trigger, min_accept_task,
              recharge_max_wait (optional: steps before a robot re-requests help)
tasks         mode (random | deterministic), proximity_threshold,
              [random]        arrival_rate (tasks/hour)
              [deterministic] deterministic_schedule [{day, time "HH:MM", counts {Service: n}}]
services      one entry per service type → category, reward {median, sigma_g},
              phases {waypoints [{id, point, duration, fail}]}
```

- **world.mode**: `square` is a plain continuous box; `floor_plan` builds a polygon (with optional holes) and routes agents around obstacles via jupedsim. the `charging_station` point is normalized into the floor-plan coordinate frame automatically.
- **schedule**: `false` (always active) or `{active_from: "HH:MM", active_until: "HH:MM"}`. agents outside their window go inactive; an in-progress task is requeued and a robot's battery is frozen.
- **tasks.mode**: `random` draws poisson arrivals from `arrival_rate`; `deterministic` injects exact `counts` at exact `day` + `time`.
- rewards are sampled per task from a lognormal distribution (`sigma_g: 0` → deterministic). durations accept a scalar or `{mean, sd, min}`. point types: `random_in_world` | `charging_station`.

see `config.yaml` (square + floor_plan example) and `experiments/milan/config.yaml` (schedule + deterministic example) for fully annotated configs.

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
python scripts/validate_config.py experiments/no_map/exp-01-battery/scenario-a/config.yaml
```

checks: required top-level keys, field types and value ranges for all sections, `world.mode` and the matching `floor_plan` / `size` fields, `tasks.mode` and its `arrival_rate` / `deterministic_schedule`, agent `schedule` windows, service names referenced by agents exist in `services`, skill/fail values in `[0, 1]`, and correct waypoint structure.

## experiments

experiments are grouped by world type: `experiments/no_map/` (square world) and `experiments/floor_plan/` (polygon world with obstacles). each experiment folder (`exp-XX-name/`) has scenario subfolders (`scenario-a/b/c`) and an `EXPERIMENT_CARD.md`. `experiments/milan/` is a standalone 3-day scheduled + deterministic scenario. see `experiments/README.md` for full details.

| experiment | variable | scenarios |
|---|---|---|
| `exp-01-battery` | `battery.recharge_trigger` (50 / 30 / 15) | a, b, c |
| `exp-02-taskload` | `tasks.arrival_rate` (3 / 8 / 15) | a, b, c |
| `exp-03-competition` | agent population ratio (6H:2R / 4H:4R / 2H:6R) | a, b, c |

example: `python scripts/run_full_experiment.py experiments/floor_plan/exp-02-taskload/scenario-b/config.yaml`

## output files

each scenario folder contains after a run:

| file | contents |
|---|---|
| `model_data.csv` | per-step model metrics (gini, wealth, queue size, critical battery) |
| `agent_data.csv` | per-step per-agent wealth, battery, status, type |
| `task_data.csv` | task lifecycle — created/assigned/completed steps, status, phases |
| `summary.csv` | scalar summary statistics |
| `*.png` | all generated plots |
