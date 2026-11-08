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

[Project Knowledge Summary]
- Date: 2026-11-02
- Context: Discovered by Agent while verifying asset-page gap fixes on local dev server (port 3000)
- Category: Environment Configuration
- Instructions:
  - Local dev DB is an in-memory/file SQLite fallback (no DATABASE_URL in sandbox). All seeded data (AIAPI credential, projects) evaporates whenever the dev server process is killed.
  - After restarting the dev server, re-seed the mock LLM credential before any AI-dependent probe: run `/tmp/opencode/seed_cred3.mjs` (creates chat profile with `secret:"local-fake-key"`, field names baseUrl/endpointPath/modelId/capabilityType/secret) and `/tmp/opencode/seed_cred4.mjs` (creates correction profile). Old `seed_cred.mjs` uses outdated field names and fails with 409 AIAPI_CREDENTIAL_REQUIRED.
  - mock_llm must be running on 127.0.0.1:4571 (`node /tmp/opencode/mock_llm.mjs`).
  - Next.js dev uses Turbopack; editing server files under src/server while the server runs can leave stale module state - if edits appear not to take effect, restart the dev server (do not delete .next; move it aside instead).

[Project Knowledge Summary]
- Date: 2026-11-02
- Context: Discovered by Agent while debugging asset read model returning all-null after server restart
- Category: Troubleshooting & Debugging
- Instructions:
  - persistListAssetFields -> overlayCoreNames previously nulled the whole asset read model when upstream core bindings were absent; it now returns workspace state as-is. If a page "cannot be written", first check whether the read model overlay is masking persisted values (query the sqlite file directly at /tmp/acpos-sandbox-workbench.sqlite to distinguish write failure from display masking).
  - Single-episode prompts (e.g. 第1集) take a non-batched generation path that can truncate replies; use batched prompts (第7集 or higher) for reliable conversation-file chains in probes.

[Project Knowledge Summary]
- Date: 2026-11-02
- Context: Discovered by Agent while running asset gap probes
- Category: Testing Methods
- Instructions:
  - Asset gap probe: `node /tmp/opencode/probe_asset_gaps.mjs` (43 assertions, needs dev server + mock_llm + seeded credentials). Live variant: probe_asset_live.mjs (python-generated from it, pins IPv4 64.29.17.67, timestamped topic name 素材補齊線上-HHMMSS).
  - Probe relies on conversation-file chain: CORE-01-BTN-NEW-THREAD + CORE-01-BTN-SEND with a 劇本 prompt (scene heading 第N集) -> CANDIDATE-ACCEPT injects scenes into CANONICAL-PROJECTION -> manifest items S1...

[Project Knowledge Summary]
- Date: 2026-11-02
- Context: Discovered by Agent while diagnosing live FLD-ROUTE=null despite successful core SEND (route-snapshot-empty trace evidence)
- Category: Troubleshooting & Debugging
- Instructions:
  - AIAPI routing is EXACT capability match (aiapi01.txt:459 silent downgrade forbidden). The page->capability mapping lives in AI_CAPABILITY_BY_PAGE (src/server/ai/llmClient.ts); all four pages map to "chat". Never invent capability names absent from aiapi01.txt (freeze rule line 723) - production profile registry only registers real catalog types (chat/video-generation/image-generation/audio-generation/embedding/operation...).
  - Asset route snapshot writes FLD-TRACE on empty/fail (`route-snapshot-empty:<control>:<capability>:<action>`) and FLD-ROUTE on success; read FLD-TRACE first when AI-dependent asset behavior fails on an environment.
  - Verify production deployment freshness via a code-format fingerprint (e.g. TRACE string format) + a fresh action write, since persisted field values keep old formats until a new write occurs.
  - A failing commit (TS syntax error) pushed to main wedges Vercel auto-deploy at last-good for 15+ min; pushing a follow-up real commit retriggers the pipeline.
  - Probe correction-flow assertion checks the action response envelope (kind/status), which can pass on stale CSC data; verify ASSET-01-FLD-JOB and CSC body freshness when validating generation success.

