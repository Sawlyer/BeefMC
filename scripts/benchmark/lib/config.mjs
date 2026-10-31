import { readFile } from 'node:fs/promises';
import { isAbsolute } from 'node:path';

export const SUPPORTED_VERSIONS = Object.freeze({
  '1.8.8': 8,
  '1.21.11': 21,
  '26.1.2': 25,
  '26.3': 25,
});

export function validateConfig(config) {
  if (!config || typeof config !== 'object') throw new TypeError('Config must be an object');
  const expectedJava = SUPPORTED_VERSIONS[config.version];
  if (!expectedJava) throw new Error(`Unsupported Minecraft version: ${config.version}`);
  if (config.runtimeJava !== expectedJava) throw new Error(`runtimeJava for ${config.version} must be ${expectedJava}`);
  if (config.host !== '127.0.0.1') throw new Error('host must be exactly 127.0.0.1');
  for (const key of ['javaExecutable', 'testServerRoot', 'worldSnapshot', 'outputDirectory']) {
    if (typeof config[key] !== 'string' || !isAbsolute(config[key])) throw new Error(`${key} must be an absolute path`);
  }
  if (!Number.isInteger(config.port) || config.port < 1024 || config.port > 65535) throw new Error('port must be an integer between 1024 and 65535');
  if (!Number.isInteger(config.botCount) || config.botCount < 1 || config.botCount > 100) throw new Error('botCount must be an integer from 1 to 100');
  for (const key of ['warmupSeconds', 'sampleSeconds', 'repetitions']) {
    if (!Number.isInteger(config[key]) || config[key] < (key === 'warmupSeconds' ? 0 : 1)) throw new Error(`${key} must be a valid positive integer`);
  }
  if (!Array.isArray(config.variants) || config.variants.length === 0) throw new Error('variants must contain at least one artifact');
  const names = new Set();
  for (const variant of config.variants) {
    if (!variant || typeof variant.name !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,31}$/.test(variant.name) || names.has(variant.name)) throw new Error('variant names must be safe, non-empty, and unique');
    names.add(variant.name);
    if (typeof variant.jar !== 'string' || !isAbsolute(variant.jar)) throw new Error(`variant ${variant.name} jar must be an absolute path`);
    if (typeof variant.instanceDirectory !== 'string' || !isAbsolute(variant.instanceDirectory)) throw new Error(`variant ${variant.name} instanceDirectory must be an absolute path`);
    if (typeof variant.sha256 !== 'string' || !/^[a-f0-9]{64}$/i.test(variant.sha256)) throw new Error(`variant ${variant.name} requires a valid SHA-256 digest`);
  }
  if (config.scenario && !['steady-world', 'exploration'].includes(config.scenario)) throw new Error('scenario must be steady-world or exploration');
  return config;
}

export async function loadConfig(path) {
  const source = await readFile(path, 'utf8');
  return validateConfig(JSON.parse(source));
}
