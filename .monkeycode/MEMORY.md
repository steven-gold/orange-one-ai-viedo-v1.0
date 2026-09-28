# User Instruction Memory

This file records user instructions, preferences, and teachings for reference in future interactions.

## Format

### User Instruction Entry
User instruction entries should follow this format:

[User Instruction Summary]
- Date: [YYYY-MM-DD]
- Context: [Mentioned scenario or time]
- Instructions:
  - [Content of user teaching or instruction, described line by line]

### Project Knowledge Entry
Entries discovered by the Agent during task execution should follow this format:

[Project Knowledge Summary]
- Date: [YYYY-MM-DD]
- Context: Discovered by Agent while performing [specific task description]
- Category: [Operations & Deployment|Build Methods|Testing Methods|Troubleshooting & Debugging|Workflow & Collaboration|Environment Configuration]
- Instructions:
  - [Specific knowledge points, described line by line]

## Deduplication Strategy
- Before adding a new entry, check for similar or identical instructions.
- If a duplicate is found, skip the new entry or merge it with the existing one.
- When merging, update the context or date information.
- This helps avoid redundant entries and keeps the memory file tidy.

## Entries

[Branch Authority And Operating Standard]
- Date: 2026-09-25
- Context: User directed website work on 0921acpos and required binding of rebuild-v2.1.1 as immutable operating standard
- Instructions:
  - `rebuild-v2.1.1` is the immutable governance ruleset. Read-only. Do not execute, add, modify, or delete anything on that branch unless the user explicitly permits it.
  - Bind the four mother-spec norms, four execution-domain rules, and four audit authorities from `rebuild-v2.1.1` as the basic operating standard for all work.
  - `0921acpos` is the product execution workline and the website basic-data source.
  - Four norms (WEB-GOV-01 to WEB-GOV-04): `01_BLUEPRINT_DESIGN_GOVERNANCE.md`, `02_IMPLEMENTATION_DELIVERY_STANDARD.md`, `03_EXECUTION_CONTROL_STANDARD.md`, `04_AUDIT_PROGRESS_STANDARD.md` under `.github/governance-source/active/source/12_DOCS/mother-spec/` on `rebuild-v2.1.1`.
  - Four rules (execution domains): BASIC_DESIGN, WORD_YAML, STAGE, AUDIT under `governance/execution-domains/` on `rebuild-v2.1.1`.
  - Four audit authorities: `AUDIT_CATALOG.yaml`, `GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml`, `AUDIT_PROFILE.yaml`, `AUDIT/DOMAIN.yaml` plus `AUDIT/STEPS.yaml` on `rebuild-v2.1.1`.
  - Read those artifacts from `origin/rebuild-v2.1.1` with `git show`. Do not checkout or write that branch.
  - Formal implementation of the website remains gated by WEB-GOV-02 Design Freeze. Current legal workline is STAGE-03 visual reverify on `0921acpos`.

[Governance Validation Blocker Model]
- Date: 2026-09-25
- Context: Agent debugging `validate_governance.preformal` (was 13/20) on `rebuild-v2.1.1`
- Category: Troubleshooting & Debugging
- Instructions:
  - Residual preformal failures decompose into three independent blockers; all three were closed on 2026-09-25 and `validate_governance.preformal` now reports 20/20.
  - Blocker A: `external_trust_root`. The trust root is an external JSON with `{schema_version:1, trust_model:EXTERNAL_IMMUTABLE_PACKAGE_HASH_SET, semantic_authority_content_hash, package_files:[{path,sha256}]}` covering every file of the governed source root (excluding `__pycache__/*.pyc`/build dirs). Keep it OUT of the repo and point `WEB_GOVERNANCE_TRUST_ROOT` at it. Regenerate it after any package byte change; sha comparison is exact.
  - Blocker B: closed by rebuilding the 5 product-cycle evidence files under `11_EVIDENCE/audit/` per the spec in 当前工作区 内的 `/.monkeycode/specs/evidence-cycle-b/`, registering `HIGH_PRESSURE_HARDENING_RESULT.yaml` in the root manifest, and re-anchoring the semantic baseline `content_hash` (single canonical literal in `validate_reference_semantics.py`).
  - Blocker C: closed by adding registry entries for the lettered sections (`WEB-GOV-01-S083A`, `WEB-GOV-03-S062A`, `WEB-GOV-04-S004A`) in `SECTION_NUMBER_REGISTRY.yaml` and fixing the misplaced `<!-- SECTION_UID -->` anchors so each anchor is immediately above its registered heading. Only anchor comments were touched; normative prose was not changed.
  - After any governance-source byte change run `compile_governance_baseline.py`, then `refresh_governance_root_manifest.py`, then regenerate `CHECKSUMS.sha256`, and finally regenerate the external trust root. Keep `PYTHONDONTWRITEBYTECODE=1`; stale `__pycache__` fails `parser_hygiene`.

