# Product Execution Environment Admission Standard / 產品執行環境准入規範

This document is an external governance standard for Product Execution Environment admission. It is intentionally separated from reusable Mother/Page Stage semantics and is loaded only when the applicable Product Execution Workline admission condition is active.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S000 -->
## 0. Scope and Layer Boundary / 範圍與分層邊界

This standard governs Product-governance release selection, governance-revision transition, Application Baseline admission/materialization, and their audits. It MUST_NOT enter the reusable Page Stage normative denominator, MUST_NOT alter generic Stage operation/input/output universes, and MUST_NOT make any concrete repository, branch, framework, provider, or application-source location part of Mother/Stage common semantics.

Product-specific repository/branch/source values are runtime/admission bindings owned by the Product Execution Workline or external environment authority. The reusable Stage core may consume only the resulting admitted authority/evidence when a stage operation actually requires it.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S001 -->
## 1. Product Governance Release Selection and Revision Transition / 產品治理發布選擇與版本轉移

**Scope isolation:** This section is an external Product Execution Environment admission contract. It is NOT part of the reusable Page Stage normative denominator, MUST_NOT change the Page Stage operation/input/output universe, and grants zero Page Stage definition or completion credit. It applies only when a concrete Product Execution Workline elects to consume a released governance revision.

Formal Product Stage execution MUST NOT follow a moving governance branch, tag, latest-tip convention, chat-selected revision, or candidate workline. The Product Execution Workline MUST materialize exactly one Current `PRODUCT_SELECTED_GOVERNANCE_RELEASE` and every effectful Product Stage workflow MUST read that product-owned selection before loading governance.

The selection MUST bind one exact governance repository, immutable released commit SHA/tree SHA, released governance UID/revision/display version, release receipt digest/reference, Root Manifest digest, explicit product selection Authority, and fresh post-promotion reverification evidence. The selected governance checkout MUST be performed by exact commit SHA. A governance candidate, a branch tip that later advances, a release receipt still lacking fresh reverification, or a selection whose exact commit cannot be independently resolved receives zero formal Product Stage execution or closure credit.

Every active Product Work Unit MUST materialize one `PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT` before its first effectful operation. The receipt MUST bind the Work Unit/Stage, the product-owned selected-release reference, exact loaded governance commit/tree, governance UID/revision, Root Manifest digest, effective normative-set digest, loader identity and timestamp. `NO_PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT = NO_EXTERNAL_PRODUCT_EXECUTION`; a receipt bound to another selected release, another Work Unit, a moving branch ref, or a candidate governance identity is invalid.

A change of the product-owned selected governance release MUST be a separate Product governance-selection transition, never an incidental consequence of a remote branch moving. Before any old-UID Product artifact can receive Current credit, one `GOVERNANCE_REVISION_TRANSITION_RECEIPT` MUST classify the prior selection, new selection, impacted Work Units/artifact classes, reverse-dependency impact, preserved immutable facts, invalidated execution evidence, earliest legal re-entry capability/Stage, and required fresh verification. Impacted old-UID closure is `REVERIFY_REQUIRED`. Unaffected immutable Product Authority or design facts MAY be preserved only with exact hash and reverse-dependency proof; old execution matrices, handoff/readiness ledgers, normalized execution evidence and terminal receipts MUST NOT be silently relabeled to the new UID.

When the Current Product scope/matrix/evidence is still bound to an older governance UID and no valid transition receipt exists, execution MUST fail as `GOVERNANCE_REVISION_TRANSITION_REQUIRED`. When a valid transition receipt exists but the affected Work Unit has not yet been freshly rebound/reverified, execution MUST fail as `GOVERNANCE_REVISION_TRANSITION_REENTRY_REQUIRED` at the receipt's earliest owner. The transition transaction occurs before normal Stage execution and grants zero Product completion credit by itself.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S002 -->
## 2. Application Baseline Admission and Current-Workline Materialization / 應用基線准入與目前工作線實體化

**Scope isolation:** This section is a conditional external Product/Application admission contract, not a universal Page Stage requirement. It applies only when a concrete Product Execution Workline lacks an admitted Current application baseline. It MUST_NOT be included in the reusable Page Stage normative denominator, MUST_NOT make any named branch/repository/framework part of Mother semantics, and grants zero Page Stage definition or completion credit.

A missing Current `APPLICATION_ROOT` is not a request for AI or the user to choose another branch. When a usable application exists only outside the Registry-selected Product Execution Workline, that source is provenance only and the implementation-capability admission result is `APPLICATION_BASELINE_ADMISSION_REQUIRED` until a governed baseline-admission transaction materializes an allowed baseline into the Current Product Execution Workline.

Before any such materialization, one `APPLICATION_BASELINE_ADMISSION_MANIFEST` MUST bind: source repository/branch/exact head/tree and source path set; source Authority/provenance; target repository and Registry-selected Product Execution Branch; exact target pre-write HEAD; canonical application-root identity; bounded include/exclude/write set; conflict/overwrite policy; required preserved Product/Governance/Stage artifacts; approval/Change Request Authority; and abort conditions. The source branch is never thereby promoted to Current implementation target.