[Project Knowledge Summary]
- Date: 2026-11-03
- Context: Discovered by Agent during asset audio-type conditionalization round (type derivation + live probes)
- Category: Troubleshooting & Debugging
- Instructions:
  - Asset type derivation (assetGateContract.ts itemTypeFromRequirement): explicit [TAG] labels win; when absent, semantic markers in scene beats text (SFX/音效, 旁白/配音, 配樂, 特效, 字幕) decide by frequency with fixed priority SFX>VOICE>MUSIC>VFX>TEXT; views.ASSET items merge structure.scenes beats by ref before derivation - check both paths when type comes out SCENE unexpectedly.
  - mock_llm on Node 22: IncomingMessage autoDestroy makes req.destroyed true right after body consumption - streaming loop must test res.destroyed||res.writableEnded only, otherwise SSE streams cut after first chunk.
  - Next dev request.signal aborts once response starts streaming, killing upstream LLM fetch after first chunk; the four action routes pass undefined instead (cancellation is carried by contract STOPPED state).
  - FLD-ERRORS / read-model control visibility is stage-filtered: error codes written during READY/WAIT_CONFIRMATION may read undefined after stage moves to CONFIRMED - assert via FLD-GATES snapshot (gate state/reason) instead when late in the chain.
  - CONFIRM control action uid is ASSET-01-ACT-CANDIDATE-CONFIRM (not ASSET-01-ACT-CONFIRM); LOCK uses ASSET-01-ACT-VERSION-LOCK.
  - Live probe script truth: real LLM puts SFX semantics in beat dialogue rather than scene titles, so probes must not assume fixed scene headings; bind image-compatible items by manifest type filter (exclude VOICE/MUSIC/SFX/REFERENCE) before Layer/Patch assertions.

[Project Knowledge Summary]
- Date: 2026-11-03
- Context: Discovered by Agent while closing the scorecard review-semantics gap (weighted total + three-state overall + strict confirm)
- Category: Testing Methods
- Instructions:
  - Asset scorecard overall is three-state: hard block fail -> BLOCKED, any dimension score null -> REVIEW_PENDING, all scored -> PASS only when weighted Total>=95 (spec docasset.txt:2960). Probes must accept REVIEW_PENDING for EVALUATE assertions; CONFIRMED / locked / handoff-sent full-chain assertions are unreachable until real reviewer scores exist (no provider artifacts in this environment) - assert CONFIRM fail-closed with GATE-CONFIRM reason "reviewer scores pending: ..." instead.
  - PATCH-ACCEPT already writes FLD-OUTPUT-ID=ASSET-v1, so CONFIRM interception evidence is ASSET-01-BTN-CONFIRM state + gate reason, never FLD-OUTPUT-ID.

[Project Knowledge Summary]
- Date: 2026-11-03
- Context: Discovered by Agent while diagnosing intermittent ECONNRESET to the Vercel deployment from sandbox Node scripts
- Category: Environment Configuration
- Instructions:
  - Sandbox DNS is poisoned for the Vercel domain: orange-one-acpos-test.vercel.app may resolve to 128.242.240.155 / 2a03:2880::/32 (Meta IP space) causing ECONNRESET/TLS drops, while curl --resolve to 64.29.17.67 works. Fixed by pinning `64.29.17.67 orange-one-acpos-test.vercel.app` in /etc/hosts; node fetch ignores the `agent` option (undici dispatcher required otherwise), so probes rely on this hosts entry.

