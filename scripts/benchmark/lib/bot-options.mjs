import { SUPPORTED_VERSIONS } from './config.mjs';

const CLIENT_VERSIONS = Object.freeze({
  '1.8.8': '1.8.8',
  '1.21.11': '1.21.11',
  '26.1.2': '26.1',
  '26.3': '26.1',
});

export function parseBotArgs(args) {
  const values = new Map();
  for (let i = 0; i < args.length; i += 1) {
    const key = args[i];
    if (!key.startsWith('--')) throw new Error(`unexpected argument: ${key}`);
    const value = args[++i];
    if (value === undefined || value.startsWith('--')) throw new Error(`missing value for ${key}`);
    values.set(key.slice(2), value);
  }
  const version = values.get('version');
  if (!SUPPORTED_VERSIONS[version]) throw new Error(`unsupported version: ${version}`);
  const host = values.get('host');
  if (host !== '127.0.0.1') throw new Error('host must be exactly 127.0.0.1');
  const port = Number(values.get('port'));
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('port must be an integer between 1024 and 65535');
  const count = Number(values.get('count'));
  if (!Number.isInteger(count) || count < 1 || count > 100) throw new Error('count must be an integer from 1 to 100');
  const scenario = values.get('scenario') ?? 'steady-world';
  if (!['steady-world', 'exploration'].includes(scenario)) throw new Error('scenario must be steady-world or exploration');
  const seed = Number(values.get('seed') ?? '1');
  if (!Number.isSafeInteger(seed)) throw new Error('seed must be an integer');
  const durationSeconds = Number(values.get('duration-seconds') ?? '0');
  if (!Number.isInteger(durationSeconds) || durationSeconds < 0) throw new Error('duration-seconds must be a non-negative integer');
  return {
    version, host, port, count, scenario, seed, durationSeconds,
    clientVersion: CLIENT_VERSIONS[version],
    bridgeRequired: version === '26.3',
  };
}
