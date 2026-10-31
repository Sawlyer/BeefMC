import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';

export function deriveCpu(previous, current, logicalCpus) {
  const elapsed = (current.sampledAtMs - previous.sampledAtMs) / 1000;
  if (elapsed <= 0 || logicalCpus < 1) throw new Error('CPU samples require positive elapsed time and logical CPU count');
  const cpuCores = Math.max(0, (current.cpuSeconds - previous.cpuSeconds) / elapsed);
  return { cpuCores, cpuPercentOfMachine: cpuCores / logicalCpus * 100 };
}

function percentile(values, quantile) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const position = (sorted.length - 1) * quantile;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

export function summarize(samples, key) {
  const values = samples.map(sample => sample[key]).filter(value => Number.isFinite(value));
  const unavailableReasons = samples.filter(sample => sample[key] == null && sample[`${key}Unavailable`]).map(sample => sample[`${key}Unavailable`]);
  return {
    count: values.length,
    unavailable: samples.length - values.length,
    unavailableReasons,
    mean: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null,
    median: percentile(values, 0.5),
    p95: percentile(values, 0.95),
  };
}

export function samplesToCsv(samples) {
  const keys = [...new Set(samples.flatMap(sample => Object.keys(sample)))];
  const quote = value => {
    if (value == null) return '';
    const text = typeof value === 'object' ? JSON.stringify(value) : String(value);
    return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  return [keys.join(','), ...samples.map(sample => keys.map(key => quote(sample[key])).join(','))].join('\r\n') + '\r\n';
}

export function parseJstatSample(headerLine, sampleLine) {
  const headers = headerLine.trim().split(/\s+/);
  const values = sampleLine.trim().split(/\s+/).map(Number);
  if (headers.length !== values.length || values.some(value => !Number.isFinite(value))) return null;
  const fields = Object.fromEntries(headers.map((key, index) => [key, values[index]]));
  const heapColumns = ['S0U', 'S1U', 'EU', 'OU'].filter(key => Number.isFinite(fields[key]));
  const gcColumns = ['YGC', 'FGC', 'CGC'].filter(key => Number.isFinite(fields[key]));
  const gcTimeColumns = ['YGCT', 'FGCT', 'CGCT'].filter(key => Number.isFinite(fields[key]));
  return {
      // jstat -gc reports these utilization columns in KB.
      heapBytes: heapColumns.length ? heapColumns.reduce((sum, key) => sum + fields[key], 0) * 1024 : null,
    gcCount: gcColumns.length ? gcColumns.reduce((sum, key) => sum + fields[key], 0) : null,
    gcTimeSeconds: gcTimeColumns.length ? gcTimeColumns.reduce((sum, key) => sum + fields[key], 0) : null,
  };
}

export function parseJfrGcHeapSummaries(recording, startMs = -Infinity, endMs = Infinity) {
  const events = recording?.recording?.events;
  if (!Array.isArray(events)) return [];
  return events.flatMap(event => {
    if (event?.type !== 'jdk.GCHeapSummary') return [];
    const values = event.values;
    if (values?.when !== 'After GC') return [];
    const sampledAtMs = Date.parse(values.startTime);
    const heapUsedBytes = Number(values.heapUsed);
    const committedBytes = Number(values.heapSpace?.committedSize);
    if (!Number.isFinite(sampledAtMs) || sampledAtMs < startMs || sampledAtMs > endMs || !Number.isFinite(heapUsedBytes)) return [];
    return [{
      sampledAt: new Date(sampledAtMs).toISOString(),
      gcId: Number.isFinite(Number(values.gcId)) ? Number(values.gcId) : null,
      heapUsedBytes,
      committedBytes: Number.isFinite(committedBytes) ? committedBytes : null,
    }];
  });
}

export function parseMsptOutputLine(line) {
  const plainLine = line.replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, '');
  const messageStart = plainLine.lastIndexOf(']:');
  const message = messageStart >= 0 ? plainLine.slice(messageStart + 2) : plainLine;
  const tickMarker = message.indexOf('◴');
  const valuesText = tickMarker >= 0 ? message.slice(tickMarker + 1) : message;
  const values = [...valuesText.matchAll(/-?\d+(?:[.,]\d+)?/g)]
    .map(match => Number(match[0].replace(',', '.')));
  if (values.length < 9 || values.some(value => !Number.isFinite(value))) return null;
  return { mspt: values[0], msptMin: values[1], msptMax: values[2] };
}

