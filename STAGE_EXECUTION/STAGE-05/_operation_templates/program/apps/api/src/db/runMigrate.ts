import { bootstrapDatabase } from './bootstrap';

bootstrapDatabase()
  .then((result) => {
    process.stdout.write(
      JSON.stringify({ ok: true, dialect: result.dialect, applied: result.applied, alreadyApplied: result.alreadyApplied }) + '\n',
    );
  })
  .catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(1);
  });
