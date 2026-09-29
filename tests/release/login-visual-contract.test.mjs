import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [form, css] = await Promise.all([
  readFile(new URL("../../src/app/login/LoginForm.tsx", import.meta.url), "utf8"),
  readFile(new URL("../../src/app/globals.css", import.meta.url), "utf8"),
]);

test("login keeps canonical identity POST while using current visual contract", () => {
  assert.match(form, /method="post"/);
  assert.match(form, /action="\/identity\/login"/);
  assert.match(form, /data-page-uid="identity:login"/);
  assert.match(form, /data-login-visual="ACPOS_LOGIN_CURRENT_V2"/);
  assert.match(form, /data-login-contract="CURRENT_VISUAL_AUTHORITY"/);
});

test("login exposes the governed three-locale selector without changing auth runtime", () => {
  assert.match(form, /LOCALES\.map/);
  assert.match(form, /LOCALE_LABELS\[candidate\]/);
  assert.match(form, /setLocale\(candidate\)/);
  assert.match(form, /global\.login\.email/);
  assert.match(form, /global\.login\.password/);
  assert.match(form, /global\.login\.submit/);
});

test("login visual surface uses current ACPOS split-shell and primary purple semantics", () => {
  assert.match(css, /\.login-page\s*\{[^}]*grid-template-columns:/s);
  assert.match(css, /\.login-hero\s*\{/);
  assert.match(css, /\.login-access\s*\{/);
  assert.match(css, /\.login-card\s*\{/);
  assert.match(css, /\.login-submit\s*\{[^}]*linear-gradient\(135deg, var\(--purple-secondary\)/s);
  assert.match(css, /@media \(max-width: 980px\)/);
});
