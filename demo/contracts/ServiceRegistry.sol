// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AgentRegistry} from "./AgentRegistry.sol";

interface IOrganizationServiceHook {
    function onServiceRegistered(uint256 serviceId) external;
}

/// @title ServiceRegistry - the "yellow pages": who offers which service, at what price
/// @notice Plays the ServiceManager role of RODEO's Organization.sol. Only registered agents
///         can publish offers. Each offer has an id (1..n), a category, a service type and a
///         price; the Organization contract reads them to match tasks and marks providers busy.
contract ServiceRegistry {
    struct Service {
        address provider;
        string service;      // the service type, e.g. "LabCleaning"
        string category;     // e.g. "cleaning"
        bytes32 serviceHash; // keccak(service), what the Organization matches on
        bytes32 categoryHash;
        uint256 price;       // what the provider charges (IEC base units)
        bool active;
    }

    AgentRegistry public immutable agentRegistry;
    address public immutable deployer;
    address public organization;

    Service[] private services;                                    // id = index + 1
    mapping(address => mapping(bytes32 => uint256)) private idOf;  // provider => keccak(service) => id
    mapping(bytes32 => address[]) private providers;               // keccak(service) => providers
    // an agent does one job at a time, so busy is per provider (Organization.sol: per service)
    mapping(address => bool) public busy;

    event ServiceRegistered(uint256 indexed serviceId, address indexed provider, string service,
                            string category, uint256 price);
    event ProviderBusy(address indexed provider, bool busy);

    modifier onlyOrganization() {
        require(msg.sender == organization, "only organization");
        _;
    }

    constructor(AgentRegistry agentRegistry_) {
        agentRegistry = agentRegistry_;
        deployer = msg.sender;
    }

    /// @notice One-time wiring to the Organization contract (it needs our address too).
    function setOrganization(address organization_) external {
        require(msg.sender == deployer, "only deployer");
        require(organization == address(0), "organization already set");
        organization = organization_;
    }

    /// @notice Publish an offer. The Organization immediately looks for a waiting task it fits.
    function registerService(string calldata service, string calldata category, uint256 price)
        external returns (uint256 serviceId)
    {
        require(agentRegistry.isRegistered(msg.sender), "not registered");
        require(organization != address(0), "organization not set");
        bytes32 key = keccak256(bytes(service));
        require(idOf[msg.sender][key] == 0, "service already registered");

        services.push(Service(msg.sender, service, category, key, keccak256(bytes(category)), price, true));
        serviceId = services.length;
        idOf[msg.sender][key] = serviceId;
        providers[key].push(msg.sender);
        emit ServiceRegistered(serviceId, msg.sender, service, category, price);

        IOrganizationServiceHook(organization).onServiceRegistered(serviceId);
    }

    function setBusy(address provider, bool isBusy) external onlyOrganization {
        busy[provider] = isBusy;
        emit ProviderBusy(provider, isBusy);
    }

    // ── views ──────────────────────────────────────────────────────────

    function getServiceCount() external view returns (uint256) {
        return services.length;
    }

    /// @notice What the Organization needs to match: same shape as Organization.sol's getServiceMeta.
    function getServiceMeta(uint256 serviceId) external view returns (
        uint256 id, bytes32 categoryHash, bytes32 serviceHash, uint256 price,
        address provider, bool active, bool isBusy
    ) {
        Service storage s = services[serviceId - 1];
        return (serviceId, s.categoryHash, s.serviceHash, s.price, s.provider, s.active, busy[s.provider]);
    }

    function getService(uint256 serviceId) external view returns (Service memory) {
        return services[serviceId - 1];
    }

    function offers(address provider, string calldata service) external view returns (bool) {
        return idOf[provider][keccak256(bytes(service))] != 0;
    }

    function priceOf(address provider, string calldata service) external view returns (uint256) {
        uint256 id = idOf[provider][keccak256(bytes(service))];
        require(id != 0, "no such offer");
        return services[id - 1].price;
    }

    function getProviders(string calldata service) external view returns (address[] memory) {
        return providers[keccak256(bytes(service))];
    }
}
