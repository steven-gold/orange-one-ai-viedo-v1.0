import { chromium } from 'playwright';

const base = process.env.BASE_URL || 'http://127.0.0.1:3000';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
const failedRequests = [];
const seenControls = new Set();
const seenActions = new Set();

page.on('pageerror', (error) => pageErrors.push(String(error)));
page.on('requestfailed', (request) =>
  failedRequests.push(`${request.method()} ${request.url()} ${request.failure()?.errorText ?? ''}`),
);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function waitState(state) {
  await page
    .locator(`[data-page-uid="ASSET-01"][data-page-state="${state}"]`)
    .waitFor({ state: 'visible', timeout: 15000 });
}

async function waitIdle() {
  await page.waitForFunction(() => !document.querySelector('[data-busy-action]'), null, { timeout: 15000 });
}

async function snapshot(label) {
  const data = await page.locator('[data-control-id]').evaluateAll((nodes) =>
    nodes.map((node) => ({
      id: node.getAttribute('data-control-id'),
      action: node.getAttribute('data-action-uid'),
      gate: node.getAttribute('data-gate-uid'),
      permission: node.getAttribute('data-permission-uid'),
      reason: node.getAttribute('data-disabled-reason'),
    })),
  );
  for (const item of data) {
    if (item.id) seenControls.add(item.id);
    if (item.action) seenActions.add(item.action);
  }
  console.log(
    `SNAPSHOT ${label} controls=${new Set(data.map((item) => item.id)).size} actions=${new Set(data.map((item) => item.action).filter(Boolean)).size}`,
  );
}

async function click(id) {
  const locator = page.locator(`[data-control-id="${id}"]`).first();
  await locator.waitFor({ state: 'visible' });
  await locator.click();
  await waitIdle();
}

async function clickView(id, action, componentUid) {
  await click(id);
  const control = page.locator(`[data-control-id="${id}"]`).first();
  await page.waitForFunction(
    ({ controlId, actionUid }) => {
      const element = document.querySelector(`[data-control-id="${controlId}"]`);
      return (
        element?.getAttribute('data-action-uid') === actionUid &&
        element?.getAttribute('data-view-active') === 'true'
      );
    },
    { controlId: id, actionUid: action },
    { timeout: 5000 },
  );
  assert((await control.getAttribute('data-view-active')) === 'true', `${action} did not update view state`);
  const component = page.locator(`[data-component-uid="${componentUid}"]`).first();
  assert((await component.count()) === 1, `${action} target component ${componentUid} missing`);
  await page.waitForFunction(
    (uid) => {
      const element = document.querySelector(`[data-component-uid="${uid}"]`);
      if (!element) return false;
      const rect = element.getBoundingClientRect();
      return rect.bottom > 0 && rect.top < window.innerHeight;
    },
    componentUid,
    { timeout: 5000 },
  );
}

async function project() {
  return page.evaluate(async () => {
    const response = await fetch('/v1/ui-projections/ASSET-01', { cache: 'no-store' });
    return { status: response.status, body: await response.json() };
  });
}

async function waitProjection(predicate) {
  await page.waitForFunction(
    async (source) => {
      const response = await fetch('/v1/ui-projections/ASSET-01', { cache: 'no-store' });
      if (!response.ok) return false;
      const projection = await response.json();
      return Function('p', `return (${source})(p)`)(projection);
    },
    predicate.toString(),
    { timeout: 15000 },
  );
}

await page.goto(`${base}/assets`, { waitUntil: 'networkidle' });
await waitState('READY');
await page.waitForFunction(
  () => document.querySelector('[data-control-id="ASSET-01-CTL-PROJECT"]')?.value,
);
assert(
  (await page.locator('[data-page-uid="ASSET-01"]').getAttribute('data-registry-valid')) === 'true',
  'registry invalid',
);
assert(
  (await page.locator('[data-section-id="ASSET-01-SEC-06"] [data-control-id]').count()) === 0,
  'correction controls rendered before Modify',
);
assert(
  (await page.locator('[data-section-id="ASSET-01-SEC-07"] [data-control-id]').count()) === 0,
  'layer controls rendered before image candidate',
);
await snapshot('READY');

