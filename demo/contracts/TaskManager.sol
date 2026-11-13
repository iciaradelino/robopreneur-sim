// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {AgentRegistry} from "./AgentRegistry.sol";
import {ServiceRegistry} from "./ServiceRegistry.sol";

interface IOrganizationTaskHooks {
    function onTaskRegistered(uint256 taskId) external;
    function onTaskDelivered(uint256 taskId) external;
    function onTaskCancelled(uint256 taskId) external;
}

/// @title TaskManager - the on-chain task registry and the escrow of its rewards (named as in RODEO)
/// @notice The TaskManager of RODEO's Organization.sol. Every task is registered
///         here, so its whole history is on-chain: who posted it, for what, which provider
///         got it at what price, and when each step happened.
///         Lifecycle: Open -> Assigned -> Delivered -> Completed, Assigned -> Open (requeue),
///         Open -> Cancelled.
///         Registering a task immediately calls the Organization contract, which assigns it
///         to the cheapest idle matching provider in the same transaction (or queues it until
///         one frees up). Only the Organization can assign or requeue.
///         The reward is the poster's budget and is locked at creation. On confirmation the
///         provider is paid its price and the rest goes back to the poster.
contract TaskManager {
    enum Status { None, Open, Assigned, Delivered, Completed, Cancelled }

    struct Task {
        address assigner;     // who posted (and pays for) the task
        address assignee;     // the provider the Organization picked
        string service;       // service type, e.g. "LabCleaning"
        string category;      // e.g. "cleaning"
        uint256 reward;       // budget, locked at creation
        uint256 price;        // what the assignee is paid (<= reward), set on assignment
        Status status;
        uint64 createdAt;
        uint64 assignedAt;
        uint64 closedAt;
    }

    IERC20 public immutable token;
    AgentRegistry public immutable agentRegistry;
    ServiceRegistry public immutable serviceRegistry;
    address public immutable deployer;
    address public organization;

    uint256 public taskCount;
    uint256 public totalLocked;
    mapping(uint256 => Task) private tasks;

    event TaskCreated(uint256 indexed taskId, address indexed assigner, string service, string category, uint256 reward);
    event TaskAssigned(uint256 indexed taskId, address indexed assignee, address indexed assigner, string service, uint256 price);
    event TaskRequeued(uint256 indexed taskId, address indexed previousAssignee);
    event TaskDelivered(uint256 indexed taskId, address indexed assignee, address indexed assigner);
    event TaskCompleted(uint256 indexed taskId, address indexed assignee, address indexed assigner, uint256 paid, uint256 refunded);
    event TaskCancelled(uint256 indexed taskId, address indexed assigner, uint256 refunded);

    modifier onlyOrganization() {
        require(msg.sender == organization, "only organization");
        _;
    }

    constructor(IERC20 token_, AgentRegistry agentRegistry_, ServiceRegistry serviceRegistry_) {
        token = token_;
        agentRegistry = agentRegistry_;
        serviceRegistry = serviceRegistry_;
        deployer = msg.sender;
    }

    /// @notice One-time wiring to the Organization contract (it needs our address too).
    function setOrganization(address organization_) external {
        require(msg.sender == deployer, "only deployer");
        require(organization == address(0), "organization already set");
        organization = organization_;
    }

    /// @notice Register a task and lock its reward; assignment is triggered right away.
    ///         The caller must have approved this contract.
    function createTask(string calldata service, string calldata category, uint256 reward)
        external returns (uint256 taskId)
    {
        require(agentRegistry.isRegistered(msg.sender), "not registered");
        require(organization != address(0), "organization not set");
        require(bytes(service).length > 0, "empty service");
        require(reward > 0, "reward must be > 0");
        require(token.balanceOf(msg.sender) >= reward, "insufficient balance");
        require(token.allowance(msg.sender, address(this)) >= reward, "escrow not approved");

        taskId = ++taskCount;
        Task storage t = tasks[taskId];
        t.assigner = msg.sender;
        t.service = service;
        t.category = category;
        t.reward = reward;
        t.status = Status.Open;
        t.createdAt = uint64(block.timestamp);
        totalLocked += reward;

        require(token.transferFrom(msg.sender, address(this), reward), "transfer failed");
        emit TaskCreated(taskId, msg.sender, service, category, reward);

        // Organization.sol: "Called by TaskManager after registering a task"
        IOrganizationTaskHooks(organization).onTaskRegistered(taskId);
    }

    /// @notice Organization gives an open task to a provider of the service, at its price.
    function assignTask(uint256 taskId, address assignee, uint256 price) external onlyOrganization {
        Task storage t = tasks[taskId];
        require(t.status == Status.Open, "task not open");
        require(assignee != t.assigner, "assignee is the assigner");
        require(agentRegistry.isRegistered(assignee), "assignee not registered");
        require(serviceRegistry.offers(assignee, t.service), "assignee does not offer service");
        require(price <= t.reward, "price above reward");

        t.assignee = assignee;
        t.price = price;
        t.status = Status.Assigned;
        t.assignedAt = uint64(block.timestamp);
        emit TaskAssigned(taskId, assignee, t.assigner, t.service, price);
    }

    /// @notice Organization takes an assigned task back; it is open again, the reward stays locked.
    function requeueTask(uint256 taskId) external onlyOrganization {
        Task storage t = tasks[taskId];
        require(t.status == Status.Assigned, "task not assigned");

        address previous = t.assignee;
        t.assignee = address(0);
        t.price = 0;
        t.status = Status.Open;
        t.assignedAt = 0;
        emit TaskRequeued(taskId, previous);
    }

    /// @notice Assignee marks its work as done; it is free for its next task straight away,
    ///         the money stays locked until the assigner confirms.
    function completeTask(uint256 taskId) external {
        Task storage t = tasks[taskId];
        require(t.status == Status.Assigned, "task not assigned");
        require(msg.sender == t.assignee, "not assignee");

        t.status = Status.Delivered;
        emit TaskDelivered(taskId, t.assignee, t.assigner);

        // Organization.sol onTaskComplete: free the provider and give it the best waiting task
        IOrganizationTaskHooks(organization).onTaskDelivered(taskId);
    }

    /// @notice Assigner confirms the delivered work: the assignee gets its price, the rest is refunded.
    function confirmTask(uint256 taskId) external {
        Task storage t = tasks[taskId];
        require(t.status == Status.Delivered, "task not delivered");
        require(msg.sender == t.assigner, "not assigner");

        t.status = Status.Completed;
        t.closedAt = uint64(block.timestamp);
        totalLocked -= t.reward;
        uint256 refund = t.reward - t.price;

        require(token.transfer(t.assignee, t.price), "transfer failed");
        if (refund > 0) {
            require(token.transfer(t.assigner, refund), "transfer failed");
        }
        emit TaskCompleted(taskId, t.assignee, t.assigner, t.price, refund);
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
        IOrganizationTaskHooks(organization).onTaskCancelled(taskId);
    }

    // ── views ──────────────────────────────────────────────────────────

    function getTask(uint256 taskId) external view returns (Task memory) {
        require(tasks[taskId].status != Status.None, "no such task");
        return tasks[taskId];
    }

    /// @notice What the Organization needs to match (cf. Organization.sol's getTaskMeta).
    function getTaskMeta(uint256 taskId) external view returns (
        address assigner, bytes32 categoryHash, bytes32 serviceHash, uint256 reward, Status status
    ) {
        Task storage t = tasks[taskId];
        return (t.assigner, keccak256(bytes(t.category)), keccak256(bytes(t.service)), t.reward, t.status);
    }
}
