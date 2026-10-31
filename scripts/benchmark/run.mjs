import { createWriteStream } from 'node:fs';
import { mkdir as mkdirAsync, realpath, stat as statAsync, writeFile as writeFileAsync } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';
import { join, resolve, relative, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { hostname, cpus, totalmem, platform, release } from 'node:os';
import { loadConfig } from './lib/config.mjs';
import { assertPortAvailable, copyWorldSnapshot, preflightInstance, startServer, stopServer, waitForServerReady } from './lib/server.mjs';
import { deriveCpu, parseMsptOutputLine, samplesToCsv, startJstatSampler, startWindowsSampler } from './lib/metrics.mjs';
import { jfrStartupArgument, readJfrGcHeapSummaries } from './lib/profiler.mjs';
import { resolveWithinRoot } from './lib/paths.mjs';
import { acquireRunLocks } from './lib/locks.mjs';

async function assertTestServerPath(root, path, label) {
  const absolute = await resolveWithinRoot(root, path, label);
  const repoPath = resolve(import.meta.dirname, '../..').toLowerCase();
  const rel = relative(repoPath, absolute);
  if (!rel.startsWith('..' + sep) && rel !== '..') throw new Error('Benchmark output and instances must stay outside the Git repository');
  return absolute;
}

function rotate(values, offset) {
  const index = offset % values.length;
  return [...values.slice(index), ...values.slice(0, index)];
}

async function waitForBotSpawn(child, logStream, timeoutMs = 120_000) {
  let buffer = '';
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      child.removeListener('error', onError);
      if (error) reject(error);
      else resolve(value);
    };
    const timeout = setTimeout(() => finish(new Error('Bots did not all join before timeout')), timeoutMs);
    const onError = error => finish(new Error('Bot process failed to start: ' + error.message));
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', chunk => {
      logStream.write(chunk);
      buffer += chunk;
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        try {
          const event = JSON.parse(line);
          if (event.type === 'all-spawned') finish(null, event);
          if (event.type === 'failure') finish(new Error(event.error));
        } catch {}
      }
    });
    child.stderr.on('data', chunk => logStream.write(chunk));
    child.once('error', onError);
    child.once('exit', code => {
      finish(new Error(`Bot process exited before all bots joined (code ${code})`));
    });
  });
}