[Project Knowledge Summary]
- Date: 2026-11-03
- Context: Discovered by Agent while filling the VIDEO-01 production-data gap (videoGateContract.ts + action/persist integration)
- Category: Build Methods
- Instructions:
  - VIDEO-01 mirrors the asset scorecard pattern: src/lib/videoGateContract.ts holds QCP_VIDEO_PROFILE (9 dims, weights 15/20/10/10/10/10/10/10/5, RIGHTS hard block weight 5), buildVideoScorecard (three-state overall, weighted_total), buildVideoGates (13 gates), deriveVideoPageState, videoGateContextFrom, EXACT_VIDEO_HANDOFF_MANIFEST (ten-field contract); videoHashOf is the shared FNV-1a helper for checksum/script-hash/fingerprint/manifest-id.
  - Video EVALUATE requires a candidate (FLD-OUTPUT-VERSION / FLD-CANDIDATE-VERSION) or it fails closed with no scorecard - spec places EVALUATION gate after CANDIDATE; no video provider exists in this environment, so full-chain LOCK/HANDOFF assertions need a seeded candidate (local: node:sqlite INSERT into ghsn_video_field_projection; live: unavailable - assert the fail-closed set instead).
  - Video page-state precedence: handoff > locked > confirmed > correction-open > scorecard(WAIT_CONFIRMATION/ERROR) > executing-running-without-candidate > candidate > ready; the live page legitimately rests in EXECUTING after FLOW-START because no provider completion callback exists.
  - Video page has no FLD-GATES container (unlike asset): gate status is carried by FLD-PAGE-STATE + FLD-DISABLED-REASON (overlay-derived) and FLD-ERROR (action-written); EVALUATE/FLOW-START clear stale FLD-ERROR.
  - Video spec source is /tmp/opencode/all_0c2c0a.txt (ACPOS-AI-05 mother design, 10503 lines); confirm contract POST /v1/video-runtime-runs/{runId}/candidates/{videoOutputVersionId}/confirm; no VIDEO-01-ERR-* literals exist in spec - write plain gate reasons into FLD-ERROR instead of inventing error codes.
  - Live vs local probe asymmetry: probes that seed fields via node:sqlite only work against the local dev DB (/tmp/acpos-sandbox-workbench.sqlite); the Vercel deployment reads its own database, so live probes must assert the fail-closed semantics reachable through HTTP actions alone.

[Project Knowledge Summary]
- Date: 2026-11-03
- Context: Discovered by Agent while implementing the QCP approval registry (QA-SYNC-01 three-element compliance)
- Category: Build Methods
- Instructions:
  - src/lib/qcpRegistry.ts is the single source for all QCP profiles: six canonical rows (QCP-CORE-BASELINE-V1 8 dims, QCP-ASSET-IMAGE-V1 9, QCP-ASSET-AUDIO-V1 8, QCP-VIDEO-BASELINE-V1 9, QCP-EDIT-FINAL-V1 12, QCP-QA-FINAL-OUTPUT-V1 17; threshold 95 each) plus QGP_POLICY_VERSION = "QGP-V1". assetGateContract/videoGateContract resolve their profile constants via resolveApprovedCriteria(uid) - never re-declare dimension arrays inline.
  - Scorecards carry the QA-SYNC-01 triple: exact profile UID + criteria_version (VIDEO-CRITERIA-*/ASSET-CRITERIA-*) + quality_gate_policy_version (QGP-V1). New pages adding scorecards must include all three fields.
  - CORE 8-dim and QA 17-dim dimension definitions are absent from the spec (counts only); registry stores them with dimensions: null (metadata rows, authority pending). EDIT 12-dim names come from the spec list; weights are implementation authority (spec says weights are new authority and does not enumerate them).
  - Verify QGP field writes with /tmp/opencode/verify_qgp.mjs (seeds candidate, EVALUATE, waits 9s, asserts scorecard triple, cleans up). Video projection table is ghsn_video_field_projection(control_uid, value_text) - value column name is value_text, and /api/video read model is model.fields[].controlUid/value.

