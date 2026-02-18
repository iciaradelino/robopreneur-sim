# battery management logic

from tasks import Task
from movement import check_if_at_location

def generate_recharge_task(model, robot):
    """
    creates a recharge task for a robot and adds it to the task queue
    the robot requests help from a human to plug it in at the charging station
    """
    # create task with charging station location
    world_config = model.world_config if hasattr(model, 'world_config') else model.config['world']
    station_location = tuple(world_config['charging_station'])
    
    task = Task(
        task_id=model.task_counter,
        name="BatteryCharging",
        category="maintenance",
        location=station_location,
        assigner_id=robot.agent_id  # robot is requesting the service
    )
    
    # add to model's task queue
    model.task_queue.append(task)
    model.task_counter += 1
    
    # store reference to this task in the robot
    robot.recharge_task = task

def update_battery(robot):
    battery_config = robot.model.battery_config if hasattr(robot.model, 'battery_config') else robot.model.config['battery']
    world_config = robot.model.world_config if hasattr(robot.model, 'world_config') else robot.model.config['world']
    station = tuple(world_config['charging_station'])

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
