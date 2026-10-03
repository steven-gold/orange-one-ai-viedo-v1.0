import express, { type Express } from 'express';
import { navigationRoutes } from './routes/navigationRoutes';
import { permissionRoutes } from './routes/permissionRoutes';
import { errorContract } from './middleware/errorContract';
import { requireAuth } from './auth/requireAuth';
import { readyCheck } from './db/bootstrap';

export function createApp(): Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok' });
  });

  app.get('/health/ready', async (_req, res) => {
    const ready = await readyCheck();
    res.status(ready.ready ? 200 : 503).json(ready);
  });

  app.use(requireAuth);
  app.use('/api/navigation', navigationRoutes);
  app.use('/api/permissions', permissionRoutes);

  app.use(errorContract);
  return app;
}