[Project Knowledge Summary]
- Date: 2026-11-03
- Context: Discovered by Agent while wiring the video-generation provider and the asset display-delivery filter
- Category: Build Methods
- Instructions:
  - Video execute phase runs through the registered "video-generation" capability (capabilityType catalog in src/server/aiapi/surface.ts; spec all_0c2c0a.txt:552 "registered capability through AI03" - TEXT_TO_VIDEO literal is not in the catalog). llmClient.generateVideoExecution() + applyAction fillVideoExecution; local testing needs seed_cred5.mjs (mock-video profile, capabilityType video-generation, mock_llm branch "影片生成執行").
  - Asset page project/topic chips implement the display-delivery mode (docasset.txt:1706): a project is listed only when its CORE upstream state has PROJECT-CONFIRM/PROJECT-LOCK plus a topic - current project via live CORE fields, others via CORE-01-FLD-PROJECT-SNAPSHOTS; topic list follows the selected project's snapshot. Filter criteria deliberately match inbound ready (fail-closed parity): listed = selectable-ready. NOTE: local dev projects all have full lock chains, so the filter's exclusion path only shows on the live deployment (e.g. 天堂 excluded).
  - CORE project snapshots carry per-project state including CORE-01-BTN-PROJECT-LOCK and CORE-01-CTL-TOPIC; global fields like PROJECT-CONFIRM reflect only the current project, so per-project judgement MUST go through snapshots for non-current projects.
  - A CORE-01-FLD-CANONICAL-FILENAME is assigned by assetCanonicalFilenameOf() at CANDIDATE-CONFIRM (deterministic ACPOS-ASSET-{hash}); before confirm GATE-NAMING reads "canonical filename pending" which is the correct pre-reservation state.

[Project Knowledge Summary]
- Date: 2026-11-04
- Context: Discovered by Agent while implementing the CORE topic-group snapshot mode (Canonical Production Script Contract)
- Category: Build Methods
- Instructions:
  - Topic-bound state lives in src/lib/coreTopicSnapshot.ts (CORE-01-FLD-TOPIC-SNAPSHOTS, key "project/topic", cap 40) - mirror of coreProjectSnapshot.ts. CORE_TOPIC_SNAPSHOT_UIDS covers CANONICAL-SCRIPT, CANDIDATE group, TOPIC-SCOPE, EVALUATION, VERSION-STATE, LOCK-REVIEW, STRUCTURED-DECISION, HUMAN-DECISION, LIFECYCLE-STAGE, PACKAGE, CHANGE-REQUEST, RETURN-MODIFY, CORE-REVIEW.
  - TOPIC-SELECT in coreActionPreview.ts: same-topic select is a no-op; switching snapshots the outgoing topic (captureTopicSnapshot) and restores the incoming one (restoreTopicPatch). A fresh topic (no snapshot) starts clean and gets a Continuity Bridge line in TOPIC-SCOPE: "topic｜前序專題：previous-topic"; a restored topic keeps its own snapshotted scope. TOPIC-DELETE drops that topic's snapshot; PROJECT-RENAME/DROP rename/drop all topic snapshots of the project.
  - API probe probe_topic_switch.mjs: /api/core/action body field is nextValue (NOT value); read model shape is top-level json.fields[]; local second-topic creation falls back to node:sqlite write because API TOPIC-CREATE correctly fails closed without LIFECYCLE-STAGE=PROJECT_LOCKED (mother lock required).
  - coreActionPreview.test.ts legacy assertions were stale (compare/structured-decision now write JSON contracts, controls count 71); keep them aligned when controls change.

