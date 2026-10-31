import test from 'node:test';
import assert from 'node:assert/strict';
import { deriveCpu, summarize, samplesToCsv, parseJstatSample, parseJfrGcHeapSummaries, parseMsptOutputLine } from '../../scripts/benchmark/lib/metrics.mjs';

test('derives process CPU from cumulative CPU seconds and elapsed wall time', () => {
  assert.deepEqual(deriveCpu(
    { sampledAtMs: 1000, cpuSeconds: 2 },
    { sampledAtMs: 3000, cpuSeconds: 4 },
    16,
  ), { cpuCores: 1, cpuPercentOfMachine: 6.25 });
});

test('summary skips unavailable values and preserves missing reason', () => {
  const result = summarize([{ mspt: 30 }, { mspt: null, msptUnavailable: 'Spark absent' }, { mspt: 50 }], 'mspt');
  assert.equal(result.count, 2);
  assert.equal(result.mean, 40);
  assert.equal(result.median, 40);
  assert.equal(result.unavailable, 1);
  assert.equal(result.unavailableReasons[0], 'Spark absent');
});

test('CSV represents unavailable metrics as empty fields, not zero', () => {
  assert.match(samplesToCsv([{ time: 't', mspt: null, msptUnavailable: 'not collected' }]), /t,,not collected/);
});

test('parses Java heap and GC counters without converting absent data to zero', () => {
  const sample = parseJstatSample('S0U S1U EU OU YGC YGCT FGC FGCT GCT', '0 2 10 20 3 0.4 1 0.5 0.9');
  assert.equal(sample.heapBytes, 32 * 1024);
  assert.equal(sample.gcCount, 4);
  assert.equal(sample.gcTimeSeconds, 0.9);
  assert.equal(parseJstatSample('S0U EU OU', '0 1 2').gcCount, null);
});

test('converts jstat heap values from kilobytes to bytes', () => {
  const sample = parseJstatSample('S0U S1U EU OU YGC', '0 0 1024 2048 1');
  assert.equal(sample.heapBytes, 3 * 1024 * 1024);
});

test('parses only after-GC JFR heap snapshots inside the measured window', () => {
  const recording = { recording: { events: [
    { type: 'jdk.GCHeapSummary', values: { startTime: '2026-10-31T12:00:00Z', gcId: 1, when: 'Before GC', heapUsed: 900, heapSpace: { committedSize: 4096 } } },
    { type: 'jdk.GCHeapSummary', values: { startTime: '2026-10-31T12:00:01Z', gcId: 1, when: 'After GC', heapUsed: 300, heapSpace: { committedSize: 4096 } } },
    { type: 'jdk.GCHeapSummary', values: { startTime: '2026-10-31T12:00:02Z', gcId: 2, when: 'After GC', heapUsed: 250, heapSpace: { committedSize: 4096 } } },
  ] } };
  const samples = parseJfrGcHeapSummaries(recording, Date.parse('2026-10-31T12:00:00Z'), Date.parse('2026-10-31T12:00:01Z'));
  assert.deepEqual(samples, [{ sampledAt: '2026-10-31T12:00:01.000Z', gcId: 1, heapUsedBytes: 300, committedBytes: 4096 }]);
});

test('parses Paper MSPT console output with dot or comma decimal separators', () => {
  assert.equal(parseMsptOutputLine('[20:00:00 INFO]: ◴ 5.1/1.2/8.9, 4.2/1.0/9.5, 3.8/1.1/12.0').mspt, 5.1);
  assert.equal(parseMsptOutputLine('[20:00:00 INFO]: ◴ 5,1/1,2/8,9, 4,2/1,0/9,5, 3,8/1,1/12,0').mspt, 5.1);
  assert.equal(parseMsptOutputLine('[20:00:00 INFO]: \u001b[33m◴ \u001b[92m5.1\u001b[37m/\u001b[92m1.2\u001b[37m/8.9\u001b[0m, 4.2/1.0/9.5, 3.8/1.1/12.0').mspt, 5.1);
  assert.equal(parseMsptOutputLine('[20:00:00 INFO]: Server tick times from last 5s, 10s, 1m:'), null);
});

test('parses Paper MSPT values when Windows console replaces the marker glyph', () => {
  const line = '[21:54:34 INFO]: \u001b[38;2;255;170;0m? \u001b[38;2;170;170;170m\u001b[38;2;85;255;85m8,1\u001b[38;2;170;170;170m/\u001b[38;2;85;255;85m5,5\u001b[38;2;170;170;170m/\u001b[38;2;85;255;85m24,3\u001b[38;2;255;255;85m, \u001b[38;2;85;255;85m8,8\u001b[38;2;170;170;170m/\u001b[38;2;85;255;85m5,5\u001b[38;2;170;170;170m/\u001b[38;2;85;255;85m24,3\u001b[38;2;255;255;85m, \u001b[38;2;85;255;85m20,3\u001b[38;2;170;170;170m/\u001b[38;2;85;255;85m0,2\u001b[38;2;255;85;85m1605,0\u001b[0m';
  assert.deepEqual(parseMsptOutputLine(line), { mspt: 8.1, msptMin: 5.5, msptMax: 24.3 });
});
