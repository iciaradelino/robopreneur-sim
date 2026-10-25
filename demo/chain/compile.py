"""Compile the demo's Solidity contracts with py-solc-x.

Usage: python -m chain.compile   (from demo/)
Writes out/compiled.json: {contract name: {abi, bytecode}}.
"""

import json
from pathlib import Path

import solcx
import yaml

DEMO_DIR = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = DEMO_DIR / "contracts"
OUT_DIR = DEMO_DIR / "out"
CONTRACT_NAMES = ["IECToken", "AgentRegistry", "ServiceRegistry", "TaskEscrow"]


def load_config(path=DEMO_DIR / "demo_config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def compile_contracts(solc_version, evm_version):
    """Compile every contract and return {name: {"abi": ..., "bytecode": ...}}."""
    if solc_version not in [str(v) for v in solcx.get_installed_solc_versions()]:
        print(f"[compile] installing solc {solc_version} ...")
        solcx.install_solc(solc_version)

    sources = [str(CONTRACTS_DIR / f"{name}.sol") for name in CONTRACT_NAMES]
    output = solcx.compile_files(
        sources,
        output_values=["abi", "bin"],
        solc_version=solc_version,
        evm_version=evm_version,
        optimize=True,
        # relative remapping: solc mangles absolute Windows paths ("C:/..." -> "/...")
        import_remappings={"@openzeppelin/": "node_modules/@openzeppelin/"},
        base_path=str(DEMO_DIR),
    )

    compiled = {}
    for key, artifact in output.items():
        # keys look like "<path>/TaskEscrow.sol:TaskEscrow"; keep only our 4 contracts
        name = key.rsplit(":", 1)[-1]
        if name in CONTRACT_NAMES:
            compiled[name] = {"abi": artifact["abi"], "bytecode": artifact["bin"]}

    missing = set(CONTRACT_NAMES) - compiled.keys()
    if missing:
        raise RuntimeError(f"contracts missing from compiler output: {sorted(missing)}")
    return compiled


def main():
    chain_cfg = load_config()["chain"]
    compiled = compile_contracts(chain_cfg["solc_version"], chain_cfg["evm_version"])

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / "compiled.json"
    out_path.write_text(json.dumps(compiled, indent=2), encoding="utf-8")
    for name, artifact in compiled.items():
        print(f"[compile] {name:<16} {len(artifact['bytecode']) // 2:>6} bytes")
    print(f"[compile] wrote {out_path.relative_to(DEMO_DIR)}")


if __name__ == "__main__":
    main()