async function runOne(config, variant, repetition, orderIndex) {
  const root = config.testServerRoot;
  const instanceDirectory = await assertTestServerPath(root, variant.instanceDirectory, 'instance directory');
  const jar = await assertTestServerPath(root, variant.jar, 'server JAR');
  const outputDirectory = await assertTestServerPath(root, config.outputDirectory, 'results directory');
  const worldSnapshot = await assertTestServerPath(root, config.worldSnapshot, 'world snapshot');
  const javaExecutable = resolve(config.javaExecutable);
  const runId = `${config.version}-${variant.name}-r${repetition}-${Date.now()}`;
  let runDirectory = join(outputDirectory, config.version, runId);
  await mkdirAsync(runDirectory, { recursive: true });
  runDirectory = await assertTestServerPath(root, runDirectory, 'run directory');
  const serverLog = createWriteStream(join(runDirectory, 'server.log'), { flags: 'wx' });
  const botLog = createWriteStream(join(runDirectory, 'bots.jsonl'), { flags: 'wx' });
    let server, bots, jstat, sampler, preflight, botInfo;
  let rows = [];
    let tickMetrics = [];
    let jfrHeapSummaries = [];
  let sampleStart, sampleEnd;
    let msptTimer;
    let collectingMspt = false;
    let awaitingMsptValues = false;
    let serverOutputBuffer = '';
    const jfrFilename = config.recordJfr ? join(runDirectory, 'profile.jfr') : null;
    const jfrArgument = jfrFilename ? jfrStartupArgument(jfrFilename) : null;
    let jfrResult = { status: config.recordJfr ? 'pending' : 'not-requested', filename: jfrFilename, error: null };
  let status = 'running';
  let errorMessage = null;
  let cleanupStatus = null;
  try {
    preflight = await preflightInstance({ ...config, ...variant, instanceDirectory, jar, javaExecutable });
    await copyWorldSnapshot(instanceDirectory, worldSnapshot);
    await assertPortAvailable('127.0.0.1', config.port);
      const jvmArgs = jfrArgument ? [...(config.jvmArgs ?? []), jfrArgument] : config.jvmArgs;
      server = startServer({ ...config, ...variant, instanceDirectory, jar, javaExecutable, jvmArgs });
      if (jfrArgument) jfrResult.status = 'recording-from-startup';
    server.stdout.pipe(serverLog, { end: false });
    server.stderr.pipe(serverLog, { end: false });
    await waitForServerReady(server, '127.0.0.1', config.port);
      server.stdout.setEncoding('utf8');
      server.stdout.on('data', chunk => {
        serverOutputBuffer += chunk;
        const lines = serverOutputBuffer.split(/\r?\n/);
        serverOutputBuffer = lines.pop() ?? '';
        for (const line of lines) {
          if (line.includes('Server tick times')) {
            awaitingMsptValues = true;
            continue;
          }
          if (!awaitingMsptValues) continue;
          awaitingMsptValues = false;
          const parsed = parseMsptOutputLine(line);
          if (collectingMspt && parsed) tickMetrics.push({ sampledAt: new Date().toISOString(), ...parsed });
        }
      });
    jstat = startJstatSampler(javaExecutable, server.pid, config.sampleIntervalMs ?? 1000);
    const botPort = config.botPort ?? config.port;
    bots = spawn(process.execPath, [
      join(import.meta.dirname, 'bots.mjs'),
      '--version', config.version,
      '--host', '127.0.0.1',
      '--port', String(botPort),
      '--count', String(config.botCount),
      '--scenario', config.scenario ?? 'steady-world',
      '--seed', String(config.seed ?? 42),
      '--duration-seconds', String(config.warmupSeconds + config.sampleSeconds + 60),
    ], { cwd: import.meta.dirname, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
    botInfo = await waitForBotSpawn(bots, botLog);
    const roleByPid = new Map([[server.pid, 'server'], [bots.pid, 'bots']]);
    if (jstat.child?.pid) roleByPid.set(jstat.child.pid, 'jstat');
    sampler = startWindowsSampler([...roleByPid.keys()], config.sampleIntervalMs ?? 1000);
    if (sampler.child.pid) roleByPid.set(sampler.child.pid, 'sampler');
    await delay(config.warmupSeconds * 1000);
    sampleStart = Date.now();
      if (config.collectMspt) {
        collectingMspt = true;
        const requestMspt = () => {
          if (server.exitCode === null) server.stdin.write('mspt\n');
        };
        requestMspt();
        msptTimer = setInterval(requestMspt, config.msptIntervalMs ?? 15_000);
      }
    await delay(config.sampleSeconds * 1000);
    sampleEnd = Date.now();
      collectingMspt = false;
      clearInterval(msptTimer);
    if (server.exitCode !== null) throw new Error(`Server exited during sample with code ${server.exitCode}`);
    if (bots.exitCode !== null) throw new Error(`Bot process exited before measured window ended (code ${bots.exitCode})`);
    const raw = sampler.samples.filter(sample => sample.sampledAtMs >= sampleStart && sample.sampledAtMs <= sampleEnd);
    const counts = new Map([...roleByPid.keys()].map(pid => [pid, raw.filter(sample => sample.pid === pid).length]));
    for (const [pid, count] of counts) if (count < 1) throw new Error(`No process samples collected for ${roleByPid.get(pid)} PID ${pid}`);
    const byPid = new Map();
    const jstatRows = jstat?.samples.filter(sample => sample.sampledAtMs >= sampleStart - 2000 && sample.sampledAtMs <= sampleEnd + 2000) ?? [];
    for (const sample of raw.sort((a, b) => a.sampledAtMs - b.sampledAtMs)) {
      const previous = byPid.get(sample.pid);
      const role = roleByPid.get(sample.pid) ?? 'unknown';
      const derived = previous ? deriveCpu(previous, sample, cpus().length) : { cpuCores: null, cpuPercentOfMachine: null };
      const jstatSample = role === 'server'
        ? jstatRows.reduce((closest, current) => !closest || Math.abs(current.sampledAtMs - sample.sampledAtMs) < Math.abs(closest.sampledAtMs - sample.sampledAtMs) ? current : closest, null)
        : null;
      const jstatAvailable = role === 'server' && jstatSample && Math.abs(jstatSample.sampledAtMs - sample.sampledAtMs) <= 2000;
      rows.push({
        runId, repetition, orderIndex, scenario: config.scenario ?? 'steady-world',
        sampledAt: new Date(sample.sampledAtMs).toISOString(), elapsedSeconds: previous ? (sample.sampledAtMs - previous.sampledAtMs) / 1000 : null,
        role, pid: sample.pid, cpuSeconds: sample.cpuSeconds, ...derived,
        workingSetBytes: sample.workingSetBytes, privateBytes: sample.privateBytes,
        heapBytes: jstatAvailable ? jstatSample.heapBytes : null,
        heapUnavailable: jstatAvailable ? null : (role === 'server' ? jstat?.unavailableReason ?? 'jstat unavailable' : 'not a Java server process'),
        gcCount: jstatAvailable ? jstatSample.gcCount : null,
        gcTimeSeconds: jstatAvailable ? jstatSample.gcTimeSeconds : null,
        gcUnavailable: jstatAvailable ? null : (role === 'server' ? jstat?.unavailableReason ?? 'jstat unavailable' : 'not a Java server process'),
        tps: null, tpsUnavailable: 'Spark metrics source not installed',
        mspt: null, msptUnavailable: 'Spark metrics source not installed',
      });
      byPid.set(sample.pid, sample);
    }
    status = 'complete';
  } catch (error) {
    status = 'failed';
    errorMessage = error.stack ?? error.message;
  } finally {
      collectingMspt = false;
      clearInterval(msptTimer);
    if (bots && bots.exitCode === null) {
      bots.stdin.write('stop\n');
      await Promise.race([once(bots, 'exit'), delay(10_000)]);
      if (bots.exitCode === null) {
        bots.kill();
        status = 'failed';
        errorMessage ??= 'Bot process required forced stop';
      }
    }
    if (jstat) await jstat.stop();
    if (sampler) await sampler.stop();
    if (server) {
      cleanupStatus = await stopServer(server);
      if (!cleanupStatus.graceful) {
        status = 'failed';
        errorMessage ??= 'Server required forced stop';
      }
    }
      if (jfrArgument) {
        const profileFile = await statAsync(jfrFilename).catch(() => null);
        jfrResult = profileFile
          ? { status: 'complete', filename: jfrFilename, sizeBytes: profileFile.size, includesStartupAndWarmup: true, sampledWindowStart: sampleStart ? new Date(sampleStart).toISOString() : null, sampledWindowEnd: sampleEnd ? new Date(sampleEnd).toISOString() : null, error: null }
          : { status: 'failed', filename: jfrFilename, includesStartupAndWarmup: true, sampledWindowStart: sampleStart ? new Date(sampleStart).toISOString() : null, sampledWindowEnd: sampleEnd ? new Date(sampleEnd).toISOString() : null, error: 'JFR output file missing after server shutdown' };
        if (profileFile && sampleStart && sampleEnd) {
          const parsedHeap = readJfrGcHeapSummaries(javaExecutable, jfrFilename, sampleStart, sampleEnd);
          jfrHeapSummaries = parsedHeap.samples;
          jfrResult.heapAfterGcSamples = jfrHeapSummaries.length;
          jfrResult.heapSummaryError = parsedHeap.error;
        }
      }
    serverLog.end();
    botLog.end();
    const measurements = {
      rawProcessSamples: rows.length,
      serverSamples: rows.filter(row => row.role === 'server').length,
      botSamples: rows.filter(row => row.role === 'bots').length,
      jstatSamples: rows.filter(row => row.role === 'jstat').length,
      processSampling: 'Windows process CPU time, working set, and private bytes sampled once per second',
      heap: rows.some(row => Number.isFinite(row.heapBytes)) ? 'available from jstat' : jfrHeapSummaries.length ? 'available as JFR after-GC snapshots' : 'unavailable',
      gc: rows.some(row => Number.isFinite(row.gcCount)) || jfrHeapSummaries.length ? 'available' : 'unavailable',
      heapAfterGcSamples: jfrHeapSummaries.length,
        tps: 'unavailable',
        mspt: tickMetrics.length ? 'available' : 'unavailable',
        msptSamples: tickMetrics.length,
        jfr: jfrResult.status,
    };
    const manifest = {
      status, error: errorMessage, cleanupStatus,
      runId, version: config.version, variant: variant.name, repetition, orderIndex,
      startedAt: sampleStart ? new Date(sampleStart).toISOString() : null,
      endedAt: sampleEnd ? new Date(sampleEnd).toISOString() : null,
      host: { hostname: hostname(), platform: platform(), osRelease: release(), cpuModel: cpus()[0]?.model, logicalCpus: cpus().length, totalMemoryBytes: totalmem() },
      javaExecutable,
      javaVersionExpected: config.runtimeJava,
      javaRuntime: preflight?.runtime ?? null,
      javaExecutableSha256: preflight?.javaExecutableSha256 ?? null,
        jvmArgs: jfrArgument ? [...(config.jvmArgs ?? []), jfrArgument] : config.jvmArgs ?? [],
      artifact: { jar, sha256: preflight?.jarSha256 ?? variant.sha256 ?? null, source: variant.source ?? null, upstreamCommit: variant.upstreamCommit ?? null },
        workload: { scenario: config.scenario ?? 'steady-world', botCount: config.botCount, warmupSeconds: config.warmupSeconds, sampleSeconds: config.sampleSeconds, seed: config.seed ?? 42, recordJfr: Boolean(config.recordJfr), collectMspt: Boolean(config.collectMspt), msptIntervalMs: config.msptIntervalMs ?? 15_000 },
      worldSnapshot,
      botClientVersion: botInfo?.clientVersion ?? null,
        jfr: jfrResult,
        jfrGcHeapSummaries: jfrHeapSummaries,
      measurements,
    };
      await writeFileAsync(join(runDirectory, 'run.json'), JSON.stringify({ manifest, samples: rows, tickMetrics }, null, 2));
    await writeFileAsync(join(runDirectory, 'samples.csv'), samplesToCsv(rows));
      await writeFileAsync(join(runDirectory, 'tick-metrics.csv'), samplesToCsv(tickMetrics));
  }
  if (status !== 'complete') throw new Error(errorMessage ?? 'Benchmark run failed');
  return { runId, runDirectory, status };
}

export async function runBenchmark(config) {
  if (platform() !== 'win32') throw new Error('The approved benchmark harness currently supports Windows only');
  if (!config.testServerRoot) throw new Error('testServerRoot is required');
  config.testServerRoot = await realpath(config.testServerRoot);
  await assertTestServerPath(config.testServerRoot, config.outputDirectory, 'results directory');
  if (!config.javaExecutable) throw new Error('javaExecutable must point to the matching local JDK runtime');
  const instanceDirectories = [];
  for (const variant of config.variants) {
    instanceDirectories.push(await assertTestServerPath(config.testServerRoot, variant.instanceDirectory, 'instance directory'));
  }
  const releaseLocks = await acquireRunLocks(config.testServerRoot, config.port, instanceDirectories);
  try {
    const results = [];
    for (let repetition = 1; repetition <= config.repetitions; repetition += 1) {
      const sequence = rotate(config.variants, repetition - 1);
      for (let index = 0; index < sequence.length; index += 1) {
        results.push(await runOne(config, sequence[index], repetition, index + 1));
      }
    }
    return results;
  } finally {
    await releaseLocks();
  }
}

async function main() {
  try {
    const configPath = process.argv[2];
    if (!configPath) throw new Error('Usage: node scripts/benchmark/run.mjs <absolute-config.json>');
    const config = await loadConfig(configPath);
    const results = await runBenchmark(config);
    process.stdout.write(`${JSON.stringify({ result: 'complete', runs: results.length, results }, null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`benchmark failed: ${error.stack ?? error.message}\n`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) await main();
