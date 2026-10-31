import { mkdir, open, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { resolveWithinRoot } from './paths.mjs';

export async function acquireRunLocks(testServerRoot, port, instanceDirectories) {
  const lockDirectory = await resolveWithinRoot(testServerRoot, join(testServerRoot, 'locks'), 'lock directory');
  await mkdir(lockDirectory, { recursive: true });
  const safeLockDirectory = await resolveWithinRoot(testServerRoot, lockDirectory, 'lock directory');
  const resources = new Set(['port-' + port]);
  for (const path of instanceDirectories) {
    const key = createHash('sha256').update(path.toLowerCase()).digest('hex').slice(0, 24);
    resources.add('instance-' + key);
  }
  const held = [];
  try {
    for (const resource of [...resources].sort()) {
      const path = await resolveWithinRoot(testServerRoot, join(safeLockDirectory, resource + '.lock'), 'lock file');
      let handle;
      try {
        handle = await open(path, 'wx');
        await handle.writeFile(JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }) + '\n');
      } catch (error) {
        if (error.code === 'EEXIST') throw new Error('Benchmark resource is locked by another run: ' + resource);
        throw error;
      } finally {
        await handle?.close();
      }
      held.push(path);
    }
  } catch (error) {
    for (const path of held) await rm(path, { force: true });
    throw error;
  }
  return async () => {
    for (const path of held.reverse()) await rm(path, { force: true });
  };
}