[Per-Unit Stage Folder Requirement]
- Date: 2026-09-25
- Context: User reviewed STAGE-04 on GitHub and reported that the dashboard page had no independent folder
- Instructions:
  - Every independent governed page or system-logic unit must own its own work-unit folder under each stage directory (for example `STAGE_EXECUTION/STAGE-04/WU-STAGE04-WB01-DASHBOARD-001/`) together with the full preflight manifest set.
  - Listing a unit only in the stage resume `eligible_units`/`remaining_stage04_units` is insufficient; verify the WU folder physically exists at the corresponding location.
  - When a unit appears in the resume but its folder is missing, materialize the matching work-unit scaffold in the correct stage/unit path before declaring the stage ready.

[Governance Sync Requirement]
- Date: 2026-09-26
- Context: User required the local `rebuild-v2.1.1` spec to always match GitHub and to be synced down before re-verifying stage completion
- Instructions:
  - Before any stage work, run `git fetch origin rebuild-v2.1.1` and fast-forward the local governance worktree `/tmp/opencode/rebuild-v2.1.1` to `origin/rebuild-v2.1.1`; the local branch and GitHub must be identical.
  - Syncing (fast-forward only) is permitted even though the branch is otherwise read-only for content changes; do not author or edit governance content unless the user explicitly permits it.
  - Product CI now resolves Current governance dynamically (checkout `ref: rebuild-v2.1.1`) and binds product `ref: ${{ github.sha }}`; product artifacts must record the governance UID/HEAD resolved at run time instead of a hardcoded governance SHA.
  - Layout note: the engine's `ROOT` is where `governance/` lives, so stage admission checks must run from a product root that already has `governance/` and `.github/governance-source/` laid out (as CI does), not from the governance worktree.
  - Re-verify each stage against the synced governance before declaring it ready.

[Stage CI Run And Dispatch Pitfalls]
- Date: 2026-09-26
- Context: Agent re-sealing STAGE-02/03 on 0921acpos and diagnosing silently-failing stage workflows
- Category: Troubleshooting & Debugging
- Instructions:
  - GitHub Actions rejects an inline flow mapping that embeds an expression, e.g. `with: {ref: ${{ github.sha }}, fetch-depth: 0}`. The file fails YAML parse, GitHub registers the run under the file path with no jobs, and the workflow silently never executes. Always use block style for `with:`.
  - A workflow triggered by a push made with the default `GITHUB_TOKEN` does NOT trigger further workflows. After a CI materialize workflow commits and pushes sealed data, dispatch the validation workflow explicitly.
  - `workflow_dispatch` by file name fails with HTTP 422 (`Workflow does not have 'workflow_dispatch' trigger`) when GitHub's registry has not (re)parsed the current file. Dispatching by the numeric workflow id has the same behavior. Re-registration only happens when the workflow file itself changes in a push to the branch. Use the numeric id from a prior run (`workflow_id` field of the runs API) as a fallback.
  - Local pre-check: run `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <workflow.yml>` on every workflow before pushing; the current governance/engine tooling does not lint workflow YAML.
  - Inspect failed runs via `GET /repos/{owner}/{repo}/actions/runs/{id}/jobs`; an empty `jobs` array with the run name shown as the file path means the workflow YAML did not parse.
  - Terminal receipts are anchored to the materialize run's `github.sha` (the parent of the seal commit); a separate validation run lands on a later HEAD, so do NOT re-check `receipt.head_sha == current HEAD`. Validate only structural fields, `conclusion == success`, and `stage_uid`, mirroring the STAGE-02 validation contract.
  - In a workflow `run: |` block the YAML block indentation is carried into a heredoc body, which breaks Python with `IndentationError: unexpected indent`. Prefer a `python3 -c "..."` one-liner over an indented `<<'PY'` heredoc.

