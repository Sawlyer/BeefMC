import { cp, mkdir, readdir, access, writeFile } from 'node:fs/promises';
import { resolve, join, relative, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import { realpath } from 'node:fs/promises';
import { loadConfig } from './lib/config.mjs';
import { assertPortAvailable, preflightInstance, startServer, stopServer, waitForServerReady } from './lib/server.mjs';
import { resolveWithinRoot } from './lib/paths.mjs';
import { acquireRunLocks } from './lib/locks.mjs';

async function assertTestServerPath(root, path, label) {
  const absolute = await resolveWithinRoot(root, path, label);
  const repoPath = resolve(import.meta.dirname, '../..');
  const rel = relative(repoPath, absolute);
  if (!rel.startsWith('..' + sep) && rel !== '..') throw new Error(label + ' must stay outside Git');
  return absolute;
}

export async function bootstrapWorld(config, variantName) {
  config.testServerRoot = await realpath(config.testServerRoot);
  const variant = config.variants.find(item => item.name === variantName);
  if (!variant) throw new Error('Unknown variant: ' + variantName);
  const instanceDirectory = await assertTestServerPath(config.testServerRoot, variant.instanceDirectory, 'instance directory');
  const snapshotDirectory = await assertTestServerPath(config.testServerRoot, config.worldSnapshot, 'world snapshot');
  const lockRelease = await acquireRunLocks(config.testServerRoot, config.port, [instanceDirectory]);
  let server;
  let javaRuntime;
  try {
    try {
      const preflight = await preflightInstance({ ...config, ...variant, instanceDirectory, javaExecutable: resolve(config.javaExecutable) });
      javaRuntime = preflight.runtime;
      const existingWorlds = (await readdir(instanceDirectory, { withFileTypes: true }))
        .filter(item => (item.isDirectory() || item.isSymbolicLink()) && (item.name === 'world' || item.name.startsWith('world_')));
      if (existingWorlds.length) throw new Error('Bootstrap refuses to overwrite existing world data in the selected instance');
      try {
        await access(join(snapshotDirectory, 'snapshot.json'));
        throw new Error('A world snapshot already exists; bootstrap refuses to overwrite it');
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      await assertPortAvailable('127.0.0.1', config.port);
      server = startServer({ ...config, ...variant, instanceDirectory, javaExecutable: resolve(config.javaExecutable) });
      server.stdout.on('data', () => {});
      server.stderr.on('data', () => {});
      await waitForServerReady(server, '127.0.0.1', config.port);
      await delay((config.worldBootstrapSeconds ?? 60) * 1000);
      server.stdin.write('save-all flush\n');
      await delay(3000);
    } finally {
      if (server) {
        const stop = await stopServer(server);
        if (!stop.graceful) throw new Error('World bootstrap server required forced stop');
      }
    }
    const names = await readdir(instanceDirectory, { withFileTypes: true });
    const worlds = names.filter(item => item.isDirectory() && (item.name === 'world' || item.name.startsWith('world_')));
    if (!worlds.some(item => item.name === 'world')) throw new Error('Server did not create its world folder');
    await mkdir(snapshotDirectory, { recursive: true });
    await assertTestServerPath(config.testServerRoot, snapshotDirectory, 'world snapshot');
    for (const world of worlds) {
      const source = await assertTestServerPath(config.testServerRoot, join(instanceDirectory, world.name), 'source world');
      const destination = await assertTestServerPath(config.testServerRoot, join(snapshotDirectory, world.name), 'snapshot world');
      await cp(source, destination, { recursive: true, force: false, errorOnExist: true });
    }
    const manifestPath = await assertTestServerPath(config.testServerRoot, join(snapshotDirectory, 'snapshot.json'), 'snapshot manifest');
    await writeFile(manifestPath, JSON.stringify({
    version: config.version,
    sourceVariant: variant.name,
    artifactSha256: variant.sha256,
    javaRuntime,
      seed: config.seed,
      createdAt: new Date().toISOString(),
      bootstrapSeconds: config.worldBootstrapSeconds ?? 60,
    }, null, 2) + '\n');
    return snapshotDirectory;
  } finally {
    await lockRelease();
  }
}

async function main() {
  const [configPath, variantName] = process.argv.slice(2);
  if (!configPath || !variantName) throw new Error('Usage: node scripts/benchmark/bootstrap-world.mjs <config.json> <variant>');
  const path = await bootstrapWorld(await loadConfig(configPath), variantName);
  process.stdout.write('Created shared world snapshot: ' + path + '\n');
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => {
    process.stderr.write('world bootstrap failed: ' + error.message + '\n');
    process.exitCode = 1;
  });
}
