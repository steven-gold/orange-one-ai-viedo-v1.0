import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const FILES = [
  "src/components/shell/AppShell.tsx",
  "src/components/pages/DashboardVisual.tsx",
  "src/components/pages/CoreVisual.tsx",
  "src/components/pages/AssetVisual.tsx",
  "src/components/pages/VideoVisual.tsx",
  "src/components/pages/EditVisual.tsx",
  "src/components/pages/QaVisual.tsx",
  "src/components/pages/DbVisual.tsx",
  "src/components/pages/StrategyVisual.tsx",
  "src/components/pages/InfoVisual.tsx",
  "src/components/pages/SystemVisual.tsx",
  "src/components/pages/IamVisual.tsx",
  "src/components/pages/DevVisual.tsx",
  "src/components/pages/SocVisual.tsx",
  "src/components/pages/ErpVisual.tsx",
  "src/components/pages/AiApiVisual.tsx",
  "src/components/pages/QaCriteriaVisual.tsx",
  "src/components/pages/StrategyAdminVisual.tsx",
  "src/components/pages/KnowledgeAdminVisual.tsx",
];

const MACHINE_CODES = new Set([
  "FINAL_LOCKED",
  "NOT_EXECUTED",
  "LOADING",
  "BOUND",
  "CONFIRM",
]);

function isAllowedMachineCode(text) {
  if (MACHINE_CODES.has(text)) return true;
  if (/^[A-Z0-9]+(?:[_-][A-Z0-9]+)+$/.test(text)) return true;
  return false;
}

test("Current visible UI literals do not bypass i18n catalogs", async () => {
  const violations = [];

  for (const path of FILES) {
    const source = await readFile(path, "utf8");
    const lines = source.split("\n");

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];

      for (const match of line.matchAll(/>([^<>{}]*[A-Za-z\u4e00-\u9fff][^<>{}]*)</g)) {
        const text = match[1].trim().replace(/\s+/g, " ");
        if (!text || isAllowedMachineCode(text)) continue;
        violations.push(`${path}:${index + 1}:direct:${text}`);
      }

      for (const match of line.matchAll(/\b(aria-label|title|placeholder)=["']([^"']*[A-Za-z\u4e00-\u9fff][^"']*)["']/g)) {
        const text = match[2].trim().replace(/\s+/g, " ");
        if (!text || isAllowedMachineCode(text)) continue;
        violations.push(`${path}:${index + 1}:${match[1]}:${text}`);
      }
    }
  }

  assert.deepEqual(
    violations,
    [],
    `Visible UI literals must use Current i18n catalogs. Found:\n${violations.join("\n")}`,
  );
});
