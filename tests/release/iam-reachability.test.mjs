import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("current IAM integration ports remain reachable through their authority-bound routes", async () => {
  const authority = await read("authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");
  const contract = await read("src/domain/iam/iamRuntimeContract.ts");
  const runtime = await read("src/server/iam/iamRuntime.ts");

  assert.match(authority, /system_implementation_status:\s*NOT_EXECUTED/);
  assert.match(contract, /IAM_PORT_COUNT\s*=\s*IAM_PORT_UIDS\.length/);
  assert.match(contract, /IAM_CONTROL_COUNT\s*=\s*14/);
  assert.match(runtime, /IAM01_RUNTIME_NOT_BOUND/);
  assert.match(runtime, /IAM01_AUTHORIZATION_EVALUATION_FAILED/);
  assert.match(runtime, /IAM01_OPERATION_FAILED/);

  const authorityPorts = [...authority.matchAll(/- port_uid:\s*(IAM-01-PORT-[A-Z0-9-]+)/g)];
  assert.equal(authorityPorts.length, 9, `expected 9 current IAM integration ports, found ${authorityPorts.length}`);

  const routeBindings = [
    ["src/app/v1/ui-projections/[pageUid]/route.ts", "GET", "getUiProjection"],
    ["src/app/v1/search/route.ts", "POST", "searchProjection"],
    ["src/app/v1/drafts/route.ts", "POST", "saveDraft"],
    ["src/app/v1/drafts/[id]/validate/route.ts", "POST", "validateDraft"],
    ["src/app/v1/governance/resources/[id]/route.ts", "PATCH", "configureGovernedResource"],
    ["src/app/v1/iam/accounts/[accountId]/authorization-impact/route.ts", "POST", "previewAuthorizationImpact"],
    ["src/app/v1/iam/accounts/[accountId]/permissions/route.ts", "POST", "assignAccountPermission"],
    ["src/app/v1/iam/accounts/[accountId]/permissions/route.ts", "DELETE", "revokeAccountPermission"],
    ["src/app/v1/governance/resources/[id]/approve/route.ts", "POST", "approveGovernedResource"],
  ];

  for (const [path, method, operation] of routeBindings) {
    const source = await read(path);
    assert.match(
      source,
      new RegExp(`export\\s+(?:const\\s+${method}\\s*=|async\\s+function\\s+${method}\\s*\\()`),
      `${path} must expose ${method}`,
    );
    const operationPattern = operation === "getUiProjection"
      ? /\bgetUiProjection\b/
      : new RegExp(`["']${operation}["']`);
    assert.match(source, operationPattern, `${path} must remain bound to ${operation}`);
  }

  assert.match(
    authority,
    /action_uid:\s*IAM-01-ACT-COMPLETE[\s\S]*?effect:\s*ORCHESTRATED_EXISTING_OPERATIONS[\s\S]*?No new endpoint\./,
    "IAM-01 COMPLETE must continue orchestrating registered operations without inventing a new endpoint",
  );
});
