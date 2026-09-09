# Strict Audit Matrix

Freeze date: 2026-09-08
Live SHA: `dc84346a41bbadc2537fe2de9ba535126547e0cf` (absent from local git)
Local `new`: `4c43aa2`
Local `origin/main`: `d5161fb`

Status key: 完整 | 已完成 | 未完成 | 待修正 | 已修正

## Live control plane

| id | layer | scope | strict_status | live | note |
|---|---|---|---|---|---|
| LIVE-HEALTH | LIVE | `/health` | 待修正 | 200 `status=ok` SHA `dc84346...` | SHA not in this clone |
| LIVE-READY | LIVE | `/health/ready` | 待修正 | 200 `status=ready` extra fields | local route file has no `readiness_scope` / `ready_account_count`; authority forbids production-ready claim |
| LIVE-PROTECTED | LIVE | `*-3zbubbsjl-gold5757.vercel.app` | 未完成 | 401 Protected deployment | missing `VERCEL_AUTOMATION_BYPASS_SECRET` |
| LIVE-SHA-ALIGN | LIVE | public alias vs git | 待修正 | public SHA absent | one later authorized deploy required |

## Pages

Unauthenticated projection on public alias: HTTP 403 `IDENTITY_RUNTIME_NOT_BOUND`. HTML shells are 200.

| id | page_uid | route | visual | projection live | production command bind | strict_status |
|---|---|---|---|---|---|---|
| PG-WB01 | workspace:WB-01 | `/` | 已完成 VIS-00/01 | 403 identity | WB-01 SQL bind exists locally | 待修正 |
| PG-CORE | CORE-01 | `/core` | 已完成 | 403 identity | partial SQL create/validate/lock/review/blueprint/script; CANDIDATE/DNA-LOCK default throw | 待修正 |
| PG-ASSET | ASSET-01 | `/assets` | 已完成 | 403 identity | bind + finding/scorecard/decide/handoff/layer/correction SQL; execute/retry/patch throw | 待修正 |
| PG-VIDEO | VIDEO-01 | `/video` | 已完成 | 403 identity | bind + finding/scorecard/decide/handoff/correction SQL; execute/retry throw | 待修正 |
| PG-EDIT | EDIT-01 | `/edit` | 已完成 | 403 identity | client HTTP invoker + voice SQL; draft ABSENT; startVoice throw | 待修正 |
| PG-QA | QA-01 | `/qa` | 已完成 | 403 identity | start/recheck/pass/fail/release/correction SQL; finding AUTHORITY_GAP | 待修正 |
| PG-DB | admin:DB-01 | `/database` | 已完成 | 403 identity | partial read; TRACE/INTEGRITY/AUDIT empty | 待修正 |
| PG-STR-WS | workspace:STR-01 | `/strategy` | 已完成 | 403 identity | decision execute throws; candidate compare unbound | 未完成 |
| PG-INFO | workspace:INFO-01 | `/info` | 已完成 | 403 identity | write `INFO_WRITE_RUNTIME_NOT_MATERIALIZED` | 未完成 |
| PG-SYS | admin:SYS-01 | `/admin/system` | 已完成 | 403 identity | lifecycle execute throws; release binding AUTHORITY_GAP | 未完成 |
| PG-IAM | admin:IAM-01 | `/admin/accounts` | 已完成 | 403 identity | write `IAM01_WRITE_RUNTIME_NOT_MATERIALIZED` | 未完成 |
| PG-DEV | admin:DEV-01 | `/admin/dev` | 已完成 | 403 identity | outreach routes ABSENT; AUTHORITY_GAP on semantics | 未完成 |
| PG-SOC | admin:SOC-01 | `/admin/social` | 已完成 | 403 identity | effectful default `PROVIDER_GATEWAY_NOT_MATERIALIZED` | 未完成 |
| PG-ERP | admin:ERP-01 | `/admin/erp` | 已完成 | 403 identity | effectful default `PROVIDER_GATEWAY_NOT_MATERIALIZED` | 未完成 |
| PG-AIAPI | admin:AIAPI-01 | `/admin/aiapi` | 已完成 | 403 identity | UI `REMAP_REQUIRED_NOT_EXECUTED`; no effectful port | 未完成 |
| PG-SG02 | admin:SG-02 | `/admin/qa-criteria` | 已完成 | 403 identity | production governance bind incomplete | 未完成 |
| PG-STR-AD | admin:STR-01 | `/admin/strategy` | 已完成 | 403 identity | remap/source AUTHORITY_GAP | 未完成 |
| PG-KB | admin:KB-01 | `/admin/knowledge` | 已完成 | 403 identity | search/citation/create/save SQL; pause/resume/retire/drafts throw | 待修正 |

