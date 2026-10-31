import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm, readFile, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { copyWorldSnapshot, preflightInstance } from '../../scripts/benchmark/lib/server.mjs';

async function fixture(t, { eula = 'eula=true\n', bind = '127.0.0.1' } = {}) {
  const root = await mkdtemp(join(tmpdir(), 'beefbench-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const instance = join(root, 'instance');
  await mkdir(instance);
  const jar = join(root, 'server.jar');
  await writeFile(jar, 'fixture jar');
  await writeFile(join(root, 'java.exe'), 'fixture runtime');
  await writeFile(join(instance, 'eula.txt'), eula);
  await writeFile(join(instance, 'server.properties'), `server-ip=${bind}\nonline-mode=false\nwhite-list=true\nenforce-whitelist=true\nserver-port=25565\n`);
  const sha256 = createHash('sha256').update('fixture jar').digest('hex');
  return { instanceDirectory: instance, jar, sha256, javaExecutable: join(root, 'java.exe'), runtimeJava: 21, port: 25565 };
}

const preflight = config => preflightInstance(config, { probeJava: async () => ({ major: 21, version: '21.0.0', raw: 'openjdk version "21.0.0"' }) });

test('preflight accepts verified local offline instance with accepted EULA', async t => {
  assert.equal((await preflight(await fixture(t))).ok, true);
});

test('preflight rejects artifact checksum mismatch', async t => {
  await assert.rejects(preflight({ ...(await fixture(t)), sha256: '0'.repeat(64) }), /SHA-256/);
});

test('preflight rejects missing runtime', async t => {
  const config = await fixture(t);
  config.javaExecutable = join(config.instanceDirectory, 'missing-java.exe');
  await assert.rejects(preflight(config), /Java executable/);
});

test('preflight rejects non-loopback listener', async t => {
  const config = await fixture(t, { bind: '0.0.0.0' });
  await assert.rejects(preflight(config), /127\.0\.0\.1/);
});

test('preflight rejects EULA unless already accepted and leaves file unchanged', async t => {
  const config = await fixture(t, { eula: 'eula=false\n' });
  await assert.rejects(preflight(config), /EULA/);
  assert.equal(await (await import('node:fs/promises')).readFile(join(config.instanceDirectory, 'eula.txt'), 'utf8'), 'eula=false\n');
});

test('preflight rejects a Java runtime that does not match the catalog', async t => {
  const config = await fixture(t);
  await assert.rejects(
    preflightInstance(config, { probeJava: async () => ({ major: 25, version: '25.0.0', raw: 'openjdk version "25.0.0"' }) }),
    /expected Java 21/,
  );
});

test('restores identical world folders and removes dimensions absent from snapshot', async t => {
  const root = await mkdtemp(join(tmpdir(), 'beefbench-world-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const snapshot = join(root, 'snapshot');
  const instance = join(root, 'instance');
  await mkdir(join(snapshot, 'world'), { recursive: true });
  await mkdir(join(snapshot, 'world_nether'), { recursive: true });
  await mkdir(join(instance, 'world'), { recursive: true });
  await mkdir(join(instance, 'world_the_end'), { recursive: true });
  await writeFile(join(snapshot, 'world', 'seed.dat'), 'baseline');
  await writeFile(join(instance, 'world', 'seed.dat'), 'changed');
  await writeFile(join(instance, 'world_the_end', 'old.dat'), 'old');
  await copyWorldSnapshot(instance, snapshot);
  assert.equal(await readFile(join(instance, 'world', 'seed.dat'), 'utf8'), 'baseline');
  await assert.rejects(access(join(instance, 'world_the_end')));
  await access(join(instance, 'world_nether'));
});
