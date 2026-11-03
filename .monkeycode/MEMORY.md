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
