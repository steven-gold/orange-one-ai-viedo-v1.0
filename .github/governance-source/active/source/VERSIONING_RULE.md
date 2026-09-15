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

