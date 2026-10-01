import type { NavigationEvent } from '../domain/types';
import { runtimeStore } from '../storage/runtimeStore';

export function persistNavigationEvent(event: NavigationEvent): NavigationEvent {
  return runtimeStore.recordAuditEvent(event);
}

export function readNavigationEvents(): NavigationEvent[] {
  return runtimeStore.listAuditEvents();
}