完整 count for pages: 0

## Page authority inventory vs production execute

Counts are Current Authority / runtime-contract constants. Production execute is `identityPageCommandRuntime.ts` unless noted ABSENT. Visual shells stay 已完成. Live unauthenticated projection stays 403 `IDENTITY_RUNTIME_NOT_BOUND`.

| id | page_uid | C / A / G | production execute | strict_status |
|---|---|---|---|---|
| INV-WB01 | workspace:WB-01 | 14 SECTION_OPEN / 0 action_uid / 3 (`PAGE-READ` `SECTION-READ` `CONTROL-READ`) | local SQL projection bind; PAGE VIEW only | 待修正 |
| INV-CORE | CORE-01 | 50 / 34 / 26 | `executeCore` SQL: PROJECT-CREATE VALIDATE CONFIRM TOPIC THREAD MESSAGE STORY MOTHER-LOCK CORE-REVIEW BLUEPRINT-* CHILD-LOCK CANONICAL-SCRIPT; CANDIDATE-* DNA-LOCK default throw | 待修正 |
| INV-ASSET | ASSET-01 | 85 / 44 / 21 freeze; unique `ASSET-01-GATE-*` in bindings = 20 | bind + finding/scorecard/decide/handoff/layer/correction SQL; execute/retry/patch throw | 待修正 |
| INV-VIDEO | VIDEO-01 | 85 / 34 / 16 freeze; unique `VIDEO_ACTION_GATE` = 13 | bind + finding/scorecard/decide/handoff/correction SQL; execute/retry throw | 待修正 |
| INV-EDIT | EDIT-01 | 160 / 124 / 25 | client HTTP invoker bound; voice SQL; draft ABSENT; startVoice throw | 待修正 |
| INV-QA | QA-01 | 87 / 32 / 19 freeze; unique `QA-01-GATE-*` in bindings = 18 | start/recheck/pass/fail/release/correction SQL; finding AUTHORITY_GAP; aux CONTROLLED_TEST | 待修正 |
| INV-DB | admin:DB-01 | 49 / 15 / 9 | ENTITY-LIST SCHEMA MIGRATION SQL; TRACE INTEGRITY AUDIT empty arrays | 待修正 |
| INV-STR-WS | workspace:STR-01 | 57 / 11 / 11 contract; unique gates in bindings = 10 | `sendConversationMessage` SQL insert; `configureStrategyDecisionRuntime` execute throw; candidate compare unbound | 未完成 |
| INV-INFO | workspace:INFO-01 | 66 / 17 / 10 | `refreshProjection` stub `{refreshed:true}`; `searchProjection` SQL; export/adopt `INFO_WRITE_RUNTIME_NOT_MATERIALIZED` | 未完成 |
| INV-SYS | admin:SYS-01 | 12 / 12 / 6 named; 4 controls `gate_uid=null` | `configureSystemLifecycleRuntime` execute throw | 未完成 |
| INV-IAM | admin:IAM-01 | 14 / 13 / 5 | `searchProjection` SQL only of 9 ports; other ops `IAM01_WRITE_RUNTIME_NOT_MATERIALIZED` | 未完成 |
| INV-DEV | admin:DEV-01 | 22 / 22 / 15 | outreach `/v1/outreach/*` ABSENT; semantics AUTHORITY_GAP | 未完成 |
| INV-SOC | admin:SOC-01 | 67 / 21 / 14 | `refreshProjection` stub; `searchProjection` channel_accounts; rest `PROVIDER_GATEWAY_NOT_MATERIALIZED` | 未完成 |
| INV-ERP | admin:ERP-01 | 42 / 21 / 10 | refresh stub; `getERPSyncStatus` `getERPFailure` snapshot/factpack/guardrails/forecast SQL; rest throw | 待修正 |
| INV-AIAPI | admin:AIAPI-01 | encoding has no `control_uid`; UI ops disabled `REMAP_REQUIRED_NOT_EXECUTED` | no effectful production port | 未完成 |
| INV-SG02 | admin:SG-02 | expected_controls 11; allowed_action_ids CONFIGURE APPROVE NAV-OPEN | production governance bind incomplete; ops reuse IAM configure/approve | 未完成 |
| INV-STR-AD | admin:STR-01 | encoding has no `control_uid`; 5 Current Views; remap NOT_EXECUTED | client adapter bound; source remap AUTHORITY_GAP | 未完成 |
| INV-KB | admin:KB-01 | 27 / 21 / 17 construction evidence; 19 `KNOWLEDGE_OPERATIONS` | `searchKnowledge` `getCitation` `createKnowledgeSource` `updateKnowledgeSource` SQL; pause/resume/retire/drafts/acquisition throw | 待修正 |

