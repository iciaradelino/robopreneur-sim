// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AgentRegistry - the member list of the marketplace
/// @notice Each agent registers itself from its own wallet. Other contracts check
///         `isRegistered` before letting an address take part.
contract AgentRegistry {
    enum Kind { Human, Robot }

    struct Agent {
        string agentId;
        Kind kind;
        bool registered;
    }

    mapping(address => Agent) private agents;
    address[] private members;

    event AgentRegistered(address indexed agent, string agentId, Kind kind);

    function registerAgent(string calldata agentId, Kind kind) external {
        require(!agents[msg.sender].registered, "already registered");
        require(bytes(agentId).length > 0, "empty agent id");

        agents[msg.sender] = Agent(agentId, kind, true);
        members.push(msg.sender);
        emit AgentRegistered(msg.sender, agentId, kind);
    }

    function isRegistered(address agent) external view returns (bool) {
        return agents[agent].registered;
    }

    function getAgent(address agent) external view returns (string memory agentId, Kind kind) {
        require(agents[agent].registered, "not registered");
        Agent storage a = agents[agent];
        return (a.agentId, a.kind);
    }

    function getMembers() external view returns (address[] memory) {
        return members;
    }
}
