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

# create plot component for gini coefficient
plot_component = make_plot_component("Gini")

# create the solara visualization
page = SolaraViz(
    model,  # pass the instance, not the class
    components=[space_component, plot_component],
    name="Robopreneur Simulation"
)

page
