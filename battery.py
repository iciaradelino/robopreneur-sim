# battery management logic

from tasks import Task
from movement import check_if_at_location
from utils import build_execution_details

def generate_recharge_task(model, robot):
    """
    creates a recharge task for a robot and adds it to the task queue
    the robot requests help from a human to plug it in at the charging station
    """
    # load station location from world config
    station_location = tuple(model.world_config['charging_station'])

    # load battery charging service config from services config
    services_config = model.services_config
    battery_service_config = services_config["BatteryCharging"]
    
    # create the task
    task = Task(
        task_id=model.task_counter,
        name="BatteryCharging",
        category=battery_service_config["category"],
        location=station_location,
        assigner_id=robot.agent_id  # robot is requesting the service
    )

    # add execution details to the task
    # this code is duplicate in task_assignation.py, we should create helper in utils.py
    execution_details = build_execution_details(battery_service_config, model)
    if execution_details is not None:
        task.execution_details = execution_details
        task.resolved_waypoints = execution_details["resolved_waypoints"]
        task.phase_index = execution_details["phase_index"]
        task.phase_remaining_time = execution_details["phase_remaining_time"]
        if task.resolved_waypoints:
            task.location = task.resolved_waypoints[0]["point"]
            task.time = execution_details["total_duration"]
            task.remaining_time = task.time

    # lifecycle: record creation step
    task.created_step = model.steps
    
    # add to model's task queue
    model.task_queue.append(task)
    model.task_counter += 1
    
    # store reference to this task in the robot
    robot.recharge_task = task

# complicated logic on this fucntion, double check 
def update_battery(robot):
    battery_config = robot.model.battery_config
    station = tuple(robot.model.world_config['charging_station'])

    # if the robot has a recharge task, use the station location from the task
    if robot.recharge_task is not None and robot.recharge_task.resolved_waypoints:
        station = robot.recharge_task.resolved_waypoints[0]["point"]

    # 
    if robot.awaiting_recharge:
        # latch: check once per step if the human has arrived and plugged in
        if not robot.is_charging and robot.recharge_task is not None:
            assignee_id = robot.recharge_task.assignee_id
            human = next((a for a in robot.model.agents if a.agent_id == assignee_id), None) if assignee_id else None
            if human is not None and check_if_at_location(robot, station) and check_if_at_location(human, station):
                robot.is_charging = True

        if robot.is_charging:
            # charge continuously until full - human can leave, robot stays plugged in
            robot.battery = min(robot.battery + battery_config['recharge_rate'], 100)
            if robot.battery >= 100:
                robot.status = "idle"
                robot.awaiting_recharge = False
                robot.is_charging = False
                robot.recharge_task = None
        else:
            # still traveling to station or waiting for human - battery keeps draining
            robot.battery = max(robot.battery - battery_config['drain_rate'], 0)

    else:
        # normal operation - drain and trigger recharge request if threshold is hit
        robot.battery = max(robot.battery - battery_config['drain_rate'], 0)
        if robot.battery <= battery_config['recharge_trigger']:
            generate_recharge_task(robot.model, robot)
            robot.awaiting_recharge = True
            robot.status = "busy"
            robot.target_location = station
