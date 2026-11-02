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
