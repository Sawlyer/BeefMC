import { copyFile, lstat, mkdir, readFile, realpath, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve, join, relative, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { resolveWithinRoot } from './lib/paths.mjs';
import { acquireRunLocks } from './lib/locks.mjs';

async function safeDestination(root, path, label) {
  const safe = await resolveWithinRoot(root, path, label);
  try {
    const info = await lstat(path);
    if (info.isSymbolicLink() || !info.isFile()) throw new Error(label + ' must be a regular file destination');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  return safe;
}

function offlineUuid(name) {
  const bytes = createHash('md5').update('OfflinePlayer:' + name, 'utf8').digest();
  bytes[6] = (bytes[6] & 0x0f) | 0x30;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = bytes.toString('hex');
  return hex.slice(0, 8) + '-' + hex.slice(8, 12) + '-' + hex.slice(12, 16) + '-' + hex.slice(16, 20) + '-' + hex.slice(20);
}

async function digest(path) {
  const hash = createHash('sha256');
  hash.update(await readFile(path));
  return hash.digest('hex');
}

export async function prepareBenchmark(sourceConfigPath, testServerRoot) {
  const root = await realpath(testServerRoot);
  if (!root.split(/[\\/]+/).some(part => part.toLowerCase() === 'test server')) throw new Error('Destination must be the Test Server directory');
  const repoRoot = await realpath(resolve(import.meta.dirname, '../..'));
  const repoRelative = relative(repoRoot, root);
  if (repoRelative === '' || (!repoRelative.startsWith('..' + sep) && repoRelative !== '..')) {
    throw new Error('Test Server must be outside the Git repository');
  }
  const source = JSON.parse(await readFile(sourceConfigPath, 'utf8'));
  if (!['1.8.8', '1.21.11', '26.1.2', '26.3'].includes(source.version)) throw new Error('Unsupported Minecraft version');
  if (!Array.isArray(source.variants) || source.variants.length === 0) throw new Error('Config needs at least one variant');
  const port = Number(source.port ?? 25565);
  const botCount = Number(source.botCount ?? 1);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid local port');
  if (!Number.isInteger(botCount) || botCount < 1 || botCount > 100) throw new Error('Invalid bot count');
  const names = new Set();
  for (const variant of source.variants) {
    if (typeof variant.name !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,31}$/.test(variant.name) || names.has(variant.name)) {
      throw new Error('variant name must be unique and use only lowercase letters, digits, hyphen, or underscore');
    }
    names.add(variant.name);
  }
  const config = {
    ...source,
    testServerRoot: root,
    host: '127.0.0.1',
    port,
    outputDirectory: join(root, 'results'),
    worldSnapshot: join(root, 'world-snapshots', source.version, 'baseline'),
    variants: [],
  };
  const instanceDirectories = source.variants.map(variant => join(root, 'instances', source.version, variant.name));
  const releaseLocks = await acquireRunLocks(root, port, instanceDirectories);

  try {
  for (const variant of source.variants) {
    const sourceJar = await resolveWithinRoot(root, variant.jar, 'artifact');
    const actualHash = await digest(sourceJar);
    if (actualHash.toLowerCase() !== String(variant.sha256).toLowerCase()) throw new Error('SHA-256 mismatch for artifact ' + variant.name);
    const instanceDirectory = await resolveWithinRoot(root, join(root, 'instances', source.version, variant.name), 'instance directory');
    await mkdir(instanceDirectory, { recursive: true });
    const jar = await safeDestination(root, join(instanceDirectory, 'server.jar'), 'server JAR destination');
    await copyFile(sourceJar, jar);
    const properties = [
      'server-ip=127.0.0.1', 'server-port=' + port, 'online-mode=false',
      'white-list=true', 'enforce-whitelist=true', 'max-players=' + Math.max(botCount + 5, 10),
      'spawn-protection=0', 'view-distance=6', 'simulation-distance=6',
      'level-name=world', 'level-seed=' + (source.seed ?? 415862303601748),
      'level-type=minecraft:normal', 'enable-query=false', 'enable-rcon=false',
      'motd=BeefMC local benchmark',
    ].join('\n') + '\n';
    await writeFile(await safeDestination(root, join(instanceDirectory, 'server.properties'), 'server.properties destination'), properties, 'utf8');
    const whitelist = Array.from({ length: botCount }, (_, index) => {
      const name = 'beefbench_' + String(index + 1).padStart(3, '0');
      return { uuid: offlineUuid(name), name };
    });
    await writeFile(await safeDestination(root, join(instanceDirectory, 'whitelist.json'), 'whitelist destination'), JSON.stringify(whitelist, null, 2) + '\n', 'utf8');
    config.variants.push({ ...variant, jar, instanceDirectory, sha256: actualHash });
  }

  const configDirectory = await resolveWithinRoot(root, join(root, 'config'), 'config directory');
  await mkdir(configDirectory, { recursive: true });
  const configPath = await safeDestination(root, join(configDirectory, 'benchmark-' + source.version + '.json'), 'config file');
  await writeFile(configPath, JSON.stringify(config, null, 2) + '\n', 'utf8');
  return configPath;
  } finally {
    await releaseLocks();
  }
}

async function main() {
  const [sourceConfigPath, testServerRoot] = process.argv.slice(2);
  if (!sourceConfigPath || !testServerRoot) throw new Error('Usage: node scripts/benchmark/prepare.mjs <source-config.json> <Test Server directory>');
  const path = await prepareBenchmark(sourceConfigPath, testServerRoot);
  process.stdout.write('Prepared local benchmark config: ' + path + '\n');
  process.stdout.write('EULA was not created or changed. Review Mojang EULA and set eula=true manually only if accepted.\n');
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => {
    process.stderr.write('prepare failed: ' + error.message + '\n');
    process.exitCode = 1;
  });
}