[Project Knowledge Summary]
- Date: 2026-11-04
- Context: Discovered by Agent while fixing the DEV-01 audit gaps against the FINAL_LOCKED spec (/tmp/opencode/dev01/)
- Category: Build Methods
- Instructions:
  - DEV-01 has exactly 22 authoritative visible controls; SEND-ONE and CANDIDATE-EDIT were invented controls (removed) - one-to-one sends and candidate edits have no registered operation, the correct paths are CAMPAIGN flow and CR-CREATE. The 6 TBL10 interactions (PROFILE-SAVE/SOURCE-MANAGE/SIGNAL-QUALIFY/IGNORE/CONTACT-UPSERT/OPPORTUNITY-STATE) stay off the visible denominator with authority pending; they are bound to the page baseline permission outreach.discovery.configure.
  - Per-action permissions: DEV_ACTION_PERMISSIONS in src/server/domain/dev.ts maps the 17 registered actions to TBL23 runtime_binding permissions (projection.search, outreach.directory.merge, projection.export, candidate.create/decide, core.change.create, outreach.batch.create/approve, outreach.send.dispatch, projection.refresh, ops.kill_switch); route /api/dev/action checks them via persistHasDevPermissions; seed.ts grants all DEV_ACCOUNT_PERMISSIONS to ACC-DEMO in the dev scope.
  - devActionPreview.ts fail() maps internal DEV_* codes to spec error uids (DEV_SPEC_ERROR_UIDS -> DEV-01-ERR-{SOURCE|CONNECTOR|IDENTITY|MERGE|MESSAGE-POLICY|SUPPRESSION|CAMPAIGN|DELIVERY|KILL|PARTIAL|UNDEFINED|AUTH}); unknown actionUid fails closed with DEV_ACTION_UNDEFINED + detail=actionUid (ERR-UNDEFINED semantics), never returns {}.
  - Campaign preview gate (TBL13): CAMPAIGN-CREATE writes previewed=false; CAMPAIGN-SEARCH records the operator preview (previewed=true on an open REVIEW campaign); CAMPAIGN-APPROVE recomputes searchAudienceProjection against campaign.audienceQuery and fails with DEV_CAMPAIGN_AUDIENCE_STALE on drift. applyDiscoveryCollection auto-registers every discovered signal into the company directory (operator directive 2026-11-05, supersedes the earlier human-qualify-only TBL11 reading); signals are consumed as QUALIFIED and COMPANY-DELETE is the operator's downstream exit with fail-closed reference integrity.
  - Candidate records carry history[] (version/status/at) appended on create/decide/change-request; policy is computed (suppression/active email) and CANDIDATE-DECIDE blocks on BLOCKED. UI stage-5 delivery policy renders a pending-authority dash (no STATE-DELIVERY-POLICY field exists); drawer is a fixed 520px side panel holding delivery history + merge details.
  - Regression probe: /tmp/opencode/probe_dev_fix.mjs (route 404 for invented actions, read-model control set, page markup). Test flow note: campaign blocks need CAMPAIGN-SEARCH after CAMPAIGN-CREATE now; store() helper in devActionPreview.test.ts has write(patch) for API-collected patches.

[Project Knowledge Summary]
- Date: 2026-11-04
- Context: Discovered by Agent while diagnosing the push/deploy outage (gnutls_handshake failures)
- Category: Troubleshooting & Debugging
- Instructions:
  - Sandbox outbound outage pattern: DNS resolves and TCP handshakes succeed to any host/port, but the first application-layer packet (TLS ClientHello, HTTP GET, SSH kex banner) is silently dropped or reset (curl 35/52/000, "kex_exchange_identification: Connection closed"). IPv6 unavailable; gateway 192.168.16.1 exposes no proxy ports (3128/8080/8888/1080/8118/9050 closed).
  - The outage is intermittent with short windows: apt (deb.debian.org) succeeded at one instant, all hosts blocked again a few minutes later. TCP port OPEN means nothing - probe with a real TLS request (git ls-remote origin) when polling for recovery.
  - Recovery workflow: high-frequency polling terminal (15s interval, git ls-remote as probe) that on success pushes HEAD:main + HEAD:261002-feat-deploy-home-shell, waits ~300s for the Vercel build, then runs /tmp/opencode/probe_live_verify.mjs (live /admin/dev control set, /api/dev read model, invented-action 404, core/assets/video APIs) with retries.
  - openssh-client was not preinstalled; apt-get install -y openssh-client is allowed and works in open windows. ssh:// and ssh over port 443 (ssh.github.com) provide no bypass - the interceptor cuts SSH banners too.

