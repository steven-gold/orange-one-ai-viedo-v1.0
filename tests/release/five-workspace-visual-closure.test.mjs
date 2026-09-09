import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

function registrySlice(source, start, end) {
  const a = source.indexOf(start);
  const b = source.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, `REGISTRY_SLICE_MISSING:${start}`);
  return source.slice(a, b);
}

function registryUids(source, prefix) {
  if (prefix === "CORE") {
    return [...source.matchAll(/^\s*["'](CORE-01-[A-Z0-9-]+)["']\s*:/gm)].map((m) => m[1]);
  }
  if (prefix === "QA") {
    return [...source.matchAll(/\bs\(["'](QA-01-[A-Z0-9-]+)["']/g)].map((m) => m[1]);
  }
  return [...source.matchAll(new RegExp(`\\bid\\s*:\\s*["'](${prefix}-01-[A-Z0-9-]+)["']`, "g"))].map((m) => m[1]);
}

test("five workspace visual closure keeps the 467 Current control registry", async () => {
  const [core, asset, video, edit, qa] = await Promise.all([
    read("src/components/pages/CoreVisual.tsx"),
    read("src/components/pages/AssetVisual.tsx"),
    read("src/components/pages/VideoVisual.tsx"),
    read("src/components/pages/EditVisual.tsx"),
    read("src/components/pages/QaVisual.tsx"),
  ]);

  const slices = [
    ["CORE", registrySlice(core, "const CONTROL_ACTION_UID", "function actionUid"), 50],
    ["ASSET", registrySlice(asset, "const CONTEXT", "const ALL_CONTROL_SPECS"), 85],
    ["VIDEO", registrySlice(video, "const CONTEXT", "const ALL="), 85],
    ["EDIT", registrySlice(edit, "const CONTEXT", "const ALL ="), 160],
    ["QA", registrySlice(qa, "const CONTEXT", "const ALL="), 87],
  ];

  let total = 0;
  for (const [prefix, source, expected] of slices) {
    const ids = registryUids(source, prefix);
    const unique = new Set(ids);
    assert.equal(unique.size, expected, `${prefix}_CONTROL_REGISTRY_COUNT`);
    assert.equal(ids.length, expected, `${prefix}_CONTROL_REGISTRY_DUPLICATE`);
    total += unique.size;
  }
  assert.equal(total, 467, "FIVE_WORKSPACE_CONTROL_TOTAL");
});

test("five workspace v2 topology is Stage Driven without a second runtime owner", async () => {
  const [core, asset, video, edit, qa] = await Promise.all([
    read("src/components/pages/CoreVisual.tsx"),
    read("src/components/pages/AssetVisual.tsx"),
    read("src/components/pages/VideoVisual.tsx"),
    read("src/components/pages/EditVisual.tsx"),
    read("src/components/pages/QaVisual.tsx"),
  ]);

  for (const [uid, source] of [["CORE-01", core], ["ASSET-01", asset], ["VIDEO-01", video], ["EDIT-01", edit], ["QA-01", qa]]) {
    assert.match(source, /data-layout-grid="workspace-three-column"/, `${uid}_THREE_COLUMN`);
    assert.match(source, /data-current-stage-action-dock="true"/, `${uid}_STAGE_DOCK`);
  }

  assert.match(asset, /data-correction-ui="full-conversation"/);
  assert.match(video, /data-correction-ui="full-conversation"/);
  assert.match(edit, /data-correction-ui="full-conversation"/);
  assert.match(qa, /data-review-discussion="true"/);

  assert.match(edit, /data-main-timeline="true"/);
  assert.match(edit, /data-timeline-legacy-merge="MERGE_VISUAL_ONLY"/);
  assert.doesNotMatch(edit, /className=\{\`\$\{styles\.panel\} \$\{styles\.rangePanel\}\`\}/);
});

test("Correction composer inputs keep their existing action owners", async () => {
  const [assetRuntime, video, edit, qa] = await Promise.all([
    read("src/components/pages/AssetControlRuntime.tsx"),
    read("src/components/pages/VideoVisual.tsx"),
    read("src/components/pages/EditVisual.tsx"),
    read("src/components/pages/QaVisual.tsx"),
  ]);

  assert.match(assetRuntime, /ASSET-01-TXT-CORRECTION-REQUEST/);
  assert.match(assetRuntime, /LOCAL-CORRECTION-REQUEST/);
  assert.match(video, /VIDEO-01-TXT-CORRECTION/);
  assert.match(edit, /EDIT-01-FLD-API-INSTRUCTION/);
  assert.match(qa, /QA-01-INP-CORR-ACTION/);
});
