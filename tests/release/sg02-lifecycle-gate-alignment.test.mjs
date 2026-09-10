import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync("src/server/shared/pageCatalogProjectionRuntime.ts", "utf8");

test("SG02 effectful controls require the authority lifecycle state in addition to permission", () => {
  assert.match(source, /const criteriaStatus = asText\(first\?\.status\);/);
  assert.match(
    source,
    /"CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE": canConfigure && criteriaStatus === "DRAFT"/,
  );
  assert.match(
    source,
    /"CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE": canApprove && criteriaStatus === "REVIEW"/,
  );
});

test("SG02 empty projection cannot enable configure or approve by permission alone", () => {
  assert.doesNotMatch(
    source,
    /"CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE": canConfigure,\s*\n/,
  );
  assert.doesNotMatch(
    source,
    /"CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE": canApprove,\s*\n/,
  );
});
