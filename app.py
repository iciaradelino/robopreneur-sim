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
tasks_completed_plot = make_plot_component("Tasks_Completed")
system_wealth_plot = make_plot_component("System_Wealth")
queue_size_plot = make_plot_component("Queue_Size")
critical_battery_plot = make_plot_component("Critical_Battery")

# create the solara visualization
page = SolaraViz(
    model,  # pass the instance, not the class
    components=[space_component, gini_plot, tasks_completed_plot, system_wealth_plot, queue_size_plot, critical_battery_plot],
    name="Robopreneur Simulation"
)

page
