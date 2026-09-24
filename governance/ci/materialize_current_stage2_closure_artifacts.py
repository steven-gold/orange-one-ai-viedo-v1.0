#!/usr/bin/env python3
from __future__ import annotations

PACKAGED_ARTIFACT_CONTRACT = {
    "owner_output": "PAGE_CONSTRUCTION_SPEC_PACKAGE",
    "package_manifest_field": "included_artifacts",
    "artifacts": {
        "BUSINESS_ENTITY_INVENTORY": "BUSINESS_ENTITY_INVENTORY.yaml",
        "BUSINESS_ENTITY_OPERATION_MATRIX": "BUSINESS_ENTITY_OPERATION_MATRIX.yaml",
        "ENTITY_HIERARCHY_MATRIX": "ENTITY_HIERARCHY_MATRIX.yaml",
        "INTERACTION_TOPOLOGY_MATRIX": "INTERACTION_TOPOLOGY_SPEC.yaml",
        "FUNCTION_VISUAL_IMPACT_MATRIX": "FUNCTION_VISUAL_IMPACT_MATRIX.yaml",
    },
}


def main() -> None:
    raise SystemExit(
        "BLOCK: STAGE02_PACKAGE_MATERIALIZER_REQUIRES_CURRENT_OPERATION_BINDING_AND_PRODUCT_WORK_UNIT_CONTEXT"
    )


if __name__ == "__main__":
    main()