export function startJstatSampler(javaExecutable, pid, intervalMs = 1000) {
  const jstat = join(dirname(javaExecutable), process.platform === 'win32' ? 'jstat.exe' : 'jstat');
  if (!existsSync(jstat)) return { child: null, samples: [], unavailableReason: 'jstat executable not found beside selected Java runtime' };
  const child = spawn(jstat, ['-gc', String(pid), String(Math.max(250, Math.min(10_000, intervalMs)))], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  const samples = [];
  let header;
  let stderr = '';
  child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk; });
  const lines = createInterface({ input: child.stdout });
  lines.on('line', line => {
    const columns = line.trim().split(/\s+/);
    if (!header && columns.includes('YGC') && columns.includes('OU')) { header = line; return; }
    if (!header) return;
    const parsed = parseJstatSample(header, line);
    if (parsed) samples.push({ sampledAtMs: Date.now(), ...parsed });
  });
  return {
    child, samples,
    get unavailableReason() { return samples.length ? null : (stderr.trim() || 'jstat returned no valid samples'); },
    async stop() {
      if (child.exitCode === null && child.signalCode === null) {
        await new Promise(resolve => {
          const timer = setTimeout(resolve, 3000);
          child.once('exit', () => { clearTimeout(timer); resolve(); });
          child.kill();
        });
      }
      lines.close();
      return { stderr };
    },
  };
}

export function startWindowsSampler(pids, intervalMs = 1000) {
  if (process.platform !== 'win32') throw new Error('Process sampler currently requires Windows');
  const validPids = [...new Set(pids.map(Number))];
  if (validPids.length === 0 || validPids.some(pid => !Number.isInteger(pid) || pid < 1)) throw new Error('Sampler requires valid process IDs');
  const idList = validPids.join(',');
  const script = `$ids=@(${idList})+@($PID); while ($true) { $now=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); $rows=@($ids | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue | ForEach-Object { [pscustomobject]@{ pid=$_.Id; cpuSeconds=$_.CPU; workingSetBytes=$_.WorkingSet64; privateBytes=$_.PrivateMemorySize64; sampledAtMs=$now } } }); [Console]::Out.WriteLine((ConvertTo-Json -Compress -InputObject @($rows))); Start-Sleep -Milliseconds ${Math.max(250, Math.min(10_000, intervalMs))} }`;
  const encoded = Buffer.from(script, 'utf16le').toString('base64');
  const child = spawn('powershell.exe', ['-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  const samples = [];
  let stderr = '';
  child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk; });
  const lines = createInterface({ input: child.stdout });
  lines.on('line', line => {
    try {
      const decoded = JSON.parse(line);
      for (const row of Array.isArray(decoded) ? decoded : [decoded]) {
        if (row?.pid) samples.push({ ...row, pid: Number(row.pid), cpuSeconds: Number(row.cpuSeconds), workingSetBytes: Number(row.workingSetBytes), privateBytes: Number(row.privateBytes), sampledAtMs: Number(row.sampledAtMs) });
      }
    } catch {}
  });
  return {
    child, samples,
    async stop() {
      if (child.exitCode === null && child.signalCode === null) {
        await new Promise(resolve => {
          const timer = setTimeout(resolve, 3000);
          child.once('exit', () => { clearTimeout(timer); resolve(); });
          child.kill();
        });
      }
      lines.close();
      return { stderr };
    },
  };
}
