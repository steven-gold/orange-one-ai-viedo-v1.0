# Product Execution Environment Admission Standard / 產品執行環境准入規範

This document is an external execution-environment standard separated from reusable Mother/Common Stage semantics. Its purpose is to bind a concrete Product Workline to one exact Current Governance snapshot and, when needed, one admitted Current application baseline. It does not require unrelated external people, accounts, auditors, signers, or third-party evidence.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S000 -->
## 0. Scope and Layer Boundary / 範圍與分層邊界

The Product Execution Workline MUST consume Word-derived governance through one exact Current Governance snapshot. Repository/branch/source values are execution bindings only and MUST_NOT become reusable Mother/Stage semantics.

The authoritative product-design source remains the registered Word source and its deterministic structured projection. When Word content is insufficient, AI MAY supplement only from the same Word context and existing canonical system relationships; such supplementation MUST be traceable as derived design reasoning and MUST_NOT become a second source Authority.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S001 -->
## 1. Product Current Governance Snapshot Selection / 產品目前治理快照選擇

Before an effectful Product Stage operation, the Product Workline MUST materialize exactly one `PRODUCT_SELECTED_CURRENT_GOVERNANCE` at `STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml`.

The selection MUST bind: governance repository, governance branch, exact commit SHA, exact tree SHA, governance UID, governance revision, display version, Root Manifest SHA-256, product branch, selection Authority, and selection mode `EXACT_CURRENT_GOVERNANCE_SNAPSHOT`.

The selected governance checkout MUST use the exact commit SHA. A moving branch tip, chat-only version label, stale UID, stale Root Manifest digest, or a checkout different from the selected commit receives zero Product Stage execution credit.

The selected governance Registry MUST report `status: CURRENT`; its governance identity MUST report `status: CURRENT` and `identity_state: EXACT_HEAD_AND_BUNDLE_DIGEST_BOUND`.

Every effectful Stage Work Unit using `governance_execution_mode: CURRENT_VALIDATED_GOVERNANCE` MUST materialize one `PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT` before its first operation. The receipt MUST bind the Work Unit, Stage, selected-governance reference, exact commit/tree, governance UID/revision, Root Manifest digest, effective normative-set digest, loader identity, and timestamp.

No governance release receipt, immutable-release state, governance promotion transaction, external auditor, external signer, external-manifest provenance, or unrelated account is required for Product Stage execution.

When the selected Current Governance UID changes, affected prior execution evidence becomes `REVERIFY_REQUIRED`. Old matrices, handoff/readiness ledgers, normalized execution evidence, and terminal receipts MUST_NOT be silently relabeled to the new UID. Unaffected immutable Word/source/design facts MAY be preserved only with exact hash and reverse-dependency proof. Re-entry MUST start at the earliest affected owner.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S002 -->
## 2. Application Baseline Admission and Current-Workline Materialization / 應用基線准入與目前工作線實體化

This section is conditional and applies only when a concrete Product Execution Workline lacks an admitted Current application baseline. It is not a universal Common Stage requirement.

A missing Current `APPLICATION_ROOT` MUST_NOT be filled by silently selecting another branch. If usable application source exists outside the Current Product Workline, that source is provenance only until a governed baseline-admission transaction materializes an allowed baseline into the Current Product Workline.

Before materialization, one `APPLICATION_BASELINE_ADMISSION_MANIFEST` MUST bind source repository/branch/exact head/tree/path set, source Authority, target repository/branch/pre-write HEAD, canonical application root, bounded include/exclude/write set, preserve set, conflict policy, authorization, and abort conditions.

Materialization MUST use compare-and-swap against the target pre-write HEAD, write only the admitted set, preserve unrelated Current Product/Governance/Stage state, fail on unresolved conflict, and emit `APPLICATION_BASELINE_MATERIALIZATION_RECEIPT`.

After admission, one `APPLICATION_BASELINE_SNAPSHOT` MUST bind the Current Product repository/branch, ancestor baseline commit, canonical application root, exact tracked path/object set, source kind, Authority/provenance, and—when migrated—the materialization receipt.

Implementation-diff evidence MUST use this snapshot as the before-state denominator. Every applicable implementation operation MUST carry exact Program Artifact/path/owner/profile before-after-diff trace or explicit Authority-backed no-source-diff evidence.

Until the baseline admission, Current application snapshot, and foundation-freeze → implementation-capability handoff are valid under the selected exact Current Governance snapshot, the implementation capability remains BLOCKED and MUST_NOT create a parallel app root or second framework.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S003 -->
## 3. Product Current Governance Snapshot Audit / 產品目前治理快照稽核

Audit MUST prove that every Product Stage execution using Current-governance mode consumed exactly one product-owned `PRODUCT_SELECTED_CURRENT_GOVERNANCE` bound to the same governance checkout actually loaded by the workflow.

Audit MUST verify exact commit/tree/UID/revision/display version/Root Manifest hash, `PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT`, and fresh inline internal validation before effectful operations.

Negative regression MUST include at least: selected SHA differs from loaded checkout; stale governance UID; Root Manifest hash mismatch; missing Current-governance load receipt; moving branch tip used instead of exact commit; affected old-governance execution evidence reused without re-entry; impacted closure retained as PASS instead of `REVERIFY_REQUIRED`.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S004 -->
## 4. Application Baseline Admission and Materialization Audit / 應用基線准入與實體化稽核

Audit MUST distinguish source provenance from Current implementation target. A non-Current branch/repository snapshot cannot become Current merely because it exists.

Audit MUST verify exact source repository/branch/head/tree/path set, target repository/Product Workline/pre-write HEAD, bounded include/exclude/write set, preserve set, conflict result, authorization, materialization commit ancestry, canonical application root, and resulting application object identities.

Before implementation-capability admission, Audit MUST validate `APPLICATION_BASELINE_SNAPSHOT`: ancestor baseline commit, physically present/tracked application root, exact path/object identities, valid source kind/provenance, and migration receipt when applicable.

Implementation-capability diff audit MUST cover the complete applicable implementation-operation denominator. Missing baseline, missing operation coverage, stale object, source-branch-as-target substitution, receipt mismatch, unresolved conflict, or application root absent after claimed migration MUST block implementation-capability admission/closure.
