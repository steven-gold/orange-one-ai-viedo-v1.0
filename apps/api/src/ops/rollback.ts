import { restoreFromFile, type RuntimeSnapshot } from './backup';

export async function rollbackToSnapshot(path: string): Promise<RuntimeSnapshot> {
  return restoreFromFile(path);
}
