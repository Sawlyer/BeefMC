import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import net from 'node:net';
import { assertPortAvailable, waitForServerReady } from '../../scripts/benchmark/lib/server.mjs';

test('rejects an already occupied loopback server port', async t => {
  const listener = net.createServer();
  await new Promise(resolve => listener.listen(0, '127.0.0.1', resolve));
  t.after(() => listener.close());
  await assert.rejects(assertPortAvailable('127.0.0.1', listener.address().port), /already occupied/);
});

test('does not treat an unrelated listener as the benchmark server readiness signal', async t => {
  const listener = net.createServer();
  await new Promise(resolve => listener.listen(0, '127.0.0.1', resolve));
  t.after(() => listener.close());
  const child = new EventEmitter();
  child.stdout = new PassThrough();
  child.stderr = new PassThrough();
  child.exitCode = null;
  const pending = waitForServerReady(child, '127.0.0.1', listener.address().port, 400);
  setTimeout(() => child.stdout.write('Done (0.1s)! For help\n'), 50);
  await pending;
});
