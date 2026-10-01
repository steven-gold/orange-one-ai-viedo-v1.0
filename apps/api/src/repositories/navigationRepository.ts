import type { CanonicalNavigationItem, NavigationArea } from '../domain/types';
import { runtimeStore } from '../storage/runtimeStore';

export function listNavigationItems(area?: NavigationArea): CanonicalNavigationItem[] {
  const items = runtimeStore.listItems();
  const scoped = area ? items.filter((entry) => entry.area === area) : items;
  return scoped.sort((a, b) => a.order - b.order);
}

export function getNavigationItem(uid: string): CanonicalNavigationItem | undefined {
  return runtimeStore.getItem(uid);
}

export function getAuthorityUid(): string {
  return runtimeStore.authorityUid;
}
