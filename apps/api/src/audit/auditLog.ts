import type { NavigationEvent } from '../domain/types';
import { runtimeStore } from '../storage/runtimeStore';

export async function persistNavigationEvent(event: NavigationEvent): Promise<NavigationEvent> {
  return runtimeStore.recordAuditEvent(event);
}

export async function readNavigationEvents(): Promise<NavigationEvent[]> {
  return runtimeStore.listAuditEvents();
}
