import { bootstrapDatabase } from '../db/bootstrap';
import { closeSqlClient } from '../db/client';
import { backupToFile } from './backup';

const path = process.argv[2] || 'apps/api/data/backup.json';

bootstrapDatabase()
  .then(() => backupToFile(path))
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
