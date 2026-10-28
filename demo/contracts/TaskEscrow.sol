// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {AgentRegistry} from "./AgentRegistry.sol";
import {ServiceRegistry} from "./ServiceRegistry.sol";

/// @title TaskEscrow - task agreements, assignment, and the money they lock
/// @notice Lifecycle: Open -> Assigned -> Delivered -> Completed, Assigned -> Open (requeue),
///         Open -> Cancelled. The reward is locked at creation and released to the assignee
///         only when the assigner confirms the delivered work, or refunded on cancellation.
///         Assignment is decided off-chain by the operator (master node); this contract
///         only checks that the choice is valid.
contract TaskEscrow {
    enum Status { None, Open, Assigned, Delivered, Completed, Cancelled }

    struct Task {
        address assigner;
        address assignee;
        string service;
        uint256 reward;
        Status status;
        uint64 createdAt;
        uint64 assignedAt;
        uint64 closedAt;
    }

    IERC20 public immutable token;
    AgentRegistry public immutable agentRegistry;
    ServiceRegistry public immutable serviceRegistry;
    address public immutable operator;

    uint256 public taskCount;
    uint256 public totalLocked;
    mapping(uint256 => Task) private tasks;

    event TaskCreated(uint256 indexed taskId, address indexed assigner, string service, uint256 reward);
    event TaskAssigned(uint256 indexed taskId, address indexed assignee, address indexed assigner, string service);
    event TaskRequeued(uint256 indexed taskId, address indexed previousAssignee);
    event TaskDelivered(uint256 indexed taskId, address indexed assignee, address indexed assigner);
    event TaskCompleted(uint256 indexed taskId, address indexed assignee, address indexed assigner, uint256 reward);
    event TaskCancelled(uint256 indexed taskId, address indexed assigner, uint256 refunded);

    modifier onlyOperator() {
        require(msg.sender == operator, "only operator");
        _;
    }

    constructor(IERC20 token_, AgentRegistry agentRegistry_, ServiceRegistry serviceRegistry_, address operator_) {
        token = token_;
        agentRegistry = agentRegistry_;
        serviceRegistry = serviceRegistry_;
        operator = operator_;
    }

    /// @notice Post a task and lock its reward. The caller must have approved this contract.
    function createTask(string calldata service, uint256 reward) external returns (uint256 taskId) {
        require(agentRegistry.isRegistered(msg.sender), "not registered");
        require(reward > 0, "reward must be > 0");
        require(token.balanceOf(msg.sender) >= reward, "insufficient balance");
        require(token.allowance(msg.sender, address(this)) >= reward, "escrow not approved");

        taskId = ++taskCount;
        tasks[taskId] = Task({
            assigner: msg.sender,
            assignee: address(0),
            service: service,
            reward: reward,
            status: Status.Open,
            createdAt: uint64(block.timestamp),
            assignedAt: 0,
            closedAt: 0
        });
        totalLocked += reward;

        require(token.transferFrom(msg.sender, address(this), reward), "transfer failed");
        emit TaskCreated(taskId, msg.sender, service, reward);
    }

    /// @notice Operator assigns an open task to a registered provider of the service.
    function assignTask(uint256 taskId, address assignee) external onlyOperator {
        Task storage t = tasks[taskId];
        require(t.status == Status.Open, "task not open");
        require(assignee != t.assigner, "assignee is the assigner");
        require(agentRegistry.isRegistered(assignee), "assignee not registered");
        require(serviceRegistry.offers(assignee, t.service), "assignee does not offer service");

        t.assignee = assignee;
        t.status = Status.Assigned;
        t.assignedAt = uint64(block.timestamp);
        emit TaskAssigned(taskId, assignee, t.assigner, t.service);
    }

    /// @notice Operator puts an assigned task back in the queue; the reward stays locked.
    function requeueTask(uint256 taskId) external onlyOperator {
        Task storage t = tasks[taskId];
        require(t.status == Status.Assigned, "task not assigned");

        address previous = t.assignee;
        t.assignee = address(0);
        t.status = Status.Open;
        t.assignedAt = 0;
        emit TaskRequeued(taskId, previous);
    }

    /// @notice Assignee marks its work as done; the reward stays locked until the assigner confirms.
    function completeTask(uint256 taskId) external {
        Task storage t = tasks[taskId];
        require(t.status == Status.Assigned, "task not assigned");
        require(msg.sender == t.assignee, "not assignee");

        t.status = Status.Delivered;
        emit TaskDelivered(taskId, t.assignee, t.assigner);
    }

    /// @notice Assigner confirms the delivered work; the reward goes to the assignee.
    function confirmTask(uint256 taskId) external {
        Task storage t = tasks[taskId];
        require(t.status == Status.Delivered, "task not delivered");
        require(msg.sender == t.assigner, "not assigner");

        t.status = Status.Completed;
        t.closedAt = uint64(block.timestamp);
        totalLocked -= t.reward;

        require(token.transfer(t.assignee, t.reward), "transfer failed");
        emit TaskCompleted(taskId, t.assignee, t.assigner, t.reward);
    }

    /// @notice Assigner withdraws a task nobody has taken yet; full refund.
    function cancelTask(uint256 taskId) external {
        Task storage t = tasks[taskId];
        require(t.status == Status.Open, "task not open");
        require(msg.sender == t.assigner, "not assigner");

        t.status = Status.Cancelled;
        t.closedAt = uint64(block.timestamp);
        totalLocked -= t.reward;

        require(token.transfer(t.assigner, t.reward), "transfer failed");
        emit TaskCancelled(taskId, t.assigner, t.reward);
    }

    function getTask(uint256 taskId) external view returns (Task memory) {
        require(tasks[taskId].status != Status.None, "no such task");
        return tasks[taskId];
    }
}
