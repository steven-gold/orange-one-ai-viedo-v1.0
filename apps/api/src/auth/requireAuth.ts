import type { NextFunction, Request, Response } from 'express';
import { authenticate } from './authentication';

const PUBLIC_PATHS = new Set(['/health', '/health/ready']);

export async function requireAuth(req: Request, res: Response, next: NextFunction): Promise<void> {
  if (PUBLIC_PATHS.has(req.path)) {
    next();
    return;
  }
  try {
    const principal = await authenticate(req);
    req.principal = principal;
    if (!principal.authenticated) {
      res.status(401).json({
        error: { code: 'UNAUTHENTICATED', message: 'Valid session and account identity are required' },
      });
      return;
    }
    next();
  } catch (error) {
    next(error);
  }
}
