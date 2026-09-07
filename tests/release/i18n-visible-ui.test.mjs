import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

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
  "AUTO",
  "MANUAL",
]);

function isAllowedMachineCode(text) {
  if (MACHINE_CODES.has(text)) return true;
  if (/^[A-Z0-9]+(?:[_-][A-Z0-9]+)+$/.test(text)) return true;
  return false;
}

function lineOf(sourceFile, node) {
  return sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1;
}

test("Current visible UI literals do not bypass i18n catalogs", async () => {
  const violations = [];

  for (const path of FILES) {
    const source = await readFile(path, "utf8");
    const sourceFile = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

    function visit(node) {
      if (ts.isJsxText(node)) {
        const text = node.getText(sourceFile).trim().replace(/\s+/g, " ");
        if (text && /[A-Za-z\u4e00-\u9fff]/.test(text) && !isAllowedMachineCode(text)) {
          violations.push(`${path}:${lineOf(sourceFile,node)}:direct:${text}`);
        }
      }

      if (ts.isJsxAttribute(node)) {
        const name = node.name.getText(sourceFile);
        if (["aria-label","title","placeholder"].includes(name) && node.initializer && ts.isStringLiteral(node.initializer)) {
          const text = node.initializer.text.trim().replace(/\s+/g, " ");
          if (text && /[A-Za-z\u4e00-\u9fff]/.test(text) && !isAllowedMachineCode(text)) {
            violations.push(`${path}:${lineOf(sourceFile,node)}:${name}:${text}`);
          }
        }
      }

      ts.forEachChild(node, visit);
    }

    visit(sourceFile);
  }

  assert.deepEqual(
    violations,
    [],
    `Visible UI literals must use Current i18n catalogs. Found:\n${violations.join("\n")}`,
  );
});
