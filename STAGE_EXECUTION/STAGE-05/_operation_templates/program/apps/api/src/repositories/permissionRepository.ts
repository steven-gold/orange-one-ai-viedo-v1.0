import type { PermissionAssignment } from '../domain/types';
import { runtimeStore } from '../storage/runtimeStore';

export function getAssignment(accountUid: string): PermissionAssignment | undefined {
  return runtimeStore.getAssignment(accountUid);
}
