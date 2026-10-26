// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AgentRegistry} from "./AgentRegistry.sol";

/// @title ServiceRegistry - the "yellow pages": who offers which service
/// @notice Only registered agents can publish offers.
contract ServiceRegistry {
    struct Offer {
        string category;
        bool active;
    }

    AgentRegistry public immutable agentRegistry;

    // provider => keccak(service name) => offer
    mapping(address => mapping(bytes32 => Offer)) private offersOf;
    // keccak(service name) => providers
    mapping(bytes32 => address[]) private providers;

    event ServiceRegistered(address indexed provider, string service, string category);

    constructor(AgentRegistry agentRegistry_) {
        agentRegistry = agentRegistry_;
    }

    function registerService(string calldata service, string calldata category) external {
        require(agentRegistry.isRegistered(msg.sender), "not registered");
        bytes32 key = keccak256(bytes(service));
        require(!offersOf[msg.sender][key].active, "service already registered");

        offersOf[msg.sender][key] = Offer(category, true);
        providers[key].push(msg.sender);
        emit ServiceRegistered(msg.sender, service, category);
    }

    function offers(address provider, string calldata service) external view returns (bool) {
        return offersOf[provider][keccak256(bytes(service))].active;
    }

    function getProviders(string calldata service) external view returns (address[] memory) {
        return providers[keccak256(bytes(service))];
    }
}