[Project Knowledge Summary]
- Date: 2026-11-05
- Context: Discovered by Agent after the sandbox reset restored outbound network and the deploy completed
- Category: Operations & Deployment
- Instructions:
  - The 2026-11-04 outbound outage ended via a sandbox reset (all terminals lost, clock jumped, network restored at 2026-11-05 11:25 UTC) - when an outage persists beyond hours, a platform reset resolves it; long-running terminals (poll loops, dev servers) must be re-created afterwards.
  - Live baseline is now fc73d826 (DEV-01 spec alignment + 23 authoritative controls + UX batch + send-flow preview/confirm). probe_live_verify.mjs expects read-model size 36 (23 controls + STATE fields) and the CAMPAIGN-REVIEW section; dev control-count assertions live in probe_company_delete.mjs (23/36).
  - UX corrections landed 2026-11-05: sticky error bar + busy bar, Stage2 live-filter (local query state) + clear-search buttons, CAMPAIGN-APPROVE disabled until previewed, EMAIL-DISPATCH confirm with recipient count, letter preview cards on stage 4/5. Stage4 audience search stays Enter-confirmed (authority-consistent preview for the approve drift check).
  - COMPANY-DELETE (DEV-01-BTN-COMPANY-DELETE -> DEV-01-ACT-COMPANY-DELETE) deletes workbench companies with fail-closed reference integrity: candidates/campaign recipients/merge preview references fail with DEV_COMPANY_IN_USE (err uid DEV-01-ERR-IDENTITY).

[Project Knowledge Summary]
- Date: 2026-11-05
- Context: Discovered by Agent while fixing the live "cells and text stuck together" layout bug
- Category: Troubleshooting & Debugging
- Instructions:
  - Visual verification stack: playwright + chromium installed globally (`npm install -g playwright && npx playwright install chromium --with-deps`); screenshot script /tmp/opencode/shot.mjs runs as `cd /tmp/opencode && [SHOT_BASE=...] [SHOT_STAGE=1-5] NODE_PATH=$(npm root -g) node shot.mjs`; default base http://localhost:3000, live base https://orange-one-acpos-test.vercel.app.
  - Local read-model seeding for layout tests: file-backed SQLite at /tmp/acpos-sandbox-workbench.sqlite, table ghsn_dev_field_projection(control_uid, value_text); company array control_uid is DEV-01-STATE-COMPANIES, signals is DEV-01-STATE-SIGNALS; JSON must use legal DevOpportunityState values (OPEN/QUALIFIED/CONTACTED/REPLIED/PROPOSAL/WON/LOST/SUPPRESSED) - an unknown state used to crash the whole page render.
  - Live layout bugs reproduce only with data: empty stages render clean; seed companies/signals before screenshotting. Directory identityValue holds full registration text (long), so table cells need minmax(0, Xfr) grid columns + single-line ellipsis + title tooltips (fix landed in 9964f061). translate() now falls back to entry.en then the key itself, so one bad key renders text instead of wiping the page.
  - Render-layer validation workflow for future UI changes: seed data -> screenshot stage locally -> fix -> tsc + tsx --test src/lib/devActionPreview.test.ts -> probes (probe_company_delete/probe_dev_fix/probe_topic_switch) -> commit/push -> sleep 150 -> probe_live_verify -> screenshot live stage.

