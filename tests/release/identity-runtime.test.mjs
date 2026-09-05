import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("internal cookie session identity is materialized and WB-01 projection bind is registered", async () => {
  const identity = await read("src/server/identity/identityRuntime.ts");
  const sessionRoute = await read("src/app/v1/identity/session/route.ts");
  const loginPage = await read("src/app/login/page.tsx");
  const loginForm = await read("src/app/login/LoginForm.tsx");
  const formLogin = await read("src/app/identity/login/route.ts");
  const shell = await read("src/components/shell/AppShell.tsx");
  const instrumentation = await read("src/instrumentation.ts");
  const ready = await read("src/app/health/ready/route.ts");

  assert.match(identity, /IDENTITY_COOKIE_NAME = "acpos_session"/);
  assert.match(identity, /OPEN_LOGIN_PATH = "\/login"/);
  assert.match(identity, /IDENTITY_SESSION_PATH = "\/v1\/identity\/session"/);
  assert.match(identity, /scrypt\$\$\{SCRYPT_N\}\$/);
  assert.match(identity, /JOIN app_users u ON lower\(u\.email::text\) = lower\(a\.email\)/);
  assert.match(identity, /a\.status = 'READY'/);
  assert.match(identity, /ensureProductionNeonRuntime/);
  assert.doesNotMatch(identity, /u\.status = 'READY'/);
  assert.doesNotMatch(identity, /NEON_AUTH|Authorization Bearer|configureUiProjectionRuntime/);

  assert.match(sessionRoute, /export async function GET/);
  assert.match(sessionRoute, /export async function POST/);
  assert.match(sessionRoute, /export async function DELETE/);
  assert.match(sessionRoute, /IDENTITY_COOKIE_NAME/);

  assert.match(loginPage, /LoginForm/);
  assert.match(loginForm, /data-page-uid="identity:login"/);
  assert.match(loginForm, /action="\/identity\/login"/);
  assert.match(formLogin, /createIdentitySession/);
  assert.match(formLogin, /NextResponse.redirect/);
  assert.match(shell, /data-port-uid="GHS-PORT-IDENTITY"/);
  assert.match(shell, /href="\/login"/);

  assert.match(instrumentation, /bindWb01ProjectionRuntime/);
  assert.match(ready, /status:\s*503/);
});
