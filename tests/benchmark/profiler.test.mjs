import test from 'node:test';
import assert from 'node:assert/strict';
import { jfrStartupArgument } from '../../scripts/benchmark/lib/profiler.mjs';

test('builds a startup JFR option that preserves Windows paths containing spaces', () => {
  const file = 'C:\\Test Server\\results\\run 1\\profile.jfr';
  assert.equal(
    jfrStartupArgument(file),
    `-XX:StartFlightRecording=name=BeefMCBenchmark,settings=profile,disk=true,dumponexit=true,filename=${file}`,
  );
});

test('rejects paths that would split the JFR option list', () => {
  assert.throws(() => jfrStartupArgument('C:\\Test Server\\results,old\\profile.jfr'), /comma/);
});
