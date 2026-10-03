import { listAuditEvents } from '../audit/auditLogger';
import type { NavigationEvent } from '../domain/types';

export interface AuditDrainResult {
  drained: number;
  events: NavigationEvent[];
}

/**
 * Asynchronous audit drain used by the runtime to forward recorded navigation
 * events to downstream sinks without blocking the request path.
 */
export async function drainAuditEvents(): Promise<AuditDrainResult> {
  const events = await listAuditEvents();
  return { drained: events.length, events };
}
