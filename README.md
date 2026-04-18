# robopreneur simulation

agent-based model simulating economic competition between humans and robots in a service-based economy.

## features
- continuous 2d spatial environment
- battery-constrained robot agents
- service-based task economy
- configurable via yaml
- real-time visualization with solara
- headless experiment runner with csv export

## quick start

### run visualization
```bash
python -m solara run app.py
```

### run headless experiments
```bash
# run single experiment with plots
python scripts/run_full_experiment.py experiments/exp-01-battery/scenario-a/config.yaml

# or run simulation only
python scripts/run_experiment.py experiments/exp-01-battery/scenario-a/config.yaml

# then generate plots
python scripts/plot_results.py experiments/exp-01-battery/scenario-a
```

## experiments

see `experiments/README.md` for detailed documentation.

three validation experiments included:
1. **battery constraint test** - validates battery mechanics impact on robot performance
2. **task load stress test** - validates queue management and system saturation
3. **agent competition dynamics** - validates economic competition patterns

each experiment has scenario configs, expected results, and comprehensive plotting.

## validating config.yaml

run before any simulation to catch misconfigured files early:
```bash
python scripts/validate_config.py experiments/exp-00/scenario-a/config.yaml
```

checks the following:
- **required sections** — all top-level keys are present (`simulation`, `world`, `humans`, `robots`, `battery`, `tasks`, `assignment_policy`, `pricing_model`, `services`)
- **simulation** — `seed` is an int, `duration` is a positive int
- **world** — `size` is positive, `boundaries` is a bool, `charging_station` is a 2-element numeric list
- **agents** — each human/robot has the correct fields; every service they list must be defined in `services`; `skill` values are between 0 and 1
- **battery** — all four fields (`recharge_rate`, `drain_rate`, `recharge_trigger`, `min_accept_task`) are positive numbers
- **tasks** — `arrival_rate` and `proximity_threshold` are positive numbers
- **assignment_policy / pricing_model** — values are from the known valid set
- **services** — each service has a valid `category`, a `reward` with `median` and `sigma_g`, and properly structured `phases` (waypoints with `id`, `point.type`, `duration`, `fail`)