[Project Knowledge Summary]
- Date: 2026-11-06
- Context: Discovered by Agent when the live site suddenly returned 503 on every DB-backed API mid-session
- Category: Troubleshooting & Debugging
- Instructions:
  - Live DB is Neon Postgres via DATABASE_URL; when /api/dev /api/core /api/assets /api/video all return 503 with code DATABASE_RUNTIME_NOT_BOUND and the message embeds "HTTP status 402 ... exceeded the quota", the Neon free-tier quota is exhausted - it is an account/billing issue, not a code bug. Verify deploy contents by grepping the deployed JS chunk for new control uids (page HTML only has 1 data-control-uid because the rest renders client-side after the DB binds).
  - Quota recovery is automatic (monthly reset) or manual (plan upgrade in Neon console); no redeploy needed. Do not attempt code-side workarounds.
  - dev control-count chain to update on every new authoritative control: DEV_VISIBLE_CONTROLS in src/server/domain/dev.ts + DEV_ACTION_PERMISSIONS + DEV_CONTROL_ACTIONS (all three must stay in sync - a truncated DEV_CONTROL_ACTIONS makes every page action 404 while tsc and unit tests still pass because they bypass knownDevAction), then devActionPreview.test.ts count assertion, probe_company_delete.mjs VISIBLE list + count, probe_live_verify.mjs count. As of d7b60055: 28 controls / 41 fields.
  - The /api/dev/action route takes nextValue (JSON-stringified payload string), not a payload object; a raw payload object is silently ignored and yields confusing REQUIRED errors.

[Project Knowledge Summary]
- Date: 2026-11-08
- Context: Discovered by Agent while wiring the EDIT-01 client timeline state machine (c68e43a1)
- Category: Testing Methods
- Instructions:
  - EDIT-01 has a client-side timeline model at src/lib/editTimeline.ts (pure functions, 20 unit tests in editTimeline.test.ts, run via `NODE_PATH=$(npm root -g) tsx --test`); the UI owns the instance, server audit actions are unchanged (previewEditAction GATED fallback still writes the control's own uid).
  - Interactive probe /tmp/opencode/probe_edit_timeline.mjs (playwright, 11 assertions: drop/split/undo/seek/range/marker/play/version) must seek playhead back inside a clip before testing split - split is fail-closed outside clip bounds.
  - Icon buttons render Icon instead of label text; probe must read aria-label, not textContent.
  - Client-side UI states (timecode/playhead/clip fields) intentionally diverge from read-model fields; Field components for precision/inspector were switched to readonly to avoid GATED fallback polluting them.
  - editTimeline binary functions (seek/setTool/selectClip/patchSelected/stepFrame/toggleTrackFlag) need lambda wrapping when passed to run()/runOnly() helpers; a plain reference fails tsc.
  - Follow-up wave (47026b2d): media bin now parses inbound.mediaRefs (JSON/comma/single, sandbox seed "S2" is a valid exact ref so probe assertions must stay label-agnostic), voice takes render read-model value, SUB-TEXT is controlled (SUB-TEXT-EDIT needs non-empty nextValue), TIMECODE accepts input via timecodeToSeconds (range-checked hh<=23 mm/ss<=59 ff<=29), clips drag via dragClipTo (snapValue had a bug: snapping was skipped entirely when no range was set), keyboard shortcuts on window keydown skip INPUT/TEXTAREA targets. Probe note: read the timecode INPUT with inputValue(), not textContent; run probe assertions in an order that keeps the playhead inside the seeded clip.
  - Render/AUTO wave (33206152): EDIT-01-FLD-SOURCE-VERSION is DERIVED by the server projection from VIDEO-01-FLD-VIDEO-VERSION (edit-table writes are overwritten) — seed the video table to unblock the flow->stage->save->lock->render gate chain. React gotcha: never read a flag set inside a setRenderJobs updater from the synchronous code after it (updaters run async in batching); observe state transitions in a follow-up useEffect with a done-ref instead. Buttons render static translated labels only — assert gate outcomes via value fields (LBL-CURRENT-STAGE, FLD-SOURCE-VERSION, job list) or note elements, never button text.
  - Field-gap wave (380b44f6): QA gate contract (policy QA-GATE-V1, checks SCORE_BASELINE,CHECKSUM,RIGHTS, OPEN/BLOCKED, hardBlock) is DERIVED in resolveQaInbound and projected in persist.ts — QA action previews only read GATE-STATUS, never write it. EDIT voice provider/model are projected from assignedAiRouteSnapshot("chat") ("provider / model" split on "/" and "、"). Probe timing: dev-server hot recompiles make single post-act reads flaky — poll (loop with waitForTimeout) instead of fixed waits.
