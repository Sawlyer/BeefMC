import { createReadStream } from 'node:fs';
import { cp, lstat, readFile, readdir, rm, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';
import { join } from 'node:path';
import net from 'node:net';
import { resolveWithinRoot } from './paths.mjs';

async function sha256(path) {
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(path)) hash.update(chunk);
  return hash.digest('hex');
}

function properties(source) {
  return new Map(source.split(/\r?\n/).flatMap(line => {
    const value = line.trim();
    if (!value || value.startsWith('#') || value.startsWith('!')) return [];
    const index = value.indexOf('=');
    return index < 0 ? [] : [[value.slice(0, index).trim(), value.slice(index + 1).trim()]];
  }));
}

export async function probeJavaVersion(javaExecutable) {
  const child = spawn(javaExecutable, ['-version'], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '';
  child.stdout.setEncoding('utf8').on('data', chunk => { output += chunk; });
  child.stderr.setEncoding('utf8').on('data', chunk => { output += chunk; });
  let timer;
  let result;
  try {
    result = await Promise.race([
      once(child, 'exit').then(([code]) => ({ code })),
      new Promise((_, reject) => {
        timer = setTimeout(() => {
          child.kill();
          reject(new Error('Timed out querying selected Java runtime'));
        }, 10_000);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
  if (result.code !== 0) throw new Error('Selected Java runtime failed java -version');
  const match = output.match(/version\s+"([^"]+)"/i);
  if (!match) throw new Error('Could not read selected Java runtime version');
  const parts = match[1].split('.');
  const major = parts[0] === '1' ? Number(parts[1]) : Number(parts[0]);
  if (!Number.isInteger(major)) throw new Error('Could not parse selected Java runtime version');
  return { major, version: match[1], raw: output.trim() };
}

export async function preflightInstance(config, { probeJava = probeJavaVersion } = {}) {
  if ((await sha256(config.jar)).toLowerCase() !== config.sha256.toLowerCase()) throw new Error('Artifact SHA-256 does not match manifest');
  for (const [label, path] of [['Java executable', config.javaExecutable], ['server JAR', config.jar]]) {
    let info;
    try { info = await stat(path); } catch { throw new Error(`${label} not found: ${path}`); }
    if (!info.isFile()) throw new Error(`${label} is not a file: ${path}`);
  }
  const eulaPath = join(config.instanceDirectory, 'eula.txt');
  if (config.testServerRoot) {
    for (const [label, path] of [
      ['instance directory', config.instanceDirectory],
      ['server JAR', config.jar],
      ['server.properties', join(config.instanceDirectory, 'server.properties')],
      ['whitelist', join(config.instanceDirectory, 'whitelist.json')],
    ]) {
      await resolveWithinRoot(config.testServerRoot, path, label);
      const info = await lstat(path);
      if (info.isSymbolicLink() || !info.isFile() && !info.isDirectory()) throw new Error(label + ' has an invalid file type');
      if (label !== 'instance directory' && !info.isFile()) throw new Error(label + ' must be a regular file');
    }
    await resolveWithinRoot(config.testServerRoot, eulaPath, 'EULA file');
    let eulaInfo;
    try { eulaInfo = await lstat(eulaPath); } catch { throw new Error('EULA has not been accepted in this isolated test instance'); }
    if (eulaInfo.isSymbolicLink() || !eulaInfo.isFile()) throw new Error('EULA file must be a regular file');
  }
  let eula;
  try { eula = await readFile(eulaPath, 'utf8'); } catch { throw new Error('EULA has not been accepted in this isolated test instance'); }
  if (!/^\s*eula\s*=\s*true\s*$/im.test(eula)) throw new Error('EULA has not been accepted in this isolated test instance');
  const source = await readFile(join(config.instanceDirectory, 'server.properties'), 'utf8');
  const props = properties(source);
  if (props.get('server-ip') !== '127.0.0.1') throw new Error('server.properties server-ip must be 127.0.0.1');
  if (props.get('online-mode') !== 'false') throw new Error('server.properties online-mode must be false for local offline bots');
  if (props.get('white-list') !== 'true' || props.get('enforce-whitelist') !== 'true') throw new Error('server whitelist and enforce-whitelist must be enabled');
  if (Number(props.get('server-port')) !== config.port) throw new Error('server.properties port does not match benchmark config');
  const runtime = await probeJava(config.javaExecutable);
  if (runtime.major !== config.runtimeJava) throw new Error('Selected Java runtime is ' + runtime.major + ', expected Java ' + config.runtimeJava);
  return {
    ok: true,
    jarSha256: config.sha256.toLowerCase(),
    javaExecutableSha256: await sha256(config.javaExecutable),
    eulaAccepted: true,
    host: '127.0.0.1',
    port: config.port,
    runtime,
  };
}

export function startServer(config) {
  return spawn(config.javaExecutable, [
    ...(config.jvmArgs ?? []),
    '-jar', config.jar, '--nogui',
  ], {
    cwd: config.instanceDirectory,
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
  });
}

export async function stopServer(child, timeoutMs = 20_000) {
  if (!child) return { graceful: true, exitCode: null };
  if (child.exitCode !== null || child.signalCode !== null) return { graceful: true, exitCode: child.exitCode };
  const exited = new Promise(resolve => child.once('exit', (code, signal) => resolve({ code, signal })));
  child.stdin?.write('stop\n');
  let timer;
  const result = await Promise.race([
    exited,
    new Promise(resolve => { timer = setTimeout(() => resolve(null), timeoutMs); }),
  ]);
  clearTimeout(timer);
  if (result) return { graceful: true, exitCode: result.code, signal: result.signal };
  child.kill();
  await Promise.race([exited, delay(5_000)]);
  return { graceful: false, exitCode: child.exitCode, signal: child.signalCode };
}

export async function assertPortAvailable(host, port) {
  await new Promise((resolve, reject) => {
    const socket = net.connect({ host, port });
    let settled = false;
    const finish = (error) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      error ? reject(error) : resolve();
    };
    socket.setTimeout(1000);
    socket.once('connect', () => finish(new Error('Local benchmark port is already occupied: ' + host + ':' + port)));
    socket.once('error', error => {
      if (error.code === 'ECONNREFUSED') finish();
      else finish(new Error('Cannot verify local benchmark port: ' + error.message));
    });
    socket.once('timeout', () => finish(new Error('Timed out verifying local benchmark port')));
  });
}

export async function waitForServerReady(child, host, port, timeoutMs = 180_000) {
  let output = '';
  let sawReadyLine = false;
  let spawnError = null;
  const inspect = chunk => {
    output = (output + chunk.toString()).slice(-8192);
    if (/Done \([^)]*\)!/.test(output)) sawReadyLine = true;
  };
  const onError = error => { spawnError = error; };
  child.stdout.on('data', inspect);
  child.stderr.on('data', inspect);
  child.once('error', onError);
  const start = Date.now();
  try {
    while (Date.now() - start < timeoutMs) {
      if (spawnError) throw new Error('Server process failed to start: ' + spawnError.message);
      if (child.exitCode !== null) throw new Error('Server exited before readiness (code ' + child.exitCode + ')');
      if (sawReadyLine) {
        const connected = await new Promise(resolve => {
          const socket = net.connect({ host, port });
          socket.setTimeout(500);
          socket.once('connect', () => { socket.destroy(); resolve(true); });
          socket.once('error', () => resolve(false));
          socket.once('timeout', () => { socket.destroy(); resolve(false); });
        });
        if (connected) return;
      }
      await delay(250);
    }
    throw new Error('Server did not log readiness and open its local port before timeout');
  } finally {
    child.stdout.removeListener('data', inspect);
    child.stderr.removeListener('data', inspect);
    child.removeListener('error', onError);
  }
}

export async function copyWorldSnapshot(instanceDirectory, snapshotDirectory) {
  const names = (await readdir(snapshotDirectory, { withFileTypes: true }))
    .filter(item => item.isDirectory() && (item.name === 'world' || item.name.startsWith('world_')))
    .map(item => item.name);
  if (!names.includes('world')) throw new Error('World snapshot must contain a world directory');
  const existing = (await readdir(instanceDirectory, { withFileTypes: true }))
    .filter(item => (item.isDirectory() || item.isSymbolicLink()) && (item.name === 'world' || item.name.startsWith('world_')));
  for (const item of existing) await rm(join(instanceDirectory, item.name), { recursive: true, force: true });
  for (const name of ['world', ...names.filter(name => name !== 'world')]) {
    const source = join(snapshotDirectory, name);
    const target = join(instanceDirectory, name);
    await cp(source, target, { recursive: true, force: true });
  }
  return names;
}
