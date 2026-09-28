# Blocker B - Evidence Generator Specification

Scope: produce the five product-cycle evidence files (plus coupled registry updates) that close the
`current_test_evidence_sync` and `evidence_state_closure` checks, so the successor-aware regression
suites `test_v2_1_8_*`, `test_v2_1_9_*`, `test_v2_1_12_*` and `test_high_pressure_hardening.py`
pass against the governance package on `rebuild-v2.1.1`.

The machine-readable contract is `evidence_schema.yaml` in this directory. This document is the
generator design. Every value is traced to a real product execution; the generator must never
invent a value.

## 1. Key finding (why B is more than "5 files")

The five evidence files alone do not close the checks. The consumers also require:

1. `HIGH_PRESSURE_HARDENING_RESULT.yaml` to be a registered member of
   `GOVERNANCE_ROOT_MANIFEST.yaml` (`current_artifacts` or `validators`).
   Source: `test_high_pressure_hardening.py:115-120`.
2. `REVIEW_PROGRESS_LEDGER.yaml` in the "machine closed / human pending" state with the current
   revision. Source: `validate_current_test_evidence.py:169-181`,
   `validate_evidence_state_closure.py:69-73`.
3. `GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml` and, under fresh revalidation, the review ledger to
   carry the current revision. Source: `validate_current_test_evidence.py:79-80`.
4. Registering `HIGH_PRESSURE_HARDENING_RESULT.yaml` changes the semantic baseline, which forces a
   `content_hash` recompute and re-anchoring of the single canonical literal.
   Source: `validate_reference_semantics.py:32-46,55`.

Treat B as an atomic transaction: evidence + registration + re-anchor + checksums.

## 2. Preconditions

- Governance package checked out at candidate revision `R`; `GOVERNANCE_ROOT_MANIFEST.governance_revision`
  is the authority for `R` (currently `v2.2.25-normative-execution-matrix`).
- Product execution on `0921acpos` completed, with the GitHub runs that back the closure evidence.
- The 17 mandatory suites executed through the standalone subprocess/JSON runner on the product side
  (`mandatory_regression_runner: STANDALONE_SUBPROCESS_JSON`). Generic pytest collection is forbidden.
- Blocker A (external trust root) and Blocker C (mother-spec anchors) are outside this generator; the
  generator must not fake them.

## 3. Inputs

| Input | Source | Used for |
|-------|--------|----------|
| Current revision `R` | `GOVERNANCE_ROOT_MANIFEST.governance_revision` | `candidate`, all revision fields |
| Current suite denominators | `SEMANTIC_AUTHORITY_BASELINE.mandatory_regression_assets` | exact `n/n PASS` strings |
| Predecessor suite snapshot | prior revision run record | `fresh_revalidation.predecessor_mandatory_regression_assets` |
| GitHub run facts | GitHub Actions API (`gh run view`) | `GITHUB_REPLAY_CLOSURE_RESULT`, replay fields |
| Real suite results | standalone runner JSON output | all `<result_key>` values |
| Real defect states | product defect tracking | `GOVERNANCE_DEFECT_LEDGER.defects` |

Authoritative GitHub run IDs already bound by the validator (`validate_evidence_state_closure.py:52-59`):

| key | run_id | expected result |
|-----|--------|-----------------|
| `v218_successor_linkage_final` | 34733833659 | `SUCCESS_6_OF_6` |
| `pre_page_replay` | 34734265713 | `SUCCESS_5_OF_5` |
| `page_blueprint_replay_after_hash_correction` | 34734528373 | `SUCCESS_6_OF_6` |
| `page_replay_content_audit_closure` | 34734730080 | `SUCCESS_7_OF_7` |

The generator reads `head_sha` from each run; it must not hardcode a sha.

## 4. Decision: fresh vs non-fresh

- If the predecessor evidence was produced at a revision older than `R`, set
  `fresh_revalidation.required: true`. `HIGH_PRESSURE`/`REFERENCE_SEMANTIC` stay at the predecessor
  revision; review ledger and blueprint move to `R`; `predecessor_mandatory_regression_assets` is the
  older snapshot and must differ from current.
- Otherwise `required: false` and all revision fields start with the candidate prefix.
- Choose exactly one; the two branches enforce different constraints
  (`validate_current_test_evidence.py:71-83`).

## 5. Generation algorithm

1. Resolve `R` and current denominators. Build the exact-string map:
   `key -> f"{expected_total}/{expected_passed} PASS"`, plus `mandatory_regression_matrix`.