Materialization MUST use compare-and-swap against the declared target pre-write HEAD, write only the admitted set, preserve unrelated Current Product execution/governance state, fail on unresolved path/content conflicts, and emit an external or persisted `APPLICATION_BASELINE_MATERIALIZATION_RECEIPT` bound to the exact admitted source snapshot, target branch, materialization commit, canonical application root, resulting governed application path/object set, conflict result and admission-manifest reference. Manual copy, unbounded merge, latest-branch import, or silent overwrite receives no admission credit.

After admission, one `APPLICATION_BASELINE_SNAPSHOT` MUST bind the Current Product repository/branch, a baseline commit that is an ancestor of the implementation-capability execution head, canonical application root, exact tracked application path/object set, baseline source kind (`PREEXISTING_CURRENT_BASELINE` or `AUTHORIZED_MIGRATION`), Authority/provenance and—when migrated—the materialization receipt. The foundation-freeze -> implementation-capability `APPLICATION_ROOT` target-resolution receipt MUST consume this snapshot. The snapshot's governed application objects MUST still match the Current Product workline before implementation-capability execution starts.

`implementation_diff_exact_trace_required` is anchored to this application baseline. Every applicable implementation-operation result that mutates program source MUST trace Program Artifact UID, canonical path/owner/Construction Profile, baseline/before identity, after identity, producing operation and exact diff evidence. An applicable implementation operation with no repository-source mutation MUST carry explicit no-source-diff evidence/Authority rather than disappear from the implementation-diff denominator.

A non-Current branch containing the desired application, a non-empty target string, or an existing historical build is never a substitute for Current-workline materialization. Until the admission transaction, Current application snapshot and foundation-freeze -> implementation-capability handoff have all passed under the product-selected released governance, the implementation capability remains BLOCKED and MUST_NOT create an alternative app root, bootstrap a second framework, or write program source.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S003 -->
## 3. Product Governance Release Selection and Transition Audit / 產品治理發布選擇與轉移稽核

**Scope isolation:** This audit applies only to an external Product Execution Environment that consumes a released governance revision. It is excluded from the reusable Page Stage normative denominator and cannot grant or withhold generic Page Stage definition completeness by itself.

Audit MUST prove that every formal Product Stage execution used one product-owned `PRODUCT_SELECTED_GOVERNANCE_RELEASE` bound to an exact immutable released governance commit/tree/UID/revision and fresh post-promotion reverification evidence. A workflow checkout of a moving governance branch/tag, a candidate governance identity, a selected SHA different from the actually loaded checkout, or a missing/invalid `PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT` is a blocker and receives zero Product Stage credit.

For a selected-governance change, Audit MUST reconstruct the `GOVERNANCE_REVISION_TRANSITION_RECEIPT` and verify old/new selection identities, impacted Work Units and reverse dependencies, preserved immutable facts, invalidated execution/evidence classes, earliest legal re-entry owner, fresh matrix/handoff/evidence regeneration and terminal verification. Relabeling an old-UID closure to a new UID without fresh transition evidence is false completion. A governance branch tip advancing by itself MUST NOT change Product Current Governance.

Negative regression MUST include at least: selected SHA differs from loaded governance checkout; selected identity is candidate/not released; selected release lacks fresh reverification evidence; old-governance scope/evidence reused without transition receipt; transition receipt bound to another Work Unit; and impacted closure retained as PASS instead of `REVERIFY_REQUIRED`.

<!-- SECTION_UID: WEB-EXT-ADMISSION-01-S004 -->
## 4. Application Baseline Admission and Materialization Audit / 應用基線准入與實體化稽核

**Scope isolation:** This audit is conditional on an external Product/Application baseline-admission transaction. It is not a universal Page Stage audit dimension and MUST_NOT make a repository branch, application framework, or source-migration path part of common Page Stage semantics.

Audit MUST distinguish source provenance from Current implementation target. When an application baseline originates from a non-Current branch/repository snapshot, Audit MUST require a pre-existing `APPLICATION_BASELINE_ADMISSION_MANIFEST`, bounded materialization transaction and `APPLICATION_BASELINE_MATERIALIZATION_RECEIPT` before that content can satisfy the Current `APPLICATION_ROOT`.

Audit MUST verify exact source repository/branch/head/tree/path set, target repository/Registry-selected Product Execution Branch and pre-write HEAD, bounded include/exclude/write set, preservation set, conflict policy/result, authorization, materialization commit ancestry, canonical application root and resulting application object identities. Source-branch presence alone, manual copy, unbounded merge, latest-tip import or silent overwrite is not admission evidence.

Before implementation-capability admission, Audit MUST independently validate `APPLICATION_BASELINE_SNAPSHOT`: its baseline commit is an ancestor of the Current Product execution head, its canonical application root is physically present/tracked, every governed application path/object identity still matches Current Git state, and its source kind/provenance is valid. For migrated baselines the snapshot MUST trace to the admitted materialization receipt.

Implementation-capability diff audit MUST use that snapshot as the before-state denominator for the complete applicable implementation-operation denominator. Every applicable operation MUST either carry exact Program Artifact/path/owner/profile before-after-diff trace or explicit Authority-backed no-source-diff evidence. Missing baseline, missing operation coverage, stale baseline object, source-branch-as-target substitution, materialization receipt mismatch, unresolved import conflict or application root absent after claimed migration MUST block implementation-capability admission/closure.
