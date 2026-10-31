# Local runtime benchmark

This harness compares a BeefMC release with its direct parent and, where available, Paper. It runs only on Windows and rejects non-loopback server targets. Server artifacts, instances, world snapshots, and raw results belong under the sibling Test Server directory, outside Git.

## Safety and setup

- Use only isolated local instances. Harness forces 127.0.0.1, offline mode, and a generated whitelist.
- Read the Minecraft EULA. The harness never creates or edits eula.txt; each instance must already have eula=true.
- The prepare.mjs command copies checksum-verified JARs and writes isolated server.properties and whitelist.json.
- bootstrap-world.mjs starts one accepted-EULA instance, saves a deterministic baseline world, then shuts it down. The runner restores that snapshot before every measured run.
- Do not use production worlds, credentials, plugins, or server addresses.

## Commands

    node scripts/benchmark/prepare.mjs <Test-Server-artifacts\source-config.json> <Test Server>
    node scripts/benchmark/bootstrap-world.mjs <Test-Server\config\benchmark-1.21.11.json> beefmc
    node scripts/benchmark/run.mjs <Test-Server\config\benchmark-1.21.11.json>

The prepared smoke configuration starts with one bot and a one-second sample. Run smoke checks first.

For iterative comparisons, use a short sequential profile: 25 bots, 60-second warm-up, 180-second sample, and 2 repetitions. Three variants take about 24 minutes of measurement time, plus startup and shutdown. Keep variants sequential while measuring CPU; parallel servers compete for the same CPU and can distort the comparison. The 64 GiB host has enough RAM for parallel smoke checks, but RAM capacity does not remove CPU contention.

The earlier 10-bot, 120-second warm-up, 480-second sample, 3-repetition profile took about 90 minutes across three variants and kept measured server CPU below 0.14 core. Use that extended profile only when a short result is inconclusive. Add a third repetition or longer sample when run-to-run variation is close to the difference being measured. Use fresh-world exploration only for changes involving chunk generation or memory growth.

To create a run config, set botCount, warmupSeconds, sampleSeconds, repetitions, and scenario in a local source config, then run `prepare.mjs` to refresh whitelists. Keep intensive performance profiling on 1.21.11; other supported versions get compilation and focused regression checks when patches are ported. Do not repeat the full bot profile across every version.

Use separate configurations for steady-world and exploration; reset snapshot before each run. Compare variants sequentially with identical JDK, JVM arguments, world snapshot, settings, bot count, and timing. Do not compare runs from different Minecraft versions as if they shared one performance baseline.

## Measurements and limits

- Windows Get-Process samples server, bot, and jstat process CPU time, working set, and private bytes every second.
- jstat -gc records Java heap use and GC counters when matching JDK tools permit attachment. When JFR is enabled, the runner also extracts timestamped `jdk.GCHeapSummary` after-GC snapshots from the recording. These snapshots are event-based and must not be treated as continuous heap measurements.
- TPS/MSPT remain unavailable unless a common measurement source is installed and captured for every variant. Missing metrics are empty with a reason, never zero.
- Each run writes run.json, samples.csv, process logs, and optional JFR files under Test Server/results/<version>/<run-id>/.
- The benchmark bot workload is synthetic. It does not establish plugin compatibility or represent every production workload.
- Review raw runs and variance before changing PERFORMANCE.md or selecting an optimization.
