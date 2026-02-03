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

# create plot components for metrics
gini_plot = make_plot_component("Gini")
battery_plot = make_plot_component("Avg_Battery")
wealth_plot = make_plot_component(["Human_Wealth", "Robot_Wealth"])
allocation_plot = make_plot_component(["Idle_Ratio", "Exec_Ratio", "Busy_Ratio"])

# create the solara visualization
page = SolaraViz(
    model,  # pass the instance, not the class
    components=[space_component, gini_plot, battery_plot, wealth_plot, allocation_plot],
    name="Robopreneur Simulation"
)

page
