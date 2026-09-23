# Versioning Rule

- Immutable historical baselines remain immutable. `v2.1.11` is the verified predecessor of this candidate and MUST NOT be edited in place.
- `v2.1.12` is a successor-state monotonic predecessor-validator and Required Evidence parse-integrity bugfix candidate.
- A locked/verified predecessor MUST NOT be edited. Any reproduced governance defect opens a new bugfix candidate, followed by full regression, external trust-root regeneration, clean-package verification, Source-Control replay/synchronization against the applicable legal phase, and user freeze decision.
- A defect whose failure mode can recur in more than one lifecycle Stage MUST be repaired at the common invariant layer and enforced in every affected Stage, not patched only at the first observed Stage.
- Unresolved Authority carry-forward identity is the exact tuple `(gap_uid, authority_ref, disposition, authority_evidence_ref)`. Count-only, GAP-UID-only, or alias-based validation MUST NOT satisfy continuity.
- Every ledger-local terminal CI receipt projection MUST preserve the canonical six fields `provider`, `repository_or_project`, `head_sha`, `run_id`, `job_denominator`, and `conclusion`. Abbreviated `jobs` or `result` fields MAY be display aliases but MUST NOT substitute for the canonical receipt.
- Closure metadata MUST remain monotonic for already-proven predecessor facts. A later legal successor MAY add evidence, supersede it with explicit provenance, or mark affected consumers REVERIFY_REQUIRED, but MUST NOT silently delete or revert established predecessor start/completion/proof/run identities.
- Materialization CI evidence and terminal closure CI receipt are distinct evidence identities. A terminal external CI receipt MUST NOT require self-writing its own run identity into the same commit it validates.
- Website/page authority versions remain independent from governance-package versions.

- A predecessor validator MUST_NOT hard-code global Current state equality to its own terminal state after a registered legal successor begins. Legal successor presence is accepted only while predecessor completion/proofs/Authority identity/terminal receipts remain intact; illegal skip remains BLOCKED by the Phase Boundary Gate.
- Every registered predecessor→successor edge MUST have positive legal-successor regression and negative illegal-skip/reversion/drift regression.
- Required Evidence presence is not acceptance. Exact evidence bytes MUST pass parser plus applicable schema/required-field validation before MATERIALIZED/PASS/CLOSED or Stage exit-gate use; malformed or unparseable Required Evidence MUST BLOCK.

## External Trust Root Rule

The candidate package cannot self-prove integrity. The trust-root hash set is an external release-control artifact. Full Pre-formal verification MUST use a matching external trust root; Formal Freeze is prohibited when external trust verification is absent or fails.

## v2.1.13 successor rule
- v2.1.12 remains the immutable predecessor evidence baseline; v2.1.13 is a successor governance hardening revision.
- A defect first observed in one Stage MUST be repaired at the common invariant layer when the same defect class can occur elsewhere.
- Stale predecessor snapshots MUST leave the Current projection after a verified successor is accepted, but predecessor evidence MUST remain immutable history-only; deletion is not a substitute for supersession.
- Port exposure, state events, registry membership and semantic similarity MUST NOT be promoted into trigger/action/error bindings without an explicit binding or uniquely resolving Current Authority.
- FINAL/LOCKED status does not confer Current Authority; Current Authority set membership is mandatory.
- Required Evidence MUST physically materialize and parse/schema validate before use.
- Validator schema-path/enum drift is a validator defect; schema-declared sparse zero-valued optional classes may be absent and still equal zero.
- A denominator or blocker-set change invalidates predecessor receipts for successor verification until a new exact external receipt exists.

## v2.1.14 test-feedback / specification-evolution rule
- v2.1.13 remains the immutable locally verified predecessor; v2.1.14 introduces the mandatory Stage-test defect-feedback and specification-evolution closed loop.
- Every reproduced Stage-test bug/gap MUST be recorded and scoped before repair. `GLOBAL_SHARED` defects are repaired at the common invariant layer and every affected governance layer; `STAGE_LOCAL` defects MUST remain local unless recurrence evidence authorizes expansion.
- The required promotion sequence is: Stage test -> defect/gap record -> production conformance review -> scope classification -> spec patch -> multidirection high-pressure test -> `v2.1.X` version promotion -> Source-Control versioned candidate sync -> predecessor backtrace -> full Current revalidation -> Source-Control Current authority promotion -> Formal Freeze -> next Stage.
- Every adopter MUST configure exactly one Source-Control Current governance entry. The path is adapter-defined; historical evidence and versioned candidates MUST NOT compete with it as Current Authority.
- Current authority promotion before predecessor backtrace and full Current revalidation is forbidden for every Source-Control adapter.
- GitHub adapter profile for this project uses `docs/governance/CURRENT_GOVERNANCE_SPEC.yaml`; this path is profile-specific and is not a common-provider requirement.



