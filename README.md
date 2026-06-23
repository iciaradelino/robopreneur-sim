# Robopreneur Sim

An agent-based simulation (built on [Mesa](https://mesa.readthedocs.io/)) of robots and humans
offering paid services in a shared workspace. Agents move through a continuous space or a
floor plan, pick up tasks from a queue, earn wealth, and (for robots) manage battery and
recharging. The model tracks system metrics such as task throughput, wealth distribution
(Gini), queue size, and critical-battery rate.

## Run with Docker

Build the image:

```bash
docker build -t robopreneur-sim .
```

### Interactive visualization (default)

Run the Solara dashboard and open it in your browser:

```bash
docker run --rm -p 8765:8765 robopreneur-sim
```

Then visit **http://localhost:8765**.

### Change the simulation settings

The simulation reads its parameters from [`config.yaml`](config.yaml) — edit that file to
change the number of agents, services, battery behaviour, task rate, run length, etc.

The `Dockerfile` copies `config.yaml` into the image at build time, so after editing it just
rebuild (`docker build -t robopreneur-sim .`). To iterate without rebuilding each time, mount
your local file over the one in the container:

```bash
docker run --rm -p 8765:8765 \
  -v "$(pwd)/config.yaml:/app/config.yaml" \
  robopreneur-sim
```

### Headless experiment run

Run a simulation without the UI and write CSV results back to your host. Mount a
directory so the output (`model_data.csv`, `agent_data.csv`, `task_data.csv`,
`summary.csv`) lands next to the config:

```bash
docker run --rm \
  -v "$(pwd)/experiments:/app/experiments" \
  robopreneur-sim \
  python scripts/run_experiment.py experiments/floor_plan/exp-01-battery/scenario-a/config.yaml
```

## Run locally (without Docker)

```bash
pip install -r requirements.txt

# interactive dashboard
solara run app.py

# headless experiment
python scripts/run_experiment.py <path/to/config.yaml>
```

## Configuration

All simulation parameters live in [`config.yaml`](config.yaml): simulation length and seed,
world geometry (`square` or `floor_plan`), human/robot agents and their services, battery
behaviour, task arrival rate, and per-service rewards and phases. Pass an alternate config
via the `ROBOPRENEUR_CONFIG` environment variable (dashboard) or as the CLI argument
(headless).

## Project layout

| Path | Purpose |
| --- | --- |
| `model.py` | Mesa model: world setup, stepping, data collection |
| `agents.py` | Human and robot agent behaviour |
| `task_assignation.py`, `tasks.py` | Task generation and assignment |
| `battery.py`, `floor_plan.py`, `schedule.py` | Battery, geometry, and scheduling logic |
| `metrics.py` | Model-level reporters (Gini, throughput, etc.) |
| `app.py` | Solara dashboard and plot components |
| `scripts/` | Headless runners and plotting utilities |
| `experiments/` | Predefined experiment configs and results |

## Outputs

Headless runs produce per-run CSVs and a one-line `summary.csv`. Use the helpers in
`scripts/` (e.g. `plot_results.py`, `compare_scenarios.py`) to generate plots from them.
