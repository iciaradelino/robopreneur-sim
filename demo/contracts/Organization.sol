// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ServiceRegistry} from "./ServiceRegistry.sol";
import {TaskManager} from "./TaskManager.sol";

/// @title Organization - on-chain task assignment
/// @notice Adapted from RODEO's Organization.sol
///         (IERoboticsAILab/RODEO, blockchain-network/smart-contracts/contracts/Organization.sol).
///         TaskManager and ServiceRegistry play its TaskManager and ServiceManager.
///         Nobody picks assignees by hand any more; the contract does, at three moments:
///         - a task is registered     -> assignTask: the cheapest idle provider whose offer
///                                       matches its category and service with price <= reward
///         - a provider becomes free  -> tryAssignTaskForProvider: the waiting task with the
///           (delivers, is unassigned,   highest reward it can do (oldest first on a tie)
///           or lists a new service)
///         A task nobody can take yet waits in an on-chain queue (TaskQueued).
///         Differences from Organization.sol: busy is per provider (an agent does one job at a
///         time), a poster never gets its own task, and the queue only holds waiting tasks
///         instead of scanning every task ever registered.
contract Organization is Ownable {
    TaskManager public taskManager;
    ServiceRegistry public serviceRegistry;

    mapping(uint256 => address) public taskToProvider;  // tasks in progress
    uint256[] private waiting;                          // open tasks nobody could take yet
    mapping(uint256 => uint256) private waitingSlot;    // taskId => index in `waiting` + 1

    event TaskQueued(uint256 indexed taskId, address indexed assigner, string service, uint256 reward);
    event TaskMatched(uint256 indexed taskId, uint256 indexed serviceId, address indexed provider, uint256 price);

    constructor() Ownable(msg.sender) {}

    function setTaskManager(address taskManager_) external onlyOwner {
        taskManager = TaskManager(taskManager_);
    }

    function setServiceRegistry(address serviceRegistry_) external onlyOwner {
        serviceRegistry = ServiceRegistry(serviceRegistry_);
    }

    // ── hooks (Organization.sol: onTaskRegistered / onServiceRegistered / onTaskComplete) ──

    /// @notice Called by TaskManager right after a task is registered: assign it now or queue it.
    function onTaskRegistered(uint256 taskId) external {
        require(msg.sender == address(taskManager), "Unauthorized caller");
        if (!assignTask(taskId, address(0))) {
            enqueue(taskId);
        }
    }

    /// @notice Called by ServiceRegistry when a provider lists a new service.
    function onServiceRegistered(uint256 serviceId) external {
        require(msg.sender == address(serviceRegistry), "Not authorized");
        (, , , , address provider, , ) = serviceRegistry.getServiceMeta(serviceId);
        tryAssignTaskForProvider(provider);
    }

    /// @notice Called by TaskManager when the assignee delivers: it is free for the next task.
    function onTaskDelivered(uint256 taskId) external {
        require(msg.sender == address(taskManager), "Unauthorized caller");
        address provider = taskToProvider[taskId];
        delete taskToProvider[taskId];
        serviceRegistry.setBusy(provider, false);
        tryAssignTaskForProvider(provider);
    }

    /// @notice Called by TaskManager when an open task is cancelled: drop it from the queue.
    function onTaskCancelled(uint256 taskId) external {
        require(msg.sender == address(taskManager), "Unauthorized caller");
        dequeue(taskId);
    }

    // ── owner actions ──────────────────────────────────────────────────

    /// @notice Take a task back from its provider: it goes to another provider (or waits),
    ///         and the freed provider picks up the best waiting task it can do.
    function unassignTask(uint256 taskId) external onlyOwner {
        address provider = taskToProvider[taskId];
        require(provider != address(0), "Task not assigned");
        delete taskToProvider[taskId];
        taskManager.requeueTask(taskId);
        serviceRegistry.setBusy(provider, false);

        bool reassigned = assignTask(taskId, provider);  // never straight back to the same provider
        tryAssignTaskForProvider(provider);
        if (!reassigned) {
            enqueue(taskId);  // after the freed provider looked, so it does not take it back
        }
    }

    // ── matching ───────────────────────────────────────────────────────

    /// @dev Cheapest idle provider for the task; false if there is none.
    function assignTask(uint256 taskId, address exclude) internal returns (bool) {
        (address assigner, bytes32 taskCategory, bytes32 taskService, uint256 reward, TaskManager.Status status)
            = taskManager.getTaskMeta(taskId);
        if (status != TaskManager.Status.Open) return false;

        uint256 count = serviceRegistry.getServiceCount();
        address bestProvider;
        uint256 bestServiceId;
        uint256 lowestPrice = type(uint256).max;

        for (uint256 serviceId = 1; serviceId <= count; serviceId++) {
            (bool idle, address provider, uint256 price) = idleOffer(serviceId, taskCategory, taskService);
            if (!idle || provider == assigner || provider == exclude) continue;
            if (price <= reward && price < lowestPrice) {
                lowestPrice = price;
                bestProvider = provider;
                bestServiceId = serviceId;
            }
        }
        if (bestProvider == address(0)) return false;

        assign(taskId, bestServiceId, bestProvider, lowestPrice);
        return true;
    }

    /// @dev The waiting task with the highest reward the (now idle) provider can do.
    function tryAssignTaskForProvider(address provider) internal {
        if (serviceRegistry.busy(provider)) return;

        uint256 bestTaskId;
        uint256 bestServiceId;
        uint256 bestPrice;
        uint256 highestReward;

        for (uint256 i = 0; i < waiting.length; i++) {
            uint256 taskId = waiting[i];
            (address assigner, bytes32 tCat, bytes32 tType, uint256 reward, ) = taskManager.getTaskMeta(taskId);
            if (assigner == provider) continue;
            // higher reward wins; on a tie the older task (rewards are > 0, so the first match always counts)
            if (reward < highestReward || (reward == highestReward && taskId > bestTaskId)) continue;

            (uint256 serviceId, uint256 price) = findOffer(provider, tCat, tType);
            if (serviceId != 0 && price <= reward) {
                highestReward = reward;
                bestTaskId = taskId;
                bestServiceId = serviceId;
                bestPrice = price;
            }
        }
        if (bestTaskId == 0) return;

        dequeue(bestTaskId);
        assign(bestTaskId, bestServiceId, provider, bestPrice);
    }

    /// @dev Is service `serviceId` active, of this category and type, and its provider idle?
    function idleOffer(uint256 serviceId, bytes32 category, bytes32 service)
        internal view returns (bool idle, address provider, uint256 price)
    {
        (, bytes32 sCat, bytes32 sType, uint256 p, address sProvider, bool active, bool busy)
            = serviceRegistry.getServiceMeta(serviceId);
        return (active && !busy && sCat == category && sType == service, sProvider, p);
    }

    function findOffer(address provider, bytes32 category, bytes32 service)
        internal view returns (uint256 serviceId, uint256 price)
    {
        uint256 count = serviceRegistry.getServiceCount();
        for (uint256 i = 1; i <= count; i++) {
            (, bytes32 sCat, bytes32 sType, uint256 p, address sProvider, bool active, ) = serviceRegistry.getServiceMeta(i);
            if (sProvider == provider && active && sCat == category && sType == service) {
                return (i, p);
            }
        }
        return (0, 0);
    }

    function assign(uint256 taskId, uint256 serviceId, address provider, uint256 price) internal {
        taskToProvider[taskId] = provider;
        serviceRegistry.setBusy(provider, true);
        taskManager.assignTask(taskId, provider, price);
        emit TaskMatched(taskId, serviceId, provider, price);
    }

    // ── waiting queue ──────────────────────────────────────────────────

    function enqueue(uint256 taskId) internal {
        waiting.push(taskId);
        waitingSlot[taskId] = waiting.length;
        (address assigner, , , uint256 reward, ) = taskManager.getTaskMeta(taskId);
        emit TaskQueued(taskId, assigner, taskManager.getTask(taskId).service, reward);
    }

    function dequeue(uint256 taskId) internal {
        uint256 slot = waitingSlot[taskId];
        if (slot == 0) return;
        uint256 last = waiting[waiting.length - 1];
        waiting[slot - 1] = last;
        waitingSlot[last] = slot;
        waiting.pop();
        delete waitingSlot[taskId];
    }

    function getWaitingTasks() external view returns (uint256[] memory) {
        return waiting;
    }
}
