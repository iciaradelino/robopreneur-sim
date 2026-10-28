"""Compile the demo's Solidity contracts with py-solc-x."""

import solcx

from chain.config import DEMO_DIR

CONTRACT_NAMES = ["IECToken", "AgentRegistry", "ServiceRegistry", "TaskEscrow"]


def compile_contracts(solc_version, evm_version):
    """Compile every contract and return {name: {"abi": ..., "bytecode": ...}}."""
    if solc_version not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(solc_version)

    output = solcx.compile_files(
        [str(DEMO_DIR / "contracts" / f"{name}.sol") for name in CONTRACT_NAMES],
        output_values=["abi", "bin"],
        solc_version=solc_version,
        evm_version=evm_version,
        optimize=True,
        # relative remapping: solc mangles absolute Windows paths ("C:/..." -> "/...")
        import_remappings={"@openzeppelin/": "node_modules/@openzeppelin/"},
        base_path=str(DEMO_DIR),
    )
    # keys look like "<path>/TaskEscrow.sol:TaskEscrow"; keep only our 4 contracts
    return {key.rsplit(":", 1)[-1]: {"abi": a["abi"], "bytecode": a["bin"]}
            for key, a in output.items() if key.rsplit(":", 1)[-1] in CONTRACT_NAMES}
