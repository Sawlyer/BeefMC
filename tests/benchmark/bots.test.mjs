import test from 'node:test';
import assert from 'node:assert/strict';
import { parseBotArgs } from '../../scripts/benchmark/lib/bot-options.mjs';

test('parses bounded loopback workload and pins client protocol', () => {
  const options = parseBotArgs(['--version', '1.21.11', '--host', '127.0.0.1', '--port', '25565', '--count', '10', '--scenario', 'steady-world', '--seed', '42']);
  assert.equal(options.clientVersion, '1.21.11');
  assert.equal(options.count, 10);
  assert.equal(options.bridgeRequired, false);
});

test('rejects external hosts, missing values, and invalid counts', () => {
  assert.throws(() => parseBotArgs(['--version', '1.21.11', '--host', 'example.com', '--port', '25565', '--count', '1']), /127\.0\.0\.1/);
  assert.throws(() => parseBotArgs(['--version', '1.21.11', '--host', '127.0.0.1', '--port', '25565', '--count', '0']), /count/);
  assert.throws(() => parseBotArgs(['--version']), /value/);
});

test('routes 26.3 bot traffic through a local compatibility bridge', () => {
  const options = parseBotArgs(['--version', '26.3', '--host', '127.0.0.1', '--port', '25568', '--count', '1', '--scenario', 'steady-world', '--seed', '1']);
  assert.equal(options.clientVersion, '26.1');
  assert.equal(options.bridgeRequired, true);
});
