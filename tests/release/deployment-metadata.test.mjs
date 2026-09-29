import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("deployment metadata prefers ACPOS overrides and falls back to Vercel system metadata", async () => {
  const helper = await read("src/server/shared/deploymentMetadata.ts");
  assert.match(helper, /ACPOS_DEPLOYMENT_ENV/);
  assert.match(helper, /VERCEL_ENV/);
  assert.match(helper, /ACPOS_RELEASE_SHA/);
  assert.match(helper, /VERCEL_GIT_COMMIT_SHA/);
  assert.match(helper, /ACPOS_DEPLOYMENT_ENV[\s\S]*VERCEL_ENV[\s\S]*unspecified/);
  assert.match(helper, /ACPOS_RELEASE_SHA[\s\S]*VERCEL_GIT_COMMIT_SHA[\s\S]*unresolved/);
});

test("health and readiness share the deployment metadata resolver", async () => {
  for (const path of ["src/app/health/route.ts", "src/app/health/ready/route.ts"]) {
    const source = await read(path);
    assert.match(source, /getDeploymentMetadata/);
    assert.match(source, /metadata\.environment/);
    assert.match(source, /metadata\.release_sha/);
    assert.doesNotMatch(source, /process\.env\.ACPOS_RELEASE_SHA/);
  }
});