2. If fresh: freeze `predecessor_mandatory_regression_assets` and
   `predecessor_evidence_revisions = {high_pressure, reference_semantic, machine_review_target_revision}`.
   Assert the snapshot differs from current (changed/added/removed non-empty).
3. Capture GitHub run facts and assert run_id/result/head_sha against the table above.
4. Run/collect the 17 suite results. Assert `passed == total`; if any suite is short, emit the real
   value and fail the transaction (never upgrade to PASS).
5. Write `GOVERNANCE_CANDIDATE_STATE.yaml`:
   `candidate = R`, `formal_test_started = false`, `completion_claim = PREFORMAL_V...` (no
   `FORMAL_FREEZE`/`PRODUCTION_RELEASE`), `fresh_revalidation`, `preformal_execution` (all exact
   strings + wrapper truth `BLOCKED_TOOL_TIMEOUT` / `NOT_COMPLETED_TOOL_TIMEOUT`).
6. Write `HIGH_PRESSURE_HARDENING_RESULT.yaml` and `REFERENCE_SEMANTIC_REPAIR_RESULT.yaml` from the
   same exact-string map. Note `REFERENCE_SEMANTIC_REPAIR_RESULT.results.fuzz_total` uses key
   `fuzz_total`, while the candidate and high-pressure files use `reference_semantic_fuzz`.
7. Write `GOVERNANCE_DEFECT_LEDGER.yaml` and `GITHUB_REPLAY_CLOSURE_RESULT.yaml` with the closure
   rules in `evidence_schema.yaml`.
8. Coupled registries: register `HIGH_PRESSURE_HARDENING_RESULT.yaml` in the root manifest, refresh
   the manifest, add the path to `SEMANTIC_AUTHORITY_BASELINE.required_root_manifest_paths`, recompute
   `content_hash`, update the canonical literal in `validate_reference_semantics.py`, update the
   `SPECIFICATION_MANIFEST.yaml` mirror, set the review ledger to machine-closed/human-pending at `R`,
   and bump the blueprint revision to `R`.
9. Regenerate `CHECKSUMS.sha256` over the final tree.
10. Validate, then commit.

## 6. Validation loop (gate the transaction)

Run in order; all must pass before commit:

1. `validate_current_test_evidence.validate(pkg)` -> `PASS`
2. `validate_evidence_state_closure.validate(pkg)` -> `PASS`
3. `validate_reference_semantics.validate(pkg)` -> `PASS` (baseline re-anchor correct)
4. Standalone suites: `test_v2_1_8_*`, `test_v2_1_9_*`, `test_v2_1_12_*`, `test_high_pressure_hardening.py`
   -> `expected_total/expected_passed` from baseline.
5. `validate_governance.preformal(pkg)` -> residual failures limited to Blocker A and Blocker C only.

If steps 1-4 pass but step 5 still reports `external_trust_root` and `section_registry` /
`execution_governance_load`, that is expected: B is closed while A and C remain external.

## 7. CLI contract (generator, to be implemented on the product side)

```
generate_evidence_cycle.py \
  --pkg <path-to-governance-package> \
  --product-repo <path-to-0921acpos> \
  --candidate-revision <vX.Y.Z...> \
  --fresh / --no-fresh \
  --suite-results <runner-json> \
  --github-runs <gh-run-json-dir> \
  --defect-ledger <yaml> \
  --predecessor-snapshot <yaml> \
  [--dry-run] [--out <dir>]
```

- `--dry-run` prints the diff it would write and performs the validation loop without mutating the tree.
- Exit `0` only if the full validation loop passes; otherwise print the failing check ids and exit `1`.
- The generator refuses to run if any suite result is missing or short, if a GitHub run fact is
  unverifiable, or if it would have to fabricate a defect status.

## 8. Fail-closed rules

- No value without provenance: every evidence field maps to a run, a suite output, or a registry.
- Real result below denominator => write the real value and fail; never round up.
- Historical predecessor evidence must never be reused to close the current successor.
- Human formal review stays `PENDING`; the generator must not auto-approve it.
- The generator must not synthesize Blocker A trust-root data or Blocker C section anchors.

## 9. Current status

- Schema: this directory (`evidence_schema.yaml`).
- Generator: specification only; it must run against real product data, so it cannot be executed in
  the governance-only worktree.
- `validate_governance.preformal` remains `13/20` until B values are supplied and A/C land.
