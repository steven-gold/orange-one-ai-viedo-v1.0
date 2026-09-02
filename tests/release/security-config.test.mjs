import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const nextConfig = await readFile("next.config.ts", "utf8");
const gitignore = await readFile(".gitignore", "utf8");
const envExample = await readFile(".env.example", "utf8");

test("production security headers are declared", () => {
  for (const token of [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
  ]) assert.match(nextConfig, new RegExp(token));
});

test("standalone production output is enabled", () => {
  assert.match(nextConfig, /output:\s*"standalone"/);
});

test("environment and private-key files are ignored while example remains tracked", () => {
  assert.match(gitignore, /^\.env$/m);
  assert.match(gitignore, /^\.env\.\*$/m);
  assert.match(gitignore, /^!\.env\.example$/m);
  assert.match(gitignore, /^\*\.pem$/m);
  assert.match(gitignore, /^\*\.key$/m);
});

test("environment contract never enables controlled mode by default", () => {
  assert.match(envExample, /^NEXT_PUBLIC_ACPOS_RUNTIME_MODE=$/m);
  assert.doesNotMatch(envExample, /^NEXT_PUBLIC_ACPOS_RUNTIME_MODE=CONTROLLED_TEST$/m);
  assert.match(envExample, /^ACPOS_DEPLOYMENT_ENV=production$/m);
});
