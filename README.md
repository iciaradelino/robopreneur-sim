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