// Context/local controls.
await page.locator('[data-control-id="ASSET-01-CTL-MODE"] button').nth(1).click();
await page.locator('[data-control-id="ASSET-01-CTL-MODE"] button').nth(0).click();
await page.locator('[data-control-id="ASSET-01-FLD-SEARCH"]').fill('Character');
await page.locator('[data-control-id="ASSET-01-CTL-FILTER"]').selectOption('ALL');
await page.locator('[data-control-id="ASSET-01-LST-ASSET"] button').first().click();
await clickView('ASSET-01-BTN-BLUEPRINT', 'ASSET-01-ACT-BLUEPRINT-VIEW', 'ASSET-01-CMP-BINDING');
await clickView('ASSET-01-BTN-SCRIPT', 'ASSET-01-ACT-SCRIPT-VIEW', 'ASSET-01-CMP-SCRIPT');

// Reuse First / Generate Missing -> candidate through UI -> route -> runtime -> projection.
await click('ASSET-01-BTN-EXECUTE');
await waitState('CANDIDATE_OUTPUT');
await page.locator('[data-asset-version-ref]').first().waitFor({ state: 'visible' });
assert(
  (await page.locator('[data-control-id="ASSET-01-FLD-PROVIDER"] strong').textContent())?.includes(
    'SIMULATED_EXTERNAL',
  ),
  'provider simulation not labeled',
);
assert(
  (await page.locator('[data-section-id="ASSET-01-SEC-07"] [data-control-id]').count()) === 13,
  'image layer/patch controls not materialized',
);
await snapshot('CANDIDATE');

// Preview controls.
await click('ASSET-01-BTN-SINGLE');
await click('ASSET-01-BTN-ZOOM-IN');
await click('ASSET-01-BTN-ZOOM-OUT');
await click('ASSET-01-BTN-FIT');
await click('ASSET-01-BTN-REFERENCE');

// Versioned layer document and mutations.
await click('ASSET-01-BTN-LAYER-DOC-CREATE');
await waitProjection((projection) => Boolean(projection.layer_document_id));
await click('ASSET-01-BTN-LAYER-DOC-UPDATE');
await click('ASSET-01-BTN-LAYER-ADD');
await waitProjection((projection) => Boolean(projection.layer_id));
await click('ASSET-01-BTN-LAYER-DUPLICATE');
await click('ASSET-01-BTN-LAYER-REORDER');
await page.locator('[data-control-id="ASSET-01-CTL-LAYER-PROPERTIES"]').selectOption('OPACITY_100');
await waitIdle();
await page.locator('[data-control-id="ASSET-01-CTL-LAYER-MASK"]').selectOption('MASK_ENABLED');
await waitIdle();
await click('ASSET-01-BTN-LAYER-DELETE');
await click('ASSET-01-BTN-LAYER-ADD');

// Patch preview and accept creates a NEW exact Asset Version.
await click('ASSET-01-BTN-PATCH-CREATE');
await waitProjection((projection) => Boolean(projection.patch_id));
await click('ASSET-01-BTN-PATCH-PREVIEW');
await click('ASSET-01-BTN-PATCH-REVISE');
assert(
  (await page.locator('[data-control-id="ASSET-01-BTN-PATCH-REVISE"]').getAttribute('data-context-state-active')) ===
    'true',
  'patch revise did not update context state',
);
await click('ASSET-01-BTN-PATCH-ACCEPT');
await waitProjection((projection) => projection.candidate_versions.length >= 2);
await click('ASSET-01-BTN-AB');
await page.waitForFunction(
  () => Number(document.querySelector('[data-preview-count]')?.getAttribute('data-preview-count')) >= 2,
);

// Evaluate -> WAIT_CONFIRMATION and verify UI_ONLY view actions are not no-ops.
await click('ASSET-01-BTN-EVALUATE');
await waitState('WAIT_CONFIRMATION');
assert(
  (await page.locator('[data-control-id="ASSET-01-FLD-OVERALL"] strong').textContent()) === '98',
  'scorecard not projected',
);
await clickView('ASSET-01-BTN-RESULT-DETAIL', 'ASSET-01-ACT-RESULT-VIEW', 'ASSET-01-CMP-SCORE');
await clickView(
  'ASSET-01-BTN-VERSION-HISTORY',
  'ASSET-01-ACT-VERSION-HISTORY',
  'ASSET-01-CMP-VERSION',
);
await clickView('ASSET-01-BTN-RUNTIME-DETAIL', 'ASSET-01-ACT-RUNTIME-VIEW', 'ASSET-01-CMP-RUNTIME');

