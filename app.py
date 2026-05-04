# minimal solara app to run the mesa model
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mesa.visualization import SolaraViz, make_plot_component
from mesa.visualization.utils import update_counter
import pandas as pd
import solara
from model import RobopreneurModel

def _collect_in_progress_tasks(model):
    """collect active tasks from agents"""
    active_tasks = []
    for agent in model.agents:
        task = getattr(agent, "current_task", None)
        if task is not None:
            active_tasks.append(task)
    return active_tasks


def _agent_history_dataframe(model):
    """return agent history in a flat dataframe"""
    history = model.datacollector.get_agent_vars_dataframe()
    if history is None or history.empty:
        return pd.DataFrame()

    history = history.reset_index()

    if "AgentID" not in history.columns:
        for candidate in ("agent_id", "AgentId", "unique_id"):
            if candidate in history.columns:
                history = history.rename(columns={candidate: "AgentID"})
                break
    if "Step" not in history.columns:
        for candidate in ("step", "StepId"):
            if candidate in history.columns:
                history = history.rename(columns={candidate: "Step"})
                break

    return history

@solara.component
def floor_plan_map_component(model):
    """render a map with true geometry, agents, and tasks"""
    update_counter.get()
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.subplots_adjust(right=0.76)

    # draw the world geometry
    if getattr(model, "floor_plan", None):
        geometry = model.floor_plan.geometry
        shell_x, shell_y = geometry.exterior.xy
        ax.fill(
            shell_x,
            shell_y,
            facecolor="#efefef",
            edgecolor="#6fa8dc",
            linewidth=2.0,
            zorder=1,
        )
        for hole in geometry.interiors:
            hole_x, hole_y = hole.xy
            ax.fill(
                hole_x,
                hole_y,
                facecolor="white",
                edgecolor="#e06666",
                linewidth=1.8,
                hatch="//",
                zorder=2,
            )
        min_x, min_y, max_x, max_y = geometry.bounds
        pad_x = max((max_x - min_x) * 0.05, 0.2)
        pad_y = max((max_y - min_y) * 0.05, 0.2)
        ax.set_xlim(min_x - pad_x, max_x + pad_x)
        ax.set_ylim(min_y - pad_y, max_y + pad_y)
    else:
        # fallback for square mode
        world_size = model.world_config["size"]
        ax.add_patch(
            plt.Rectangle(
                (0, 0),
                world_size,
                world_size,
                facecolor="#efefef",
                edgecolor="#6fa8dc",
                linewidth=2.0,
                zorder=1,
            )
        )
        ax.set_xlim(0, world_size)
        ax.set_ylim(0, world_size)

    # draw charging station
    charging_x, charging_y = model.world_config["charging_station"]
    ax.scatter(
        charging_x,
        charging_y,
        marker="*",
        s=130,
        c="#f39c12",
        edgecolors="black",
        linewidths=0.6,
        zorder=6,
    )

    # draw pending and active tasks
    pending_tasks = list(model.task_queue)
    active_tasks = _collect_in_progress_tasks(model)

    if pending_tasks:
        pending_x = [task.location[0] for task in pending_tasks]
        pending_y = [task.location[1] for task in pending_tasks]
        ax.scatter(pending_x, pending_y, marker="x", s=55, c="#cc0000", zorder=5)

    if active_tasks:
        active_x = [task.location[0] for task in active_tasks]
        active_y = [task.location[1] for task in active_tasks]
        ax.scatter(active_x, active_y, marker="D", s=40, c="#ff9900", zorder=5)

    # draw agents
    robot_x = []
    robot_y = []
    human_x = []
    human_y = []
    for agent in model.agents:
        if hasattr(agent, "battery"):
            robot_x.append(agent.pos[0])
            robot_y.append(agent.pos[1])
        else:
            human_x.append(agent.pos[0])
            human_y.append(agent.pos[1])

    if robot_x:
        ax.scatter(
            robot_x,
            robot_y,
            s=60,
            c="blue",
            edgecolors="black",
            linewidths=0.5,
            zorder=7,
        )
    if human_x:
        ax.scatter(
            human_x,
            human_y,
            s=60,
            c="green",
            edgecolors="black",
            linewidths=0.5,
            zorder=7,
        )

    # basic map formatting
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("map view")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.2)

    # keep legend stable even when a category is empty
    legend_handles = [
        Line2D([0], [0], marker="o", color="w", label="robot", markerfacecolor="blue", markeredgecolor="black", markersize=7),
        Line2D([0], [0], marker="o", color="w", label="human", markerfacecolor="green", markeredgecolor="black", markersize=7),
        Line2D([0], [0], marker="x", color="#cc0000", label="pending task", linestyle="None", markersize=7),
        Line2D([0], [0], marker="D", color="#ff9900", label="active task", linestyle="None", markersize=6),
        Line2D([0], [0], marker="*", color="#f39c12", label="charging station", linestyle="None", markersize=9),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
        framealpha=0.95,
    )

    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def individual_robot_battery_component(model):
    """plot individual robot battery levels over time"""
    update_counter.get()
    fig, ax = plt.subplots(figsize=(8, 4.5))

    history = _agent_history_dataframe(model)
    required_cols = {"Step", "AgentID", "Battery"}
    if history.empty or not required_cols.issubset(history.columns):
        ax.text(0.5, 0.5, "no battery history yet", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        solara.FigureMatplotlib(fig)
        plt.close(fig)
        return

    if "Agent_Type" in history.columns:
        robot_data = history[history["Agent_Type"] == "robot"].copy()
    else:
        robot_data = history[history["Battery"].notna()].copy()

    if robot_data.empty:
        ax.text(0.5, 0.5, "no robot battery data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        for agent_id in robot_data["AgentID"].unique():
            trajectory = robot_data[robot_data["AgentID"] == agent_id]
            ax.plot(trajectory["Step"], trajectory["Battery"], linewidth=1.5, alpha=0.75, label=agent_id)
        ax.set_xlabel("step")
        ax.set_ylabel("battery level (%)")
        ax.set_title("individual robot battery levels")
        ax.grid(alpha=0.3)
        ax.legend(loc="best", fontsize=8)

    fig.tight_layout()
    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def individual_wealth_trajectories_component(model):
    """plot individual wealth trajectories over time"""
    update_counter.get()
    fig, ax = plt.subplots(figsize=(8, 4.5))

    history = _agent_history_dataframe(model)
    required_cols = {"Step", "AgentID", "Wealth"}
    if history.empty or not required_cols.issubset(history.columns):
        ax.text(0.5, 0.5, "no wealth history yet", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        solara.FigureMatplotlib(fig)
        plt.close(fig)
        return

    for agent_id in history["AgentID"].unique():
        trajectory = history[history["AgentID"] == agent_id]
        if "Agent_Type" in history.columns:
            agent_type = trajectory["Agent_Type"].iloc[0]
        else:
            agent_type = "robot" if trajectory["Battery"].notna().any() else "human"
        color = "blue" if agent_type == "robot" else "green"
        ax.plot(trajectory["Step"], trajectory["Wealth"], color=color, alpha=0.6, linewidth=1.0)

    legend_handles = [
        Line2D([0], [0], color="blue", linewidth=2, label="robots"),
        Line2D([0], [0], color="green", linewidth=2, label="humans"),
    ]
    ax.legend(handles=legend_handles, loc="best")
    ax.set_xlabel("step")
    ax.set_ylabel("wealth")
    ax.set_title("individual wealth trajectories")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def task_status_component(model):
    """plot current task status counts"""
    update_counter.get()
    fig, ax = plt.subplots(figsize=(6.5, 4.5))

    pending_count = len(model.task_queue)
    active_count = len(_collect_in_progress_tasks(model))
    failed_count = sum(1 for task in model.completed_tasks if getattr(task, "status", None) == "failed")

    labels = ["pending", "active", "failed"]
    values = [pending_count, active_count, failed_count]
    colors = ["#cc0000", "#ff9900", "#8e44ad"]

    bars = ax.bar(labels, values, color=colors, alpha=0.85)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, str(value), ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("count")
    ax.set_title("task status")
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def agent_use_component(model):
    """plot agent status distribution over time"""
    update_counter.get()
    fig, ax = plt.subplots(figsize=(8, 4.5))

    history = _agent_history_dataframe(model)
    required_cols = {"Step", "Status"}
    if history.empty or not required_cols.issubset(history.columns):
        ax.text(0.5, 0.5, "no agent status history yet", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        solara.FigureMatplotlib(fig)
        plt.close(fig)
        return

    status_counts = history.groupby(["Step", "Status"]).size().unstack(fill_value=0)
    if status_counts.empty:
        ax.text(0.5, 0.5, "no agent status history yet", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        status_pct = status_counts.div(status_counts.sum(axis=1), axis=0) * 100
        status_pct.plot.area(ax=ax, alpha=0.7, stacked=True)
        ax.set_xlabel("step")
        ax.set_ylabel("percentage of agents (%)")
        ax.set_title("agent use (status distribution)")
        ax.legend(title="status", loc="upper right")

    fig.tight_layout()
    solara.FigureMatplotlib(fig)
    plt.close(fig)

# create a model instance
model = RobopreneurModel()

# use the custom map as the space visualization
space_component = floor_plan_map_component
battery_levels_component = individual_robot_battery_component
wealth_trajectories_component = individual_wealth_trajectories_component
task_status_component_plot = task_status_component
agent_use_component_plot = agent_use_component

# create plot components for metrics
gini_plot = make_plot_component("Gini")
tasks_completed_plot = make_plot_component("Tasks_Completed")
system_wealth_plot = make_plot_component("System_Wealth")
queue_size_plot = make_plot_component("Queue_Size")
critical_battery_plot = make_plot_component("Critical_Battery")

# create the solara visualization
page = SolaraViz(
    model,  # pass the instance, not the class
    components=[
        space_component,
        gini_plot,
        tasks_completed_plot,
        system_wealth_plot,
        queue_size_plot,
        critical_battery_plot,
        battery_levels_component,
        wealth_trajectories_component,
        task_status_component_plot,
        agent_use_component_plot,
    ],
    name="Robopreneur Simulation"
)

page
