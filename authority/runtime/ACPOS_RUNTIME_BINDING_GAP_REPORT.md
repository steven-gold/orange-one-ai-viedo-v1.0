# ACPOS Runtime Binding Gap Report

Revision: 2026-09-10 CURRENT-ONLY  
Status: ACTIVE_EFFECTFUL_RUNTIME_CLOSURE

## Authority and evidence policy

This report is a Current gap record. Construction behavior is resolved from the single active construction authority. Deployment state is resolved from GitHub Current, Vercel Current Deployment, and Neon Current Production. Historical source material is provenance only and is not executable authority.

Do not create parallel runtimes, duplicate APIs, synthetic business rows, guessed permissions, guessed provider routes, or forced-enabled controls to close a gap.

## Verified Current Production

- Production main SHA: `5dd33537d6207d8a5b195afc1a3a8a1c903b0d3c`
- Vercel commit status: SUCCESS
- Production URL: `https://orange-one-acpos-test.vercel.app`
- Main Release Gate #1017: SUCCESS
- Post-Deploy #1325: SUCCESS
- Readiness: HTTP 200
- Routes/projections: 18
- Authenticated pages visible: 18
- Browser smoke: 54 cases
- Front navigation: 8
- Admin navigation: 8
- Production DOM governance: 548 interactive / 548 governed / 362 enabled / 186 disabled
- Neon Production: `wild-wave-25661146 / main / neondb`
- Migrations: 40/40
- Latest migration: `0040_kb_source_retire_audit_rls_closure`
- Active permission resources: 3672
- Approved ALLOW assignments: 158
- RLS tables: 62
- RLS policies: 123
- Approved Provider capabilities: 4
- Approved secret references: 4
- Queue: 1
- Worker: 1

## Verified new-branch construction

- Current new SHA: `0f5aff87d4dc14612fc68151b40210bd34728ae4`
- Release Gate #1021: SUCCESS
- KB retire runtime + migration 0040 application code exists on new and passed release validation.
- CORE control gating now reports prerequisite/runtime blockers instead of marking all action controls enabled.
- These application changes are not yet merged/deployed to Production main.

## Current runtime blockers

### 1. Department materialization chain

Production currently contains:

- department_tasks: 1
- the only department task is TEST_ONLY and WAITING_DEPENDENCY
- department_script_views: 0
- task_input_manifests: 0
- instruction_packages: 0
- canonical_script_versions: 0
- script_projection_rules: 0
- quality_criteria_versions: 0
- rights_profiles: 0
- route_policies: 0

The existing ASSET/VIDEO production runtime consumes these canonical objects and correctly fails closed when they do not exist. Therefore the blocker is upstream materialization, not a reason to force-enable UI controls.

Required closure chain:

`governed lock decision -> child lock materialization -> work package compiler -> task orchestrator -> department script view -> task input manifest -> instruction package -> department runtime`

### 2. CORE

CORE truthful gating is constructed on new and Release Gate #1021 is green. Remaining runtime closures include registered operations whose canonical materializer/decision owner is not yet connected. Production main still exposes the prior UI gating until consolidated deployment.

### 3. ASSET

ASSET production port runtime is materialized, including provider job, output, scorecard/finding/correction/handoff paths. Positive execution remains blocked by missing canonical department execution inputs and exact route/instruction lineage.

### 4. VIDEO

VIDEO production port runtime is materialized. Positive execution remains blocked by the same upstream execution-input chain and exact dependency handoff.

### 5. EDIT + VOICE

EDIT+VOICE runtime exists, but positive project-task execution requires an exact accepted VIDEO handoff, task fingerprint, runtime run lineage, output verification/lock, and final QA handoff. The upstream task/materialization chain is not yet complete.

### 6. QA

QA lifecycle runtime exists. Positive review requires exact upstream handoff/output/criteria/evidence lineage. Release-package creation remains incomplete until its canonical evidence owner is materialized.

### 7. IAM / ERP / AIAPI / SOC

Controlled implementation evidence does not equal Production effectful acceptance. The remaining work is to prove each applicable mutation through permission -> runtime -> persistence -> reload -> rollback/error behavior without inventing missing persistence fields or scope owners.

### 8. AI Conversation

Production conversation code has pre-deploy evidence, but the final consolidated Production E2E remains pending. It must be executed after the final main deployment.

### 9. Production Effectful Acceptance

Current DOM acceptance is a visual/governance test. It does not click every enabled control and does not prove API/DB/Queue/Provider effects.

A permanent Production runner is still required for applicable enabled controls:

`UI click -> API -> permission -> runtime -> DB/Queue/Provider effect -> response -> reload/read-back -> negative path -> cleanup`

### 10. Control/action denominator

The sealed historical control/action baseline remains a denominator reference only. Final acceptance must explicitly seal Current expansion before the denominator is recomputed. Do not use the historical baseline as proof that Current controls are functionally complete.

## Non-blocking external account issues

- DeepSeek: HTTP 402, user deferred account/balance remediation.
- OpenRouter: HTTP 401, user deferred credential remediation.
- Groq and Google remain the healthy Production provider pool.

## Next executable item

Close the canonical department materialization owner chain on `new`, then run positive ASSET -> VIDEO -> EDIT+VOICE -> QA effectful paths before building exhaustive Production button acceptance.
