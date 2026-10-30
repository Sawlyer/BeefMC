import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { connect, createServer } from 'node:net';
import { once } from 'node:events';
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const [jarArg, javaArg, outputArg, sleepingArg] = process.argv.slice(2);
if (!jarArg || !javaArg || !outputArg || !['true', 'false'].includes(sleepingArg)) {
  console.error('Usage: node scripts/validation/hopper-amount.mjs <server.jar> <java.exe> <new-output-directory> <sleeping-block-entity:true|false>');
  process.exit(2);
}

const jarPath = path.resolve(jarArg);
const javaPath = path.resolve(javaArg);
const instancePath = path.resolve(outputArg);
const sleepingEnabled = sleepingArg === 'true';
const rconPassword = `beefmc-test-${process.pid}`;
const startupTimeoutMs = 180_000;
const serverLogs = [];
let child;
let rcon;

await mkdir(instancePath, { recursive: false });
await copyFile(jarPath, path.join(instancePath, 'server.jar'));
await writeFile(path.join(instancePath, 'eula.txt'), 'eula=true\n');

const serverPort = await reservePort();
const rconPort = await reservePort();
await writeFile(path.join(instancePath, 'server.properties'), [
  `server-port=${serverPort}`,
  'server-ip=127.0.0.1',
  'online-mode=false',
  'spawn-protection=0',
  'view-distance=2',
  'simulation-distance=2',
  'level-name=world',
  'level-seed=415862303601748',
  'enable-rcon=true',
  `rcon.port=${rconPort}`,
  `rcon.password=${rconPassword}`,
  '',
].join('\n'));

try {
  await startServer();
  await stopServer();
  await configureServer();
  await startServer();
  await assertCommand('tick freeze');
  await assertCommand('forceload add 100 100');

  await placeTestHoppers(0);
  const fullTransfer = await stepUntilTransfer();
  assert.deepEqual(fullTransfer, { source: 58, destination: 5 }, `Full-capacity transfer must move five items; observed ${JSON.stringify(fullTransfer)}`);

  await assertCommand('tick freeze');
  await placeTestHoppers(60);
  const partialTransfer = await stepUntilTransfer();
  assert.deepEqual(partialTransfer, { source: 59, destination: 64 }, `Partial transfer must restore uninserted item; observed ${JSON.stringify(partialTransfer)}`);

  console.log(JSON.stringify({ result: 'passed', sleepingBlockEntity: sleepingEnabled, fullTransfer, partialTransfer, instancePath }, null, 2));
} catch (error) {
  console.error(`hopper amount integration failed: ${error.message}`);
  console.error(`Server logs: ${path.join(instancePath, 'logs', 'latest.log')}`);
  console.error(`Test instance retained at ${instancePath}`);
  process.exitCode = 1;
} finally {
  rcon?.close();
  await stopServer().catch(() => {});
}

async function reservePort() {
  const server = createServer();
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  return port;
}