[V2.2.32 Stage Conformance Reconciler]
- Date: 2026-09-26
- Context: Agent converging STAGE-01..04 to v2.2.32 cross-stage handoff contract on 0921acpos
- Category: Workflow & Collaboration
- Instructions:
  - `.github/scripts/v232_conformance.py` rebuilds each producing stage's canonical `CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml`, resolves successor-execution bindings, re-mints normalized evidence, and converges `EXECUTION_STATE`/`WORK_UNIT`/resume. Args: `--root --stage --head --run --gov --gver`.
  - It is wired into the four `product-stage0X-materialize.yml` workflows as a step after the materialize/seal step and before validation, so terminal receipts carry the real `github.run_id`/`github.sha`.
  - `resolve_binding()` resolves STAGE-02 `VISUAL_AUTHORITY_TARGET`, STAGE-03 `FORMAL_DESIGN_APPROVAL_AUTHORITY`, and the 18 STAGE-04→05 classes. The 18 classes come from `STAGE_EXECUTION/SHARED_AUTHORITY/IMPLEMENTATION_EXECUTION_TARGET_AUTHORITY.yaml`, a governed machine projection of the current implementation authority on `origin/main` (package.json/next.config.ts/tsconfig.json/vercel.json/authority/ + database/migrations). Never invent a stack; unresolved classes must stay UNRESOLVED and keep the stage BLOCKED.
  - Stage guard fields are normalized on closure (`stageN_guard_result: PASS`, stale `resume_after_reentry` removed) so a CLOSED `EXECUTION_STATE` is internally consistent.
  - Sandbox-test changes before touching the product tree: copy `governance/` + `.github/governance-source/` from `/tmp/opencode/v232` (the rebuilt-v2.1.1 layout) plus the product `STAGE_EXECUTION/`; the engine's `ROOT` is where `governance/` lives. `--validate-terminal-receipt` calls `git rev-parse HEAD`, so the sandbox needs a `.git` with a ref matching `--head`.

