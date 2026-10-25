// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title IECToken - the market's currency
/// @notice The whole supply is minted to the master at deploy time, so the supply is
///         fixed from the start. The master then funds each agent with `transfer`.
contract IECToken is ERC20 {
    /// @param totalSupply_ total supply in base units (2 decimals: 100 = 1.00 IEC)
    /// @param master wallet that receives the whole supply
    constructor(uint256 totalSupply_, address master) ERC20("Robopreneur IEC", "IEC") {
        _mint(master, totalSupply_);
    }

    /// @dev 2 decimals so rewards like 140.37 IEC are exact
    function decimals() public pure override returns (uint8) {
        return 2;
    }
}