// Modify exposes correction controls. All 85 controls must have appeared across the real state sequence.
await click('ASSET-01-BTN-MODIFY');
assert(
  (await page.locator('[data-section-id="ASSET-01-SEC-06"] [data-control-id]').count()) === 5,
  'correction controls missing after Modify',
);
await snapshot('MODIFY');

// Finding action has no separate visual control; verify its registered route directly.
const finding = await page.evaluate(async () => {
  const response = await fetch('/v1/findings', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-asset-action-uid': 'ASSET-01-ACT-FINDING-CREATE',
    },
    body: JSON.stringify({
      test_metadata: {
        data_classification: 'TEST_ONLY',
        synthetic: true,
        test_dataset_id: 'TEST-ASSET-01',
        test_run_id: 'TEST-RUN-ASSET-01-E2E',
        created_for_validation: true,
        production_eligible: false,
      },
      issue_summary: 'E2E finding',
    }),
  });
  return { status: response.status, body: await response.json() };
});
assert(finding.status === 200, `finding route failed ${JSON.stringify(finding)}`);
seenActions.add('ASSET-01-ACT-FINDING-CREATE');

await page
  .locator('[data-control-id="ASSET-01-TXT-CORRECTION-REQUEST"]')
  .fill('只修正角色臉部一致性，其他內容保持不變');
await click('ASSET-01-BTN-CORRECTION-GENERATE');
await click('ASSET-01-BTN-CORRECTION-APPROVE');
await click('ASSET-01-BTN-CORRECTION-EXECUTE');
await waitState('CANDIDATE_OUTPUT');
assert(
  (await page.locator('[data-section-id="ASSET-01-SEC-06"] [data-control-id]').count()) === 0,
  'correction controls remained after new candidate',
);

// Patch reject path on the corrected candidate.
await click('ASSET-01-BTN-PATCH-CREATE');
await click('ASSET-01-BTN-PATCH-PREVIEW');
await click('ASSET-01-BTN-PATCH-REJECT');

// Restore-as-new shared operation is exercised as a TEST_ONLY shared-runtime substitute.
const beforeRestore = (await project()).body.output_version_id;
await click('ASSET-01-BTN-RESTORE-AS-NEW');
const displayedRestore = await page
  .locator('[data-control-id="ASSET-01-FLD-OUTPUT-ID"] strong')
  .textContent();
assert(displayedRestore && displayedRestore !== beforeRestore, 'restore-as-new did not produce a new draft ref');

// Re-read formal server candidate by evaluation, then confirm, lock and handoff.
await click('ASSET-01-BTN-EVALUATE');
await waitState('WAIT_CONFIRMATION');
await click('ASSET-01-BTN-CONFIRM');
await waitState('CONFIRMED');
await click('ASSET-01-BTN-LOCK');
await waitState('LOCKED');
await click('ASSET-01-BTN-HANDOFF');
await waitState('HANDOFF');
await snapshot('HANDOFF');

const finalProjection = (await project()).body;
assert(finalProjection.page_state === 'HANDOFF', 'handoff projection not persisted');
assert(
  String(finalProjection.values?.['ASSET-01-TEST-HANDOFF-REF'] || '').startsWith(
    'TEST-ASSET-VIDEO-HANDOFF-',
  ),
  'exact handoff ref missing',
);
assert(seenControls.size === 85, `control coverage ${seenControls.size}/85`);
assert(seenActions.size === 44, `action coverage ${seenActions.size}/44`);
assert(pageErrors.length === 0, `page errors: ${pageErrors.join(' | ')}`);
assert(failedRequests.length === 0, `failed requests: ${failedRequests.join(' | ')}`);
console.log(
  `ASSET01_BROWSER_FLOW_PASS controls=${seenControls.size} actions=${seenActions.size} final=${finalProjection.page_state} versions=${finalProjection.candidate_versions.length} ui_only_effects=PASS`,
);
await browser.close();
