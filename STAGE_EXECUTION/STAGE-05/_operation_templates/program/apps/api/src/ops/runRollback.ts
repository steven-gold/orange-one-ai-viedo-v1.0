import { bootstrapDatabase } from '../db/bootstrap';
import { closeSqlClient } from '../db/client';
import { rollbackToSnapshot } from './rollback';

const path = process.argv[2];
if (!path) {
  process.stderr.write('usage: tsx src/ops/runRollback.ts <snapshot.json>\n');
  process.exit(1);
}

bootstrapDatabase()
  .then(() => rollbackToSnapshot(path))
  .then((snapshot) => {
    process.stdout.write(
      JSON.stringify({
        ok: true,
        path,
        itemCount: snapshot.items.length,
        assignmentCount: snapshot.assignments.length,
        eventCount: snapshot.events.length,
      }) + '\n',
    );
  })
  .catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(1);
  })
  .finally(() => closeSqlClient());
