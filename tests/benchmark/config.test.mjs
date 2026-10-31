import test from 'node:test';
import assert from 'node:assert/strict';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { validateConfig } from '../../scripts/benchmark/lib/config.mjs';

const testRoot = join(tmpdir(), 'BeefMC Test Server');
const valid = {
  version: '1.21.11',
  runtimeJava: 21,
  javaExecutable: join(tmpdir(), 'jdk', 'bin', 'java.exe'),
  testServerRoot: testRoot,
  worldSnapshot: join(testRoot, 'world-snapshots', '1.21.11', 'baseline'),
  host: '127.0.0.1',
  port: 25565,
  botCount: 1,
  warmupSeconds: 0,
  sampleSeconds: 1,
  repetitions: 1,
  outputDirectory: join(testRoot, 'results'),
  variants: [{ name: 'beefmc', jar: join(testRoot, 'beefmc.jar'), instanceDirectory: join(testRoot, 'instances', 'beefmc'), sha256: 'a'.repeat(64) }],
};

test('accepts valid loopback benchmark config', () => {
  assert.equal(validateConfig(valid), valid);
});

test('rejects non-loopback destinations', () => {
  assert.throws(() => validateConfig({ ...valid, host: '0.0.0.0' }), /127\.0\.0\.1/);
});

test('rejects malformed artifact digest', () => {
  assert.throws(() => validateConfig({ ...valid, variants: [{ ...valid.variants[0], sha256: 'bad' }] }), /SHA-256/);
});

test('rejects unsupported Minecraft versions', () => {
  assert.throws(() => validateConfig({ ...valid, version: '1.20.4' }), /unsupported/i);
});

test('rejects invalid bot counts and sample durations', () => {
  assert.throws(() => validateConfig({ ...valid, botCount: 0 }), /botCount/);
  assert.throws(() => validateConfig({ ...valid, sampleSeconds: 0 }), /sampleSeconds/);
});