[V2.2.33 Product Admission Gate]
- Date: 2026-09-27
- Context: Agent starting STAGE-05 under latest `rebuild-v2.1.1` (1465307e, v2.2.33) found `--admission-check` now fails before any work
- Category: Workflow & Collaboration
- Instructions:
  - Governance added `WEB-EXT-ADMISSION-01` (`PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION_REGISTRY.yaml` + `12_DOCS/external-admission/...`). Every product stage admission (`active_product`) now first runs `validate_product_governance_selection`.
  - Before ANY effectful product stage operation the product workline must materialize `STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_SELECTED_GOVERNANCE_RELEASE.yaml` (`artifact_type: PRODUCT_SELECTED_GOVERNANCE_RELEASE`, `status: SELECTED_VERIFIED_RELEASE`) plus a per-WU `GOVERNANCE_LOAD_RECEIPT.yaml`. CI must checkout governance at the exact selected released commit and export `ACPOS_GOVERNANCE_SOURCE_ROOT`; a moving branch ref is FORBIDDEN.
  - The selected registry must be `status: CURRENT_RELEASED`, `branch_role_contract[branch]=='IMMUTABLE_GOVERNANCE_RULESET'`, `governance_identity.status=='RELEASED'`, `identity_state=='IMMUTABLE_RELEASED'`, `released_immutable_identity==true`, and a `GOVERNANCE_RELEASE_RECEIPT` (path `governance/release/RELEASE_RECEIPT.yaml`) must exist. As of v2.2.33 the registry is `CANDIDATE_NOT_PROMOTED` with `released_immutable_identity:false` and no release receipt, so formal product execution is BLOCKED with `CANDIDATE_GOVERNANCE_NO_PRODUCT_EXECUTION` (credit 0). Promotion is a separate authorized transaction (`governance/ci/governance_promotion_transaction.py`, issue #54) needing independent external auditor evidence.
  - An old-UID product scope/matrix/evidence vs the current gov UID (STAGE-04 was `GOV-REV-20260925-...`; now `GOV-REV-20260927-GOVERNANCE-IDENTITY-NEGATIVE-TRACE-AUDITOR-INDEPENDENCE-HARDENING`) requires a `GOVERNANCE_REVISION_TRANSITION_RECEIPT` (`STAGE_EXECUTION/SHARED_AUTHORITY/GOVERNANCE_REVISION_TRANSITION_RECEIPT.yaml`, status `REVERIFY_REQUIRED`, authorized by issue #59 `STAGE04_TO_STAGE05_REENTRY`); otherwise `GOVERNANCE_REVISION_TRANSITION_REQUIRED`.
  - STAGE-05 `APPLICATION_ROOT` (kind `CURRENT_REPOSITORY_PATH`) now additionally requires an `APPLICATION_BASELINE_SNAPSHOT` ref on the receipt. Because `0921acpos` has no application baseline, the disposition is `APPLICATION_BASELINE_ADMISSION_REQUIRED`: a governed `APPLICATION_BASELINE_ADMISSION_MANIFEST` + compare-and-swap materialization (from `origin/new`, which is PROVENANCE_ONLY, never a target) + `APPLICATION_BASELINE_MATERIALIZATION_RECEIPT` (`AUTHORIZED_MIGRATION`) must land on `0921acpos` before STAGE-05 may run. Issue #59 authorizes this transaction but it is separate from (and does not grant) stage completion credit.
  - Empirical check: `ACPOS_PRODUCT_ROOT=/workspace ACPOS_ACTIVE_WORK_UNIT=<WU>/WORK_UNIT.yaml ACPOS_CURRENT_SCOPE=<WU>/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml ACPOS_GOVERNANCE_SOURCE_ROOT=<gov checkout> python governance/ci/stage_execution_engine.py --admission-check --stage STAGE-0X` blocks first at `PRODUCT_SELECTED_GOVERNANCE_RELEASE_MISSING`.

[V2.2.33 Engine Admission-Gate Removal (4eb7163f)]
- Date: 2026-09-28
- Context: Agent auditing STAGE-01..04 against the latest `rebuild-v2.1.1` and re-running the engine
- Category: Environment Configuration
- Instructions:
  - At governance head `4eb7163f` the common engine no longer enforces the product-selection/release/baseline gates: `validate_product_governance_selection`, the `admission()` external-registry call, and `_validate_application_baseline_snapshot` were removed. External admission now lives only in the opt-in `external_execution_admission_registry`/`external_execution_admission_standard` registry keys and is not wired into `stage_execution_engine.py`.
  - Engine env vars were renamed to `STAGE_EXECUTION_ROOT`, `STAGE_ACTIVE_WORK_UNIT`, `STAGE_CURRENT_SCOPE`; the `--product-root` executor argument name and the `product_stage_execution_allowed` / `resume_control.product_execution_allowed` fields come from `governance/environment/EXECUTION_WORKLINE_BINDING.yaml`, not the registry.
  - New hard requirements: every `operation_bindings` entry needs `applicability` (`REQUIRED` | `AUTHORIZED_NOT_APPLICABLE`), `result_owner`, `operation_receipt_ref`; NA needs `authority_evidence_ref` and no executor; the executor may not be the engine itself (`COMMON_ENGINE_RECURSIVE_EXECUTOR_FORBIDDEN`).
  - `validate_normative_execution_matrix` requires every selected-profile `required_normative_section_uids` and every `outputs`+`required_evidence` type to be represented, `governance_uid` to equal the current UID, and the `coverage` block to match computed values exactly.
  - STAGE-05 profile at 4eb7163f: `scope_mode: SINGLE_GOVERNED_UNIT_VERTICAL`, `exit_gate: GOVERNED_UNIT_IMPLEMENTATION_COMPLETE`, 26 operations (adds neutral `IMPLEMENTATION_EVIDENCE_COMPILE`), `governed_entity_completeness_gate` is CONDITIONAL. `WEB-GOV-01-S083A` (Basic Design Stepwise Authoring) is required by STAGE-02/03/04 matrices.

[Deliverable Content Requirement]
- Date: 2026-09-28
- Context: User rejected an audit that listed only filenames and required the realignment deliverable to carry real content
- Instructions:
  - When asked to build, realign, or produce an audit, the generated files MUST contain their actual derived content (values, rows, bindings, target fields, tables), never a bare list of file names or an outline.

