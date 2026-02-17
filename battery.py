# battery management logic

from tasks import Task

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
    # get config from model
    battery_config = robot.model.battery_config if hasattr(robot.model, 'battery_config') else robot.model.config['battery']
    world_config = robot.model.world_config if hasattr(robot.model, 'world_config') else robot.model.config['world']
    
    # check if robot is currently charging
    if robot.awaiting_recharge and robot.recharge_task is not None:
        # check if a human has accepted the task and is working on it
        if robot.recharge_task.status == "in_progress" and robot.recharge_task.assignee_id is not None:
            # human has accepted and is "plugging in" - start charging
            robot.battery += battery_config['recharge_rate']
            
            # cap battery at 100
            if robot.battery >= 100:
                robot.battery = 100
                robot.status = "idle"
                robot.awaiting_recharge = False
                robot.recharge_task = None
        else:
            # still waiting for human to accept task, battery continues draining
            robot.battery -= battery_config['drain_rate']
            if robot.battery < 0:
                robot.battery = 0
    else:
        # normal battery drain when not charging
        drain_rate = battery_config['drain_rate']
        robot.battery -= drain_rate

        if robot.battery < 0:
            robot.battery = 0
        
        # check if battery hits recharge trigger
        if robot.battery <= battery_config['recharge_trigger'] and not robot.awaiting_recharge:
            generate_recharge_task(robot.model, robot)
            robot.awaiting_recharge = True
            robot.status = "busy"
            robot.target_location = tuple(world_config['charging_station'])
