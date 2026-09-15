#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "governance/test/stage02/STAGE02_INDEPENDENT_DENOMINATOR_RECOMPUTATION_R35.yaml"
FINDING = ROOT / "governance/test/stage02/FIND-20260915-026_STAGE02_DENOMINATOR_UNDERCOUNT.yaml"
SCANNER = ROOT / "governance/ci/run_current_stage2_actual_test.py"
MOTHER = ROOT / ".github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md"


def die(msg: str) -> None:
    raise SystemExit(f"BLOCK: {msg}")


def load(path: Path):
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj

r = load(OUT)
f = load(FINDING)
scanner = SCANNER.read_text(encoding="utf-8")
mother = MOTHER.read_text(encoding="utf-8")

if "'mutation_owner', 'failure_state', 'recovery', 'audit_event_uid', 'illegal_transition_tests'" not in scanner:
    die("CANONICAL_SCANNER_REQUIRED_TRANSITION_FIELDS_DRIFT")
if "<!-- SECTION_UID: WEB-GOV-01-S060 -->" not in mother or "Illegal Transition Tests" not in mother:
    die("S060_TRANSITION_LEDGER_REQUIREMENT_NOT_PROVEN")

pages = r.get("pages") or {}
if set(pages) != {"CORE-01", "ASSET-01"}:
    die(f"PAGE_DENOMINATOR_DRIFT:{sorted(pages)}")
raw_sum = sum(int((v or {}).get("raw_gap_total", -1)) for v in pages.values())
eff_sum = sum(int((v or {}).get("effective_gap_total", -1)) for v in pages.values())
if raw_sum != r.get("raw_gap_total"):
    die(f"RAW_ARITHMETIC_DRIFT:{raw_sum}:{r.get('raw_gap_total')}")
if eff_sum != r.get("effective_gap_total"):
    die(f"EFFECTIVE_ARITHMETIC_DRIFT:{eff_sum}:{r.get('effective_gap_total')}")
if r.get("effective_gap_total") != r.get("raw_gap_total") - r.get("validated_product_elimination_count") - r.get("validated_gap006_elimination_count"):
    die("ELIMINATION_ARITHMETIC_DRIFT")

rows = []
for page, rec in pages.items():
    for row in (rec or {}).get("transition_missing_field_rows") or []:
        rows.append((page, row.get("transition_uid"), row.get("missing_field")))
if len(rows) != r.get("transition_required_field_gap_total"):
    die("TRANSITION_ROW_DENOMINATOR_DRIFT")
field_counts = {}
for _, _, field in rows:
    field_counts[field] = field_counts.get(field, 0) + 1
if field_counts != (r.get("transition_missing_field_counts") or {}):
    die(f"TRANSITION_FIELD_COUNT_DRIFT:{field_counts}")
if "illegal_transition_tests" not in field_counts:
    die("ILLEGAL_TRANSITION_TEST_GAP_NOT_RECOMPUTED")
if r.get("transition_uid_denominator") != len({(p, t) for p, t, _ in rows}):
    die("TRANSITION_UID_DENOMINATOR_DRIFT")

mismatch = bool(r.get("denominator_mismatch_detected"))
if mismatch != (r.get("raw_denominator_delta_vs_r29") != 0 or r.get("effective_denominator_delta_vs_r29") != 0):
    die("MISMATCH_FLAG_DRIFT")
if mismatch and f.get("status") != "OPEN":
    die("FINDING_MUST_BE_OPEN_ON_MISMATCH")
if not mismatch and f.get("status") != "NOT_REPRODUCED":
    die("FINDING_STATUS_DRIFT")
if r.get("current_specification_mutated") is not False or r.get("immutable_stage1_source_mutated") is not False:
    die("SOURCE_OR_SPEC_MUTATION_FLAG_DRIFT")
if r.get("blocker_reduction_claimed") != 0 or r.get("stage_exit_allowed") is not False:
    die("PREMATURE_CLOSURE_CLAIM")
print(f"PASS: R35 independent raw={r['raw_gap_total']} effective={r['effective_gap_total']} transition_fields={r['transition_required_field_gap_total']} mismatch={mismatch}")
