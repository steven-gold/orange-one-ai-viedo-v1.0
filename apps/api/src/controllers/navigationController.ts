import type { Request, Response, NextFunction } from 'express';
import {
  NavigationResolutionError,
  resolveAdminActiveUid,
  resolveFrontActiveUid,
  resolveVisibleNavigation,
} from '../domain/navigation';
import { recordNavigationEvent } from '../audit/auditLogger';
import { getNavigationItem } from '../repositories/navigationRepository';
import type { NavigationArea } from '../domain/types';

function accountUidOf(req: Request): string {
  const fromAuth = req.header('x-account-uid');
  const fromQuery = typeof req.query.accountUid === 'string' ? req.query.accountUid : '';
  return fromAuth ?? fromQuery;
}

export function getNavigation(req: Request, res: Response, next: NextFunction): void {
  try {
    const accountUid = accountUidOf(req);
    const area: NavigationArea = req.query.area === 'ADMIN' ? 'ADMIN' : 'FRONT';
    const resolution = resolveVisibleNavigation(accountUid);
    res.status(200).json({
      area,
      authorityUid: resolution.authorityUid,
      items: resolution.items.filter((item) => item.area === area),
      resolved: true,
      error: null,
    });
  } catch (error) {
    next(error);
  }
}

export function getActiveNavigation(req: Request, res: Response, next: NextFunction): void {
  try {
    const accountUid = accountUidOf(req);
    const area: NavigationArea = req.query.area === 'ADMIN' ? 'ADMIN' : 'FRONT';
    const resolution = resolveVisibleNavigation(accountUid);
    const activePageUid = typeof req.query.pageUid === 'string' ? req.query.pageUid : null;
    const resolved =
      area === 'ADMIN'
        ? resolveAdminActiveUid(resolution.items, activePageUid)
        : resolveFrontActiveUid(
            resolution.items,
            typeof req.query.ancestry === 'string' ? req.query.ancestry.split(',') : [],
          );
    res.status(200).json({ area, activeNavigationUid: resolved });
  } catch (error) {
    next(error);
  }
}

export function activateNavigation(req: Request, res: Response, next: NextFunction): void {
  try {
    const accountUid = accountUidOf(req);
    const itemUid = String(req.body?.itemUid ?? '');
    const item = getNavigationItem(itemUid);
    if (!item) {
      res.status(404).json({
        error: { code: 'NAVIGATION_TARGET_UNRESOLVABLE', message: `Unknown item ${itemUid}` },
      });
      return;
    }
    const resolution = resolveVisibleNavigation(accountUid);
    if (!resolution.items.some((entry) => entry.uid === itemUid)) {
      throw new NavigationResolutionError(
        'NAVIGATION_TARGET_UNRESOLVABLE',
        `Item ${itemUid} is not visible to ${accountUid}`,
      );
    }
    const event = recordNavigationEvent({
      accountUid,
      area: item.area,
      itemUid: item.uid,
      route: item.route,
    });
    res.status(202).json({ eventUid: event.eventUid, route: item.route });
  } catch (error) {
    next(error);
  }
}
