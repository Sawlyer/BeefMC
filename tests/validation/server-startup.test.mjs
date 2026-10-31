import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { runStartupSmoke } from '../../scripts/validation/server-startup.mjs';

test('accepts EULA, waits for server readiness, then stops cleanly', async () => {
  const directory = await mkdtemp(path.join(tmpdir(), 'beefmc-startup-'));
  let child;
  let args;
  let options;

  try {
    const result = await runStartupSmoke({
      javaPath: 'java-test-double',
      jarPath: 'beefmc-test.jar',
      directory,
      spawnProcess: (_java, receivedArgs, receivedOptions) => {
        args = receivedArgs;
        options = receivedOptions;
        child = new EventEmitter();
        child.stdout = new PassThrough();
        child.stderr = new PassThrough();
        child.stdin = new PassThrough();
        child.kill = () => true;
        child.stdin.on('data', (data) => {
          if (data.toString().includes('stop')) {
            queueMicrotask(() => child.emit('exit', 0, null));
          }
        });
        queueMicrotask(() => child.stdout.write('Done (1.2s)! For help, type "help"\n'));
        return child;
      },
      readyTimeoutMs: 1000,
      shutdownTimeoutMs: 1000,
    });

    assert.deepEqual(args, ['-jar', 'beefmc-test.jar', '--nogui']);
    assert.equal(options.cwd, directory);
    assert.match(await readFile(path.join(directory, 'eula.txt'), 'utf8'), /eula=true/);
    assert.equal(result.exitCode, 0);
    assert.match(result.log, /Done \(/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