### v2.1.14 product-neutral applicability / entity lifecycle addendum
- Common governance is product-neutral and MUST NOT require ACPOS or any other named product to interpret or execute common invariants.
- Product-specific provenance, fixtures, compatibility aliases, and Product Profile extensions are permitted only when they do not narrow or weaken common governance.
- Every governed interaction scope MUST materialize Business Entity Inventory, Business Entity Operation Matrix, and Entity Hierarchy Matrix before functional closure.
- Functional completeness denominator is `Business Entity × Applicable REQUIRED Operation + required hierarchy edges`; page/control/action/API/port counts are not substitutes.
- A product-binding substitution audit is required before Formal Freeze.
### v2.1.14 bounded functional completion / visual synchronization addendum
- Automatic function completion MUST start from a registered REQUIRED gap or operation and MUST be restricted to the minimal registered dependency closure needed to close it.
- A `FUNCTION_ADMISSION_SCORECARD` may rank necessity/utility, but no score can create Authority, resolve ambiguity, or authorize unsupported product-scope expansion.
- Every transitive dependency requires independent admission evidence; cycles and generic CRUD/sibling symmetry expansion are blocked; out-of-closure discoveries reopen design instead of recursively extending implementation.
- User-visible/user-observable functional additions require synchronized visual/interaction bindings and approved design authority before implementation. Logic-only or visual-only completion is not acceptable.
- Indexed validation is a performance optimization only. It may cache unchanged content and select impacted validators, but it MUST NOT reduce required validation coverage; an index-drift full sweep is mandatory before freeze.


### v2.1.14 functional workbench / interaction-topology / conditional AI-continuity addendum
- Functional completeness includes interaction topology: required operations that exist individually but are fragmented across unapproved surfaces are not complete.
- Stage-02 owns the functional workbench boundary and operation/context topology; Stage-03 owns its visual projection and may not redefine semantic order or continuity.
- Cross-surface flows require explicit context handoff; responsive reflow must preserve semantic operation order.
- AI-assisted interaction governance is conditional. Declared AI conversation/multi-agent scopes must preserve identity continuity, same-baseline comparison, governed output formalization, exact revision lineage, and isolated branch adoption.
- Non-AI products remain fully valid adopters of the common specification without implementing AI-specific artifacts.

## v2.1.15 canonical Stage execution optimization rule
- v2.1.15 consolidates Stage-test-proven execution defects into common governance and introduces one frozen canonical preflight/overlay/classification/impact model for every Stage attempt.
- Existing authorized functions with missing before/after flow remain eligible for bounded automatic minimal completion when the frozen functional chain uniquely determines one role-correct closure.
- Exact-value absence alone is not Authority Gap; two or more materially distinct viable behaviors are required for Product Authority escalation.
- Stage execution uses dependency-ordered batches, local reverse-impact validation, checkpoint full sweeps, one Current Problem Register, and an append-only Resolution Ledger.
- A normative promotion invalidates active Stage completion credit and requires a clean retry under the new Governance UID.

## v2.2.0 neutral-portable governance rule
- v2.2.0 is the verified neutral/portable predecessor source revision. Product/profile identities may exist only in explicitly non-global profile/provenance layers and MUST NOT be required to interpret reusable Mother Policy.
- Semantic authority baseline identity remains immutable across a successor unless an explicit semantic-baseline maintenance authorization changes that baseline itself.

## v2.2.1 full-line source-integrity successor rule
- v2.2.1 is a bounded successor for reproduced Full-Line integrity defects: stale semantic-baseline hash consumers, stale revision whitelists, stale prose-coupled validators, and product-neutrality classification drift.
- Validator/harness defects MUST be repaired at validation implementation; they MUST NOT be solved by weakening denominators, deleting expectations, or reinserting obsolete prose into Mother Policy.
- The reusable Mother Policy MUST remain product-neutral. Product-specific profile identity is legal only in an explicitly classified non-global execution-profile/provenance context.
- Source bytes, Root Manifest, compiled baseline, checksum manifest, deterministic package identity, external trust projection, and Current governance source-lineage projection MUST advance atomically.

