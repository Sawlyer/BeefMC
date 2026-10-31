import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, rm, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { acquireRunLocks } from '../../scripts/benchmark/lib/locks.mjs';

test('exclusive port and instance locks reject overlapping benchmark runs', async t => {
  const temp = await mkdtemp(join(tmpdir(), 'beefbench-'));
  t.after(() => rm(temp, { recursive: true, force: true }));
  const root = join(temp, 'Test Server');
  const instance = join(root, 'instances', '1.21.11', 'beefmc');
  await mkdir(instance, { recursive: true });
  const release = await acquireRunLocks(root, 25565, [instance]);
  await assert.rejects(acquireRunLocks(root, 25565, [instance]), /locked/);
  await release();
  const releaseAgain = await acquireRunLocks(root, 25565, [instance]);
  await releaseAgain();
  await assert.rejects(access(join(root, 'locks', 'port-25565.lock')));
});

test('instance lock prevents same folder on a different port', async t => {
  const temp = await mkdtemp(join(tmpdir(), 'beefbench-'));
  t.after(() => rm(temp, { recursive: true, force: true }));
  const root = join(temp, 'Test Server');
  const instance = join(root, 'instance');
  await mkdir(instance, { recursive: true });
  const release = await acquireRunLocks(root, 25565, [instance]);
  await assert.rejects(acquireRunLocks(root, 25566, [instance]), /locked/);
  await release();
});
