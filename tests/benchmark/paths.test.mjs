import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { resolveWithinRoot } from '../../scripts/benchmark/lib/paths.mjs';

test('rejects paths outside physical Test Server root even when names contain that text', async t => {
  const temp = await mkdtemp(join(tmpdir(), 'beefbench-'));
  t.after(() => rm(temp, { recursive: true, force: true }));
  const root = join(temp, 'Test Server');
  await mkdir(root);
  const outside = join(temp, 'outside', 'Test Server', 'file.jar');
  await mkdir(join(temp, 'outside', 'Test Server'), { recursive: true });
  await writeFile(outside, 'outside');
  await assert.rejects(resolveWithinRoot(root, outside, 'artifact'), /inside Test Server/);
});

test('rejects junctions that redirect writes outside the Test Server root', async t => {
  const temp = await mkdtemp(join(tmpdir(), 'beefbench-'));
  t.after(() => rm(temp, { recursive: true, force: true }));
  const root = join(temp, 'Test Server');
  await mkdir(root);
  const outside = join(temp, 'outside');
  await mkdir(outside);
  const link = join(root, 'redirect');
  try {
    await symlink(outside, link, 'junction');
  } catch (error) {
    if (['EPERM', 'EACCES', 'UNKNOWN'].includes(error.code)) return t.skip('Windows junction creation unavailable');
    throw error;
  }
  await assert.rejects(resolveWithinRoot(root, join(link, 'world'), 'world path'), /inside Test Server/);
});
