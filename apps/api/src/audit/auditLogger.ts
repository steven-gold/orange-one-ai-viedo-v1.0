import type { NavigationEvent } from '../domain/types';
import { persistNavigationEvent, readNavigationEvents } from './auditLog';

export interface AuditRecordInput {
  accountUid: string;
  area: 'FRONT' | 'ADMIN';
  itemUid: string;
  route: string;
}

export async function recordNavigationEvent(input: AuditRecordInput): Promise<NavigationEvent> {
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

export async function listAuditEvents(): Promise<NavigationEvent[]> {
  return readNavigationEvents();
}
