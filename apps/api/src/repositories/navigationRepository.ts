import type { CanonicalNavigationItem, NavigationArea } from '../domain/types';
import { runtimeStore } from '../storage/runtimeStore';

export async function listNavigationItems(area?: NavigationArea): Promise<CanonicalNavigationItem[]> {
  const items = await runtimeStore.listItems();
  const scoped = area ? items.filter((entry) => entry.area === area) : items;
  return scoped.sort((a, b) => a.order - b.order);
}

export async function getNavigationItem(uid: string): Promise<CanonicalNavigationItem | undefined> {
  return runtimeStore.getItem(uid);
}

export function getAuthorityUid(): string {
  return runtimeStore.authorityUid;
}