## v2.2.10 blueprint construction traceability hardening rule
- v2.2.9 remains immutable predecessor history.
- A blueprint is not implementation-ready merely because controls/components exist or one overview visual was produced.
- Applicable blueprint artifacts, function-to-visual and visual-to-function traces, multi-state visual evidence/annotations, construction-delta classification, quantitative freeze coverage, and implementation handoff are Required before Design Freeze/implementation where applicable.
- Product-specific behavior remains governed by Product Authority; these common rules define completeness and traceability and MUST_NOT invent product semantics.

## v2.2.11 basic design visual integration rule
- Basic Design and downstream implementation/execution are separate lifecycle concerns.
- Basic Design MUST finish requirements, architecture, functional relationships, visual architecture, complete visual style, high-fidelity scenario visuals, document-embedded figures, design review, and freeze without requiring code/runtime/deployment evidence.
- Existing project Visual Authority MUST be read and inherited first; if absent, Basic Design MUST define and approve a complete reusable visual style before final visual candidates.
- Common Mother policy remains product-neutral and MUST NOT embed a product-specific palette, brand, shell geometry, page name, route, provider, or fixed implementation technology.

## v2.2.12 basic design atomic materialization rule
- v2.2.11 remains immutable predecessor history.
- Normative content changed, therefore Current Governance UID and display version must change.
- Required design denominators must be enumerated row-by-row; summary-only or representative-sample completion is forbidden.
- Human and machine design deliverables must reconcile to the same exact required denominator before Basic Design Freeze.

## v2.2.13 shared Stage-01/02 contract hardening rule
- v2.2.12 remains immutable predecessor history.
- Missing explicit trigger syntax is not automatically a product Authority choice when structured Current evidence uniquely proves a system-owned operation.
- Producer/consumer field-schema drift fails before materialization; alias fallback cannot hide the defect.
- Historical product values cannot fill Current missing contracts.
- Reusable Stage consumers remain product-neutral and task-layer order is not bypassable.

## v2.2.14 Stage-03 visual materialization hardening rule
- v2.2.13 remains immutable predecessor history.
- A selected profile may specialize sequence and artifact names but may not omit applicable Mother-required deliverables.
- Stage-03 Visual Review requires reviewable visual evidence, explicit annotation/inheritance/scenario artifacts, atomic Workbench projection, and a Current denominator that preserves unresolved visual Authority blockers.
- UNRESOLVED visual Authority is not AUTHORITY_ABSENT and never authorizes AI style invention.

## v2.2.15 Stage-03 visual materialization promotion closure rule
- v2.2.14 is retained as invalid-promotion predecessor provenance and receives no Current closure credit.
- v2.2.15 preserves the approved Stage-03 Mother/Profile materialization rules and reissues them through a valid atomic successor transaction.
- Product Stage-03 must restart from preserved Stage-01/02 immutable inputs after exact-head governance closure.

## v2.2.17 typography computed metrics hardening rule
- Typography intent, overflow checks, and screenshots alone do not prove computed-style conformance.
- Every applicable text-bearing target requires Authority-derived expected metrics and runtime computed evidence.
- Representative samples, manually entered computed values, and missing-target denominators are blocking.

## v2.2.18 structured-source projection lock rule
- Captured Word/DOCX bytes are immutable; byte changes create a new source revision.
- Canonical YAML projection has one registered fixed schema/ordering contract and is non-authority.
- Reconciliation PASS freezes the exact Word/YAML pair; any pair mutation invalidates admission.
- Stage-01 may consume only the frozen projection and may not reparse Word as a semantic fallback.

## v2.2.19 page-neutral projection schema portability rule
- Captured Word/DOCX bytes are immutable; byte changes create a new source revision.
- Canonical YAML projection has one registered fixed schema/ordering contract and is non-authority.
- Reconciliation PASS freezes the exact Word/YAML pair; any pair mutation invalidates admission.
- Stage-01 may consume only the frozen projection and may not reparse Word as a semantic fallback.

## v2.2.20 cross-page portability regression closure rule
- Captured Word/DOCX bytes are immutable; byte changes create a new source revision.
- Canonical YAML projection has one registered fixed schema/ordering contract and is non-authority.
- Reconciliation PASS freezes the exact Word/YAML pair; any pair mutation invalidates admission.
- Stage-01 may consume only the frozen projection and may not reparse Word as a semantic fallback.

## v2.2.22 projection next-step consumer sync rule
- Reusable projection consumers MUST resolve structured-document next-step identity from the canonical source contract.
- Legacy local next-step literals are forbidden when a canonical contract field exists.
- Positive and negative regression fixtures MUST consume the same canonical sequence.
