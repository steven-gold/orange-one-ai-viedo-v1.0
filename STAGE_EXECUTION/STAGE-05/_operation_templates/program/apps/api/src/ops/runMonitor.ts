import { bootstrapDatabase, readyCheck } from '../db/bootstrap';
import { closeSqlClient } from '../db/client';
import { drainAuditEvents } from '../workers/auditWorker';

bootstrapDatabase()
  .then(async (result) => {
    const ready = await readyCheck();
    const drain = await drainAuditEvents();
    process.stdout.write(
      JSON.stringify({
        ok: Boolean(ready.ready),
        dialect: result.dialect,
        applied: result.applied,
        alreadyApplied: result.alreadyApplied,
        migrationCount: ready.migrationCount,
        drained: drain.drained,
      }) + '\n',
    );
  })
  .catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(1);
  })
  .finally(() => closeSqlClient());