async function startServer() {
  serverLogs.length = 0;
  console.log(`Starting isolated server, sleeping-block-entity=${sleepingEnabled}`);
  child = spawn(javaPath, ['-Xms512M', '-Xmx512M', '-jar', 'server.jar', '--nogui'], {
    cwd: instancePath,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.setEncoding('utf8').on('data', recordLogs);
  child.stderr.setEncoding('utf8').on('data', recordLogs);
  const deadline = Date.now() + startupTimeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Server exited during startup (${child.exitCode}). Last output: ${serverLogs.slice(-30).join('\n')}`);
    if (serverLogs.some(line => line.includes('Done ('))) {
      for (let attempt = 0; attempt < 40; attempt++) {
        try {
          rcon = await Rcon.connect('127.0.0.1', rconPort, rconPassword);
          return;
        } catch {
          await delay(250);
        }
      }
      throw new Error('Server reached ready state but RCON did not accept connections');
    }
    await delay(250);
  }
  throw new Error(`Server did not reach ready state before timeout. Last output: ${serverLogs.slice(-30).join('\n')}`);
}

function recordLogs(text) {
  serverLogs.push(...text.split(/\r?\n/).filter(Boolean));
  if (serverLogs.length > 300) serverLogs.splice(0, serverLogs.length - 300);
}

async function stopServer() {
  if (!child) return;
  if (child.exitCode !== null) {
    child = undefined;
    return;
  }
  const processToStop = child;
  const exited = once(processToStop, 'exit');
  if (rcon) {
    await rcon.command('stop').catch(() => {});
    rcon.close();
    rcon = undefined;
  } else {
    processToStop.kill('SIGTERM');
  }
  const stopped = await Promise.race([exited.then(() => true), delay(10_000).then(() => false)]);
  if (!stopped) {
    processToStop.kill('SIGKILL');
    await exited;
  }
  child = undefined;
}

async function configureServer() {
  const globalConfigPath = path.join(instancePath, 'config', 'beefmc-global.yml');
  const spigotConfigPath = path.join(instancePath, 'spigot.yml');
  let globalConfig = await readFile(globalConfigPath, 'utf8');
  const setting = /(^[ \t]*sleeping-block-entity:\s*)(?:true|false)(\s*(?:#.*)?$)/m;
  assert.match(globalConfig, setting, 'BeefMC global config must expose sleeping-block-entity');
  globalConfig = globalConfig.replace(setting, `$1${sleepingEnabled}$2`);
  await writeFile(globalConfigPath, globalConfig);

  let spigotConfig = await readFile(spigotConfigPath, 'utf8');
  spigotConfig = replaceConfigNumber(spigotConfig, 'hopper-transfer', 8);
  spigotConfig = replaceConfigNumber(spigotConfig, 'hopper-amount', 5);
  await writeFile(spigotConfigPath, spigotConfig);
}

function replaceConfigNumber(contents, key, value) {
  const pattern = new RegExp(`(^[ \\t]*${key}:\\s*)\\d+`, 'm');
  assert.match(contents, pattern, `spigot.yml must expose ${key}`);
  return contents.replace(pattern, `$1${value}`);
}

async function assertCommand(command) {
  const result = await rcon.command(command);
  if (/unknown command|error executing|failed/i.test(result)) throw new Error(`${command}: ${result}`);
  return result;
}

async function placeTestHoppers(destinationCount) {
  await assertCommand('setblock 100 64 100 minecraft:air');
  await assertCommand('setblock 101 64 100 minecraft:air');
  await assertCommand('setblock 101 64 99 minecraft:stone');
  await assertCommand('setblock 100 64 100 minecraft:hopper[facing=east]');
  await assertCommand('setblock 101 64 100 minecraft:hopper[facing=north]');
  await assertCommand('item replace block 100 64 100 container.0 with minecraft:stone 63');
  if (destinationCount > 0) {
    await assertCommand(`item replace block 101 64 100 container.0 with minecraft:stone ${destinationCount}`);
  }
  const source = await readCount(100, 64, 100);
  const destination = await readCount(101, 64, 100);
  assert.equal(source, 63, 'Source inventory setup failed');
  assert.equal(destination, destinationCount, 'Destination inventory setup failed');
}

async function stepUntilTransfer() {
  for (let tick = 0; tick < 24; tick++) {
    await assertCommand('tick step 1');
    const source = await readCount(100, 64, 100);
    const destination = await readCount(101, 64, 100);
    if (source !== 63 || destination !== 0 && destination !== 60) return { source, destination };
  }
  throw new Error('Hopper did not transfer any items after 24 manual ticks');
}

async function readCount(x, y, z) {
  const data = await rcon.command(`data get block ${x} ${y} ${z} Items`);
  const match = data.match(/(?:count|Count):\s*(\d+)/);
  return match ? Number(match[1]) : 0;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

class Rcon {
  #socket;
  #nextId = 1;
  #buffer = Buffer.alloc(0);
  #pending = new Map();

  static async connect(host, port, password) {
    const client = new Rcon();
    client.#socket = (await new Promise((resolve, reject) => {
      const netSocket = connect(port, host);
      netSocket.once('connect', () => resolve(netSocket));
      netSocket.once('error', reject);
    }));
    client.#socket.on('data', chunk => client.#receive(chunk));
    const auth = await client.#send(3, password);
    if (auth.id === -1) throw new Error('RCON authentication rejected');
    return client;
  }

  command(command) {
    return this.#send(2, command).then(response => response.body);
  }

  close() {
    this.#socket?.destroy();
  }

  #send(type, body) {
    const id = this.#nextId++;
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.#pending.delete(id);
        reject(new Error(`RCON request timed out: ${body}`));
      }, 10_000);
      this.#pending.set(id, { resolve, reject, timeout });
      const payload = Buffer.from(body, 'utf8');
      const length = 4 + 4 + payload.length + 2;
      const packet = Buffer.alloc(4 + length);
      packet.writeInt32LE(length, 0);
      packet.writeInt32LE(id, 4);
      packet.writeInt32LE(type, 8);
      payload.copy(packet, 12);
      this.#socket.write(packet);
    });
  }

  #receive(chunk) {
    this.#buffer = Buffer.concat([this.#buffer, chunk]);
    while (this.#buffer.length >= 4) {
      const length = this.#buffer.readInt32LE(0);
      if (this.#buffer.length < length + 4) return;
      const id = this.#buffer.readInt32LE(4);
      const body = this.#buffer.subarray(12, length + 2).toString('utf8');
      this.#buffer = this.#buffer.subarray(length + 4);
      const pending = this.#pending.get(id);
      if (!pending) continue;
      clearTimeout(pending.timeout);
      this.#pending.delete(id);
      pending.resolve({ id, body });
    }
  }
}
