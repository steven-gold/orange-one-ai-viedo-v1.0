import type { NavigationEvent } from '../domain/types';
import { persistNavigationEvent, readNavigationEvents } from './auditLog';

export interface AuditRecordInput {
  accountUid: string;
  area: 'FRONT' | 'ADMIN';
  itemUid: string;
  route: string;
}

export function recordNavigationEvent(input: AuditRecordInput): NavigationEvent {
  const occurredAt = new Date().toISOString();
  return persistNavigationEvent({
    eventUid: `EVT-${occurredAt}-${input.itemUid}`,
    accountUid: input.accountUid,
    area: input.area,
    itemUid: input.itemUid,
    route: input.route,
    occurredAt,
  });
}

export function listAuditEvents(): NavigationEvent[] {
  return readNavigationEvents();
}
