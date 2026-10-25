// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AgentRegistry} from "./AgentRegistry.sol";

/// @title ServiceRegistry - the "yellow pages": who offers which service
/// @notice Only registered agents can publish offers. Skill is stored x1000
///         (0.95 -> 950) because Solidity has no decimals.
contract ServiceRegistry {
    struct Offer {
        string category;
        uint16 skill;
        bool active;
    }

    AgentRegistry public immutable agentRegistry;

    // provider => keccak(service name) => offer
    mapping(address => mapping(bytes32 => Offer)) private offersOf;
    // keccak(service name) => providers
    mapping(bytes32 => address[]) private providers;

    event ServiceRegistered(address indexed provider, string service, string category, uint16 skill);

    constructor(AgentRegistry agentRegistry_) {
        agentRegistry = agentRegistry_;
    }

    function registerService(string calldata service, string calldata category, uint16 skill) external {
        require(agentRegistry.isRegistered(msg.sender), "not registered");
        require(skill <= 1000, "skill must be 0-1000");
        bytes32 key = keccak256(bytes(service));
        require(!offersOf[msg.sender][key].active, "service already registered");

        offersOf[msg.sender][key] = Offer(category, skill, true);
        providers[key].push(msg.sender);
        emit ServiceRegistered(msg.sender, service, category, skill);
    }

    function offers(address provider, string calldata service) external view returns (bool) {
        return offersOf[provider][keccak256(bytes(service))].active;
    }

    function getOffer(address provider, string calldata service)
        external
        view
        returns (string memory category, uint16 skill)
    {
        Offer storage o = offersOf[provider][keccak256(bytes(service))];
        require(o.active, "no such offer");
        return (o.category, o.skill);
    }

    function getProviders(string calldata service) external view returns (address[] memory) {
        return providers[keccak256(bytes(service))];
    }
}