Inventory rule: freeze C/A/G kept when contract constant matches. Unique `gate_uid` from bindings that differs from freeze is 待修正 count, not production complete.

Exact Current Authority gates missing from production control/action maps (present in YAML / `*_GATE_UIDS`; fail-closed, not invented). Generator for `DO NOT HAND-EDIT` bindings is absent from this repo.

| id | authority gate | YAML control/action bind | code map | strict_status |
|---|---|---|---|---|
| GATE-ASSET-LAYER-ELIGIBLE | `ASSET-01-GATE-LAYER-ELIGIBLE` | catalog only; 0 control, 0 action; layer mutations use `ASSET-01-GATE-LAYER-WRITE` | in `ASSET_GATE_UIDS`; production `emptyAsset.gate_state` `false`; visual still `===true`; CONTROLLED_TEST may set true; GENERATED bindings unchanged | 已修正 |
| GATE-VIDEO-ASSET-BIND | `VIDEO-01-GATE-ASSET-BIND` | controls `VIDEO-01-FLD-ASSET-REFS` / `VIDEO-01-FLD-FILENAME-CHECKSUM` + `VIDEO-01-ACT-NOOP-VIEW` | `VIDGO_CONTROL_GATE` maps those two readonly controls; `VIDEO_ACTION_GATE` `NOOP-VIEW` stays `VIDEO-01-GATE-PAGE`; execute unwired | 已修正 |
| GATE-VIDEO-INSTRUCTION | `VIDEO-01-GATE-INSTRUCTION` | catalog only; `VIDEO-01-FLD-INSTRUCTION` YAML gate is `VIDEO-01-GATE-PAGE`; 0 action | in `VIDEO_GATE_UIDS`; production `emptyVideo.gate_state` `false`; not in `VIDEO_ACTION_GATE` | 已修正 |
| GATE-VIDEO-ROUTE | `VIDEO-01-GATE-ROUTE` | catalog only; 0 control, 0 action | in `VIDEO_GATE_UIDS`; production `emptyVideo.gate_state` `false`; not in `VIDEO_ACTION_GATE` | 已修正 |
| GATE-QA-CONTEXT | `QA-01-GATE-CONTEXT` | catalog only; `QA-01-ACT-CONTEXT-SET` and context fields use `QA-01-GATE-PAGE`; start uses `QA-01-GATE-START` | in `QA_GATE_UIDS`; production empty/read `gate_state` `false`; client empty/clear keeps `false`; GENERATED bindings unchanged | 已修正 |
| GATE-STR-MULTI | `STR-01-GATE-MULTI` | catalog only; `STR-01-TGL-MODE` YAML gate is `STR-01-GATE-TOPIC` | in `STRATEGY_GATE_UIDS`; production empty/read `gate_state` `false`; visual MULTI_AI extra-check; GENERATED bindings unchanged | 已修正 |

Map write rule: do not hand-edit GENERATED bindings; do not assign a catalog-only gate onto a control/action the YAML does not name. Option 2 applied: `VIDEO_CONTROL_GATE` from YAML first-occurrence control rows; VideoVisual readonly `data-gate-uid` uses it; `VIDEO_ACTION_GATE` unchanged; execute remains unwired. Catalog-only remainder: `ASSET_GATE_UIDS` / `VIDEO_GATE_UIDS` / `QA_GATE_UIDS` plus production `gate_state` keys written `false`.

## Runtime configure ports

