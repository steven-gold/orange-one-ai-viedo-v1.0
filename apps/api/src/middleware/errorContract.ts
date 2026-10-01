import type { NextFunction, Request, Response } from 'express';
import { NavigationResolutionError } from '../domain/navigation';
import type { ApiErrorBody } from '../domain/types';

const STATUS_BY_CODE: Record<string, number> = {
  NAVIGATION_TARGET_UNRESOLVABLE: 404,
  NAVIGATION_AUTHORITY_UNAVAILABLE: 403,
  AUTHORIZATION_DENIED: 403,
};

export function errorContract(
  error: unknown,
  _req: Request,
  res: Response,
  _next: NextFunction,
): void {
  if (error instanceof NavigationResolutionError) {
    const body: ApiErrorBody = {
      error: { code: error.code, message: error.message },
    };
    res.status(STATUS_BY_CODE[error.code] ?? 400).json(body);
    return;
  }
  const body: ApiErrorBody = {
    error: { code: 'INTERNAL_ERROR', message: 'Unexpected navigation runtime error' },
  };
  res.status(500).json(body);
}
