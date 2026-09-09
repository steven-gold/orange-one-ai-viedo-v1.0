# Requirements Document

## Introduction

The construction team needs a strict, line-level audit surface that records the 2026-09-08 live deployment freeze, constrains repair before the next authorized deployment, and later monitors completeness of every registered page, function, dependency, and related program. The surface reuses Current Authority and existing construction evidence. The surface does not create a second ACPOS product system.

## Glossary

- **System**: ACPOS website construction audit record and later monitor surface.
- **Current Authority**: Files listed in `authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml`.
- **Frozen snapshot**: `FROZEN-DEPLOYED-AUDIT-SNAPSHOT.md` in this directory.
- **Construction progress file**: `docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml`.
- **Strict status**: one of 完整, 已完成, 未完成, 待修正, 已修正.
- **Product page**: a registered `page_uid` with a registered navigation route.
- **Monitor surface**: GitHub Issue plus this specs directory now; later an evidence feed into existing SYS-01 audit composition if Authority already names that composition.

## Requirements

### Requirement 1

**User Story:** AS construction owner, I want the 2026-09-08 live audit frozen in this repository, so that later repair can be compared against an unchanged deployed record.

#### Acceptance Criteria

1. WHEN the freeze is written, THE System SHALL store the public alias URL, protected deployment URL, live `release_sha`, local `new` HEAD, and `origin/main` SHA in the frozen snapshot.
2. WHEN a live HTTP probe was taken, THE System SHALL record HTTP status and `reason_code` for `/health`, `/health/ready`, identity session, dashboard read-model, and each registered UI projection.
3. IF a later repair changes code, THE System SHALL leave the frozen snapshot text unchanged except by an explicit new freeze revision.

### Requirement 2

**User Story:** AS construction owner, I want processing-before limits written before repair, so that deploy and second-system creation stay blocked.

#### Acceptance Criteria

1. WHILE this freeze window is active, THE System SHALL treat deploy, republish, and Vercel retarget as blocked until the user authorizes one deployment.
2. WHEN a proposed change would add a product route, nav item, or parallel page authority, THE System SHALL keep that change blocked and report an authority gap.
3. WHEN CONTROLLED_TEST, HTML 200, or CI success is observed, THE System SHALL keep production-ready claims blocked.

### Requirement 3

**User Story:** AS construction owner, I want every registered page, function, dependency, and related program scored with strict status, so that incomplete work cannot hide behind a pass.

#### Acceptance Criteria

1. WHEN an audit row is recorded, THE System SHALL assign exactly one strict status from 完整, 已完成, 未完成, 待修正, 已修正.
2. WHEN a row claims 完整, THE System SHALL require matching Current Authority, repository implementation, validation evidence, and live response for the same SHA.
3. IF authority, code, evidence, or live response disagree, THE System SHALL assign 待修正.
4. IF a required binding, route, or execute path is absent, THE System SHALL assign 未完成.

### Requirement 4

**User Story:** AS construction owner, I want a real-time construction audit monitor, so that I can watch completeness while files are repaired.

#### Acceptance Criteria

1. WHEN the monitor is requested, THE System SHALL reuse Current Authority, the construction progress file, and this specs directory as the source records.
2. WHEN a new product page or nav route would be required for the monitor, THE System SHALL keep the new page blocked and keep the GitHub Issue plus this directory as the current monitor surface.
3. WHILE repair is in progress, THE System SHALL update status rows from repository evidence without treating CONTROLLED_TEST as production.

### Requirement 5

**User Story:** AS construction owner, I want the same audit recorded independently on GitHub, so that the freeze is visible outside the working tree.

#### Acceptance Criteria

1. WHEN the freeze is accepted, THE System SHALL create one GitHub Issue that cites this specs directory.
2. WHEN the Issue is created, THE System SHALL keep Current Authority, navigation, and product routes unchanged.
3. WHILE the Issue exists, THE System SHALL treat the Issue as a mirror record, not as a second construction authority.

### Requirement 6

**User Story:** AS construction owner, I want one later deployment after program files are complete, so that live SHA and git SHA match.

#### Acceptance Criteria

1. WHEN program-file repair is still open, THE System SHALL keep deployment blocked.
2. WHEN the user authorizes one deployment, THE System SHALL require the deployed SHA to exist in git.
3. IF live `/health` SHA is absent from the repository, THE System SHALL keep that live target classified 待修正.
