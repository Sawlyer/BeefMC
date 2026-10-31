import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, access, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { prepareBenchmark } from '../../scripts/benchmark/prepare.mjs';

test('prepares loopback-only instances without accepting EULA', async t => {
  const root = await mkdtemp(join(tmpdir(), 'beefbench-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const testRoot = join(root, 'Test Server');
  const artifacts = join(testRoot, 'artifacts');
  await mkdir(artifacts, { recursive: true });
  const jar = join(artifacts, 'fixture.jar');
  await writeFile(jar, 'fixture');
  const sha256 = createHash('sha256').update('fixture').digest('hex');
  const sourceConfig = join(root, 'source.json');
  await writeFile(sourceConfig, JSON.stringify({
    version: '1.21.11', runtimeJava: 21, javaExecutable: join(root, 'java.exe'), port: 25565,
    botCount: 1, warmupSeconds: 0, sampleSeconds: 1, repetitions: 1, scenario: 'steady-world',
    outputDirectory: join(testRoot, 'results'), jvmArgs: ['-Xms1G', '-Xmx1G'],
    variants: [{ name: 'beefmc', jar, sha256, source: 'test' }],
  }));
  const configPath = await prepareBenchmark(sourceConfig, testRoot);
  const config = JSON.parse(await readFile(configPath, 'utf8'));
  const instance = config.variants[0].instanceDirectory;
  const properties = await readFile(join(instance, 'server.properties'), 'utf8');
  assert.match(properties, /^server-ip=127\.0\.0\.1$/m);
  assert.match(properties, /^online-mode=false$/m);
  assert.match(properties, /^white-list=true$/m);
  await assert.rejects(access(join(instance, 'eula.txt')));
  const whitelist = JSON.parse(await readFile(join(instance, 'whitelist.json'), 'utf8'));
  assert.equal(whitelist[0].name, 'beefbench_001');
  assert.equal(config.variants[0].sha256, sha256);
});

test('refuses source artifacts outside Test Server', async t => {
  const root = await mkdtemp(join(tmpdir(), 'beefbench-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const testRoot = join(root, 'Test Server');
  await mkdir(testRoot);
  const sourceConfig = join(root, 'source.json');
  await writeFile(sourceConfig, JSON.stringify({ version: '1.21.11', variants: [{ name: 'bad', jar: join(root, 'outside.jar'), sha256: '0'.repeat(64) }] }));
  await assert.rejects(prepareBenchmark(sourceConfig, testRoot), /Test Server/);
});

test('rejects variant names that escape the Test Server instance root', async t => {
  const root = await mkdtemp(join(tmpdir(), 'beefbench-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const testRoot = join(root, 'Test Server');
  const artifacts = join(testRoot, 'artifacts');
  await mkdir(artifacts, { recursive: true });
  const jar = join(artifacts, 'fixture.jar');
  await writeFile(jar, 'fixture');
  const sourceConfig = join(root, 'source.json');
  await writeFile(sourceConfig, JSON.stringify({
    version: '1.21.11', port: 25565, botCount: 1,
    variants: [{ name: '../../../outside', jar, sha256: createHash('sha256').update('fixture').digest('hex') }],
  }));
  await assert.rejects(prepareBenchmark(sourceConfig, testRoot), /variant name/);
});
