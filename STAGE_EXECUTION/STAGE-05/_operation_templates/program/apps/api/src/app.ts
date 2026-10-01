import express, { type Express } from 'express';
import { navigationRoutes } from './routes/navigationRoutes';
import { permissionRoutes } from './routes/permissionRoutes';
import { errorContract } from './middleware/errorContract';

export function createApp(): Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok' });
  });

  app.use('/api/navigation', navigationRoutes);
  app.use('/api/permissions', permissionRoutes);

  app.use(errorContract);
  return app;
}