| id | configure* | production bind site | strict_status |
|---|---|---|---|
| RT-NEON | `bindProductionNeonRuntime` | `instrumentation.ts` | 已完成 in local code; live SHA unverified |
| RT-WB01 | `configureUiProjectionRuntime` / `configureDashboardRuntime` | `wb01ProjectionRuntime.ts` | 已完成 local; live 待修正 |
| RT-CORE | `configureCoreRuntime` | `identityPageCommandRuntime.ts` | 待修正 partial; CANDIDATE/DNA-LOCK throw |
| RT-DB | `configureDbReadModelRuntime` | same | 待修正 partial |
| RT-IAM | `configureIamRuntime` | same | 未完成 writes |
| RT-INFO | `configureInfoCommandRuntime` | same | 未完成 writes |
| RT-DEPT | `configureDepartmentOperationRuntime` | finding/scorecard/handoff/decide/correction SQL; execute/retry throw | 待修正 |
| RT-QA | `configureQaRuntime` | start/recheck/pass/fail/release SQL; QA finding AUTHORITY_GAP; correction via department SQL | 待修正 |
| RT-KB | `configureKnowledgeRuntime` | search/citation/create/save SQL; pause/resume/retire/drafts throw | 待修正 |
| RT-CONV | `configureConversationRuntime` | send message only | 待修正 |
| RT-STRDEC | `configureStrategyDecisionRuntime` | execute throw | 未完成 |
| RT-SOC | `configureSocCommandRuntime` | refresh/search only | 待修正 |
| RT-ERP | `configureErpCommandRuntime` | refresh/status/snapshot only | 待修正 |
| RT-SYS | `configureSystemLifecycleRuntime` | execute throw | 未完成 |
| RT-ASSET | `configureAssetRuntime` | bind + finding/scorecard/decide/handoff/layer/correction SQL; execute/retry/patch throw | 待修正 |
| RT-VIDEO | `configureVideoRuntime` | bind + finding/scorecard/decide/handoff/correction SQL; execute/retry throw | 待修正 |
| RT-EDIT-A | `configureEditActionRuntime` | server ABSENT; client `configureEditActionInvoker` HTTP bound | 待修正 |
| RT-EDIT-V | `configureEditVoiceRuntime` | bind + create/read/state SQL; startVoice throw | 待修正 |
| RT-EDIT-D | `configureEditDraftCommandRuntime` | production ABSENT | 未完成 |
| RT-QA-ACT | `configureQaActionRuntime` | production ABSENT; QA buttons use `qaClientPort` HTTP | 未完成 |
| RT-QA-MAN | `configureQaManualReviewRuntime` | CONTROLLED_TEST only | 未完成 |
| RT-QA-AUTO | `configureQaAutoOrchestrator` | CONTROLLED_TEST only | 未完成 |
| RT-CAND-D | `configureCandidateDecisionRuntime` | production ABSENT | 未完成 |
| RT-CAND-C | `configureCandidateCompareRuntime` | production ABSENT | 未完成 |

## Dependencies and related programs

| id | item | strict_status | note |
|---|---|---|---|
| DEP-NEON-PKG | `@neondatabase/serverless` | 已完成 local | gap report names the package present |
| DEP-ENV | `DATABASE_URL` / `UNPOOLED` / `NEON_PROJECT_ID` | 已完成 named; secrets not in git | live bind unverified at this SHA |
| DEP-MIGRATION | 0001-0015 | 待修正 | wild-wave COMPLETE not proven on live SHA |
| DEP-SMOKE | `post-deploy-smoke.mjs` | 已修正 | 403 regex now accepts `IDENTITY_RUNTIME_NOT_BOUND`; not deployed |
| DEP-SECRET | `VERCEL_AUTOMATION_BYPASS_SECRET` | 未完成 | user must supply |
| DOC-PROGRESS | construction progress YAML | 已修正 | 2026-09-08 aligned bootstrap facts; COMPLETE remains false |
| DOC-GAP | runtime gap report | 已修正 | 2026-09-08 aligned local register/driver facts; production-ready claim remains false |
| DOC-JSON | readiness JSON HEAD `e001d7bd` | 待修正 | historical evidence kept; superseded by freeze directory |
| E2E-DB | real DB E2E | 未完成 | |
| E2E-EXT | ERP/SOC/crawler/AI/DEV outreach | 未完成 | class E |

## Counts after inventory write (snapshot file unchanged)

- 完整: 0
- 已完成: visual shells + local neon package + local register call sites + CONTROLLED_TEST/CI on later SHAs
- 未完成: asset/video/edit/qa-aux/candidate/AIAPI effectful/DEV routes/external E2E/secret; most page execute paths
- 待修正: live SHA, ready=200 extra fields, identity reason_code vs ready claim, stale readiness JSON; unique GENERATED binding counts still 20/13/18/10 vs freeze G
- 已修正: construction progress YAML bootstrap claims; runtime gap report empty-register claims; 18-page C/A/G vs execute inventory; smoke 403 regex for `IDENTITY_RUNTIME_NOT_BOUND`; VIDEO readonly `VIDEO_CONTROL_GATE` includes `VIDEO-01-GATE-ASSET-BIND`; catalog-only LAYER-ELIGIBLE / INSTRUCTION / ROUTE / CONTEXT / MULTI fail-closed in `*_GATE_UIDS` and production `gate_state`
