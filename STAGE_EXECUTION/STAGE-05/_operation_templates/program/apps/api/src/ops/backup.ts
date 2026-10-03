import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { persistDump, persistRestore } from '../db/persist';
import type { CanonicalNavigationItem, NavigationEvent, PermissionAssignment } from '../domain/types';

export interface RuntimeSnapshot {
  createdAt: string;
  items: CanonicalNavigationItem[];
  assignments: PermissionAssignment[];
  events: NavigationEvent[];
}

export async function backupToFile(path: string): Promise<RuntimeSnapshot> {
  const dump = await persistDump();
  const snapshot: RuntimeSnapshot = { createdAt: new Date().toISOString(), ...dump };
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(snapshot, null, 2), 'utf8');
  return snapshot;
}

export async function restoreFromFile(path: string): Promise<RuntimeSnapshot> {
  const snapshot = JSON.parse(readFileSync(path, 'utf8')) as RuntimeSnapshot;
  await persistRestore(snapshot);
  return snapshot;
}
