import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';

const root = process.cwd();
const requested = Number(process.env.ACPOS_SMOKE_PORT || 0);

function freePort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address();
      const port = typeof addr === 'object' && addr ? addr.port : 0;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

async function waitForHealth(url, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch {
      await delay(200);
    }
  }
  return false;
}

async function main() {
  const port = requested || (await freePort());
  const child = spawn('npx', ['tsx', 'src/server.ts'], {
    cwd: `${root}/apps/api`,
    env: {
      ...process.env,
      PORT: String(port),
      ACPOS_DATABASE_PATH: process.env.ACPOS_DATABASE_PATH || `${root}/apps/api/data/acpos.sqlite`,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => {
    stdout += chunk.toString();
  });
  child.stderr.on('data', (chunk) => {
    stderr += chunk.toString();
  });
  const result = {
    ok: false,
    port,
    checks: {},
    stdout_tail: '',
    stderr_tail: '',
  };
  try {
    const healthy = await waitForHealth(`http://127.0.0.1:${port}/health`);
    result.checks.health = healthy;
    const readyRes = await fetch(`http://127.0.0.1:${port}/health/ready`);
    const readyBody = await readyRes.json();
    result.checks.ready = readyRes.ok && readyBody.ready === true;
    result.checks.migrationCount = Number(readyBody.migrationCount || 0);
    const unauth = await fetch(`http://127.0.0.1:${port}/api/navigation`);
    result.checks.unauthenticated_rejected = unauth.status === 401;
    const nav = await fetch(`http://127.0.0.1:${port}/api/navigation`, {
      headers: { 'x-account-uid': 'ACC-LIMITED', 'x-session-uid': 'sess-limited-001' },
    });
    const body = await nav.json();
    result.checks.authenticated_navigation = nav.status === 200 && Array.isArray(body.items) && body.items.length === 2;
    const activate = await fetch(`http://127.0.0.1:${port}/api/navigation/activate`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-account-uid': 'ACC-LIMITED',
        'x-session-uid': 'sess-limited-001',
      },
      body: JSON.stringify({ itemUid: 'FRONT-01' }),
    });
    result.checks.activation_persisted = activate.status === 202;
    result.ok = Object.values(result.checks).every((value) => value === true || (typeof value === 'number' && value >= 1));
  } catch (error) {
    result.checks.error = error instanceof Error ? error.message : String(error);
    result.ok = false;
  } finally {
    child.kill('SIGTERM');
    await Promise.race([once(child, 'exit'), delay(2000)]);
    result.stdout_tail = stdout.slice(-2000);
    result.stderr_tail = stderr.slice(-2000);
  }
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  process.exit(result.ok ? 0 : 1);
}

main();
