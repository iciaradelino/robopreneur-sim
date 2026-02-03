# minimal solara app to run the mesa model
from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from model import RobopreneurModel

# define the portrayal of the agents
def agent_portrayal(agent):
    if hasattr(agent, 'battery'):
        # robot agent
        return {
            "color": "blue",
            "size": 30,
        }
    else:
        # human agent
        return {
            "color": "green",
            "size": 30,
        }

# create a model instance
model = RobopreneurModel()

# create space visualization component
space_component = make_space_component(agent_portrayal)

# create plot components for metrics (limited to last 500 steps)
plot_config = {"data_limit": 500}
gini_plot = make_plot_component("Gini", **plot_config)
battery_plot = make_plot_component("Avg_Battery", **plot_config)
wealth_plot = make_plot_component(["Human_Wealth", "Robot_Wealth"], **plot_config)
allocation_plot = make_plot_component(["Idle_Ratio", "Exec_Ratio", "Busy_Ratio"], **plot_config)

# create the solara visualization
page = SolaraViz(
    model,  # pass the instance, not the class
    components=[space_component, gini_plot, battery_plot, wealth_plot, allocation_plot],
    name="Robopreneur Simulation"
)

page
