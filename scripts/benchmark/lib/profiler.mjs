import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { parseJfrGcHeapSummaries } from './metrics.mjs';

export function jfrStartupArgument(filename) {
  if (typeof filename !== 'string' || filename.length === 0) throw new Error('JFR requires an output filename');
  if (/[\r\n,]/.test(filename)) throw new Error('JFR filename cannot contain a comma or newline');
  return `-XX:StartFlightRecording=name=BeefMCBenchmark,settings=profile,disk=true,dumponexit=true,filename=${filename}`;
}

export function readJfrGcHeapSummaries(javaExecutable, filename, startMs, endMs) {
  const jfr = join(dirname(javaExecutable), process.platform === 'win32' ? 'jfr.exe' : 'jfr');
  if (!existsSync(jfr)) return { samples: [], error: 'jfr executable not found beside selected Java runtime' };
  const result = spawnSync(jfr, ['print', '--json', '--events', 'jdk.GCHeapSummary', filename], {
    encoding: 'utf8',
    windowsHide: true,
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error) return { samples: [], error: result.error.message };
  if (result.status !== 0) return { samples: [], error: result.stderr.trim() || `jfr exited with code ${result.status}` };
  try {
    return { samples: parseJfrGcHeapSummaries(JSON.parse(result.stdout), startMs, endMs), error: null };
  } catch (error) {
    return { samples: [], error: `Unable to parse jfr output: ${error.message}` };
  }
}
