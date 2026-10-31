import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createInterface } from 'node:readline';

async function withTimeout(promise, milliseconds, message) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(message)), milliseconds);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

test('bot subprocess exits promptly when stopped before its duration timer', async () => {
  const botModule = new URL('../../scripts/benchmark/bots.mjs', import.meta.url).href;
  const program = `
    import { EventEmitter } from 'node:events';
    import { runBots } from ${JSON.stringify(botModule)};
    class FakeBot extends EventEmitter {
      constructor() {
        super();
        setImmediate(() => { this.emit('login'); this.emit('spawn'); });
      }
      setControlState() {}
      quit() { this.emit('end', 'quit'); }
    }
    await runBots({ count: 1, host: '127.0.0.1', port: 25565, clientVersion: '1.21.11', scenario: 'steady-world', seed: 1, durationSeconds: 60 }, () => new FakeBot());
  `;
  const child = spawn(process.execPath, ['--input-type=module', '-e', program], {
    cwd: process.cwd(),
    windowsHide: true,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  const lines = createInterface({ input: child.stdout });
  const ready = new Promise(resolve => {
    lines.on('line', line => {
      const event = JSON.parse(line);
      if (event.type === 'all-spawned') {
        child.stdin.write('stop\n');
        resolve();
      }
    });
  });
  const exited = once(child, 'exit').then(([code, signal]) => ({ code, signal }));

  try {
    await withTimeout(ready, 3000, 'Bot child did not finish startup');
    const result = await withTimeout(exited, 2000, 'Bot child did not exit after stop request');
    assert.deepEqual(result, { code: 0, signal: null });
  } finally {
    lines.close();
    if (child.exitCode === null && child.signalCode === null) {
      child.kill();
      await exited;
    }
  }
});
