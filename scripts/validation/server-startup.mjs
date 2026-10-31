import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const READY_MARKER = /Done \(/;

export async function runStartupSmoke({
  javaPath,
  jarPath,
  directory,
  spawnProcess = spawn,
  readyTimeoutMs = 180_000,
  shutdownTimeoutMs = 30_000,
}) {
  if (!javaPath || !jarPath || !directory) {
    throw new TypeError('javaPath, jarPath, and directory are required');
  }

  await mkdir(directory, { recursive: true });
  await writeFile(path.join(directory, 'eula.txt'), 'eula=true\n');
  await writeFile(
    path.join(directory, 'server.properties'),
    [
      'online-mode=false',
      'server-ip=127.0.0.1',
      'server-port=0',
      'spawn-protection=0',
      'view-distance=3',
      '',
    ].join('\n'),
  );

  return new Promise((resolve, reject) => {
    const child = spawnProcess(javaPath, ['-jar', path.resolve(jarPath), '--nogui'], {
      cwd: directory,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, TERM: 'dumb' },
    });
    let log = '';
    let phase = 'starting';
    let readyTimer;
    let shutdownTimer;
    let settled = false;

    const cleanupTimers = () => {
      clearTimeout(readyTimer);
      clearTimeout(shutdownTimer);
    };
    const fail = (message) => {
      if (settled) return;
      settled = true;
      cleanupTimers();
      child.kill('SIGTERM');
      reject(new Error(`${message}\n${log.slice(-8000)}`));
    };
    const append = (chunk) => {
      log += chunk.toString();
      if (phase !== 'starting' || !READY_MARKER.test(log)) return;

      phase = 'stopping';
      clearTimeout(readyTimer);
      shutdownTimer = setTimeout(() => fail(`Server did not stop within ${shutdownTimeoutMs} ms.`), shutdownTimeoutMs);
      child.stdin.write('stop\n', (error) => {
        if (error) fail(`Could not send stop command: ${error.message}`);
      });
    };

    child.stdout.on('data', append);
    child.stderr.on('data', append);
    child.once('error', (error) => fail(`Could not start server process: ${error.message}`));
    child.once('exit', (code, signal) => {
      if (settled) return;
      if (phase === 'stopping' && code === 0) {
        settled = true;
        cleanupTimers();
        resolve({ exitCode: code, log });
        return;
      }
      fail(`Server exited ${phase === 'starting' ? 'before readiness' : 'without a clean shutdown'} (code=${code}, signal=${signal}).`);
    });
    readyTimer = setTimeout(() => fail(`Server did not become ready within ${readyTimeoutMs} ms.`), readyTimeoutMs);
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const [jarPath, javaPath, directory] = process.argv.slice(2);
  if (!jarPath || !javaPath || !directory) {
    console.error('Usage: node server-startup.mjs <jar> <java> <working-directory>');
    process.exitCode = 2;
  } else {
    runStartupSmoke({ jarPath, javaPath, directory })
      .then(({ log }) => {
        process.stdout.write(log);
        console.log('BeefMC startup and shutdown smoke test passed.');
      })
      .catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
      });
  }
}
