import { createApp } from './app';
import { bootstrapDatabase } from './db/bootstrap';
import { DEFAULT_PORT } from './config/env';

const port = Number(process.env.PORT ?? DEFAULT_PORT);

async function main(): Promise<void> {
  const migration = await bootstrapDatabase();
  const app = createApp();
  app.listen(port, () => {
    process.stdout.write(
      `acpos api listening on ${port} dialect=${migration.dialect} applied=${migration.applied.join(',') || 'none'}\n`,
    );
  });
}

main().catch((error) => {
  process.stderr.write(`acpos api failed to start: ${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});
