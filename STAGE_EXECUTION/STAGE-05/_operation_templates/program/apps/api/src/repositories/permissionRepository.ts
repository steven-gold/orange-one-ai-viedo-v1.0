import type { PermissionAssignment } from '../domain/types';
import { runtimeStore } from '../storage/runtimeStore';

export async function getAssignment(accountUid: string): Promise<PermissionAssignment | undefined> {
  return runtimeStore.getAssignment(accountUid);
}
