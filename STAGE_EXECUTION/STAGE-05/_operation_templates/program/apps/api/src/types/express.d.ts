import type { AuthenticatedPrincipal } from '../auth/authentication';

declare global {
  namespace Express {
    interface Request {
      principal?: AuthenticatedPrincipal;
    }
  }
}

export {};
