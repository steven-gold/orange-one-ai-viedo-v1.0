# ACPOS R9 Residual Cleanup — 2026-09-11

Scope: repository construction-content cleanup only. Current Authority, runtime, migrations, formal Production evidence, and immutable historical evidence are not replaced by this record.

## Removed stale construction surface

The directory `.monkeycode/specs/2026-09-08-strict-construction-audit-monitor/` was removed from the Current working branch because its five files described a temporary pre-repair/freeze monitor surface and contained superseded deployment/runtime assumptions, including old release SHAs, the migration-15 era, pre-repair deployment blocking, and earlier runtime-binding gaps.

Removed files:
- `AUDIT-MATRIX.md`
- `FROZEN-DEPLOYED-AUDIT-SNAPSHOT.md`
- `PRE-REPAIR-CONSTRAINTS.md`
- `design.md`
- `requirements.md`

## Authority rule

`authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml` remains the only Current Authority loader and explicitly requires exact paths in `current_authority_set`. The removed `.monkeycode/specs` files were not members of that set.

## Preservation rule

This cleanup does not delete Current Authority files, migrations, Gate25 formal inventory/ledger, Production acceptance evidence, or recurring acceptance workflows. Historical facts required for present acceptance remain under the formal construction evidence chain and Git history.

## Validation required

The cleanup is not considered closed until the resulting `new` commit passes the full ACPOS Release Gate. If any active consumer is discovered by that validation, the failure must be repaired from the active Current contract rather than restoring the obsolete monitor surface.
