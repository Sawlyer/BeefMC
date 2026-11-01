# BeefMC Performance Record

This record summarizes measured results by release. Results apply only to the listed Minecraft version and workload. No result here establishes a general CPU or memory gain across servers.

## BeefMC v0.0.3

**Change:** modern waypoint updates now iterate live connection maps instead of allocating copied sets in `ServerWaypointManager.updatePlayer` and `updateWaypoint`. Applied to 1.21.11, 26.1.2, and 26.3. Minecraft 1.8.8 has no matching code path and is unchanged. No configuration, API, or packet format changed.

**Comparison with Paper:** BeefMC v0.0.3 versus Paper 1.21.11 build 132 (`5ffef465eeeb5f2a3c23a24419d97c51afd7dbb4923ff42df9a3f58bba1ccfba`). Both used 50 local Mineflayer bots, the same steady-world snapshot and seed `7402981`, `allow-flight=true`, Java 21.0.12.1, and `-Xms512M -Xmx4G`. Three sequential pairs ran in alternating order; each run used a 20-second warm-up and 60-second measurement. No plugins or proxy.

- **Validity:** all six measured runs completed with 50 bots, 57–59 server CPU samples, four MSPT samples, and graceful shutdown. A failed setup attempt before dependency installation was excluded.
- **Server CPU:** mean of per-run median usage was 0.506 cores for BeefMC and 0.569 for Paper (11.1% lower). All three paired readings were lower for BeefMC by 8.5–15.3%.
- **MSPT:** mean of per-run averages was 5.68 ms for BeefMC and 7.35 ms for Paper (22.8% lower). All three pairs were lower by 18.4–25.2%; only four MSPT samples were collected per run.
- **Process memory:** mean per-run median working set was 1.627 GiB for BeefMC and 1.595 GiB for Paper (+2.0%). Private bytes were 1.693 GiB and 1.657 GiB (+2.1%). No memory reduction was measured; pair-to-pair memory readings varied substantially.
- **Environment:** Windows 11, AMD Ryzen 9 9950X, 32 logical CPUs, 61.6 GiB RAM. JFR and valid heap/GC samples were unavailable.
- **Conclusion:** this synthetic 50-bot workload measured lower CPU and MSPT for BeefMC v0.0.3, with slightly higher process memory. Results cover Minecraft 1.21.11 only and do not establish a general gain or production behavior.
- **Raw runs:** `Test Server/benchmark-v0.0.3/paper-direct/results/1.21.11/`.

**Comparison with BeefMC v0.0.2:**

- **Workload:** 100 local Mineflayer bots moving in a steady world; 500 benchmark pigs; shared world snapshot and seed `7402981`; `allow-flight=true`; Java 21.0.12.1; `-Xms512M -Xmx4G`; 20-second warm-up, 60-second measurement, three sequential paired runs with order alternated; no plugins or proxy.
- **Validity:** all six runs completed, recorded 100 bot spawns, 58–59 server CPU intervals and 12 MSPT samples, had no server errors, and shut down cleanly. One initial baseline with `allow-flight=false` kicked a bot and was excluded; both variants used `true` for the final comparison.
- **Server CPU:** mean per-run median was 1.085 cores at baseline and 1.032 for the candidate (4.9% lower). Paired changes were +1.6%, −9.3%, and −6.0%; CPU result is mixed.
- **MSPT:** mean of per-run averages fell from 9.958 ms to 9.342 ms (6.2%). All three pairs improved by 6.1%, 5.5%, and 7.0%.
- **Process memory:** mean median working set changed from 2.239 GiB to 2.219 GiB (0.9% lower); private bytes changed from 2.301 GiB to 2.282 GiB (0.8% lower). One pair showed a roughly 16% increase, so these readings do not establish a stable memory or retained-heap reduction.
- **JFR:** not recorded for this final candidate.
- **Conclusion:** repeated MSPT reduction supports the change for this workload. CPU effect is modest and mixed; memory reduction is unproven. Plugin, proxy, and real-client compatibility were not retested.
- **Raw runs:** `Test Server/benchmark-v0.0.3/waypoint-release-qualification/results-both-iterators/1.21.11/`.

## BeefMC v0.0.2

**Change:** enable `performance.optimize-waypoint` by default in newly generated configurations on 1.21.11, 26.1.2, and 26.3. Existing explicit values remain unchanged. Minecraft 1.8.8 is unaffected.

**Measurement:** three paired 100-bot comparisons on 1.21.11, using the same v0.0.1 JAR with only the setting changed. This is a setting comparison, not a JAR-to-JAR comparison and not a direct Paper comparison.

- **Server CPU:** mean per-run median changed from 1.001 cores off to 0.807 on (19.4% lower); all paired runs decreased by 14.4%, 34.1%, and 2.7%.
- **MSPT:** mean changed from 13.19 ms to 8.20 ms (37.8% lower); all paired runs decreased by 32.0%, 46.3%, and 34.2%.
- **Process memory:** mean working set rose from 4.027 GiB to 4.067 GiB (1.0%); private bytes were effectively unchanged at 4.748 and 4.747 GiB. No RAM reduction was measured.
- **Compatibility check:** a two-client protocol test observed matching waypoint tracking and update packets with the setting on and off, and zero waypoint packets with the vanilla locator bar disabled. GUI rendering and plugin compatibility were not tested.
- **Raw runs:** `Test Server/benchmark-v0.0.2/waypoint-100/results/1.21.11/`.

## BeefMC v0.0.1

The release included optional HAProxy PROXY protocol support on Minecraft 1.8.8. Release validation also covered modern hopper transfer behavior. Neither change has a measured CPU or RAM gain in this record.

### Earlier Paper comparison

This historical comparison measured BeefMC v0.0.1 against Paper 1.21.11 build 132.

- **Workload:** 50 local Mineflayer bots; same world snapshot, Java 21.0.12.1 and `-Xms1G -Xmx4G`; steady-world movement; three sequential pairs with order alternated; 20-second warm-up and 60-second measurement; no plugins.
- **Server CPU:** mean run average was 0.523 cores for BeefMC and 0.554 for Paper (5.6% lower for BeefMC). Paired changes were −15.6%, −8.8%, and +8.9%; CPU result is inconclusive.
- **Working set:** 1.523 GiB BeefMC versus 1.512 GiB Paper (+11.3 MiB, +0.7%).
- **Private bytes:** 1.588 GiB BeefMC versus 1.575 GiB Paper (+13.3 MiB, +0.8%). `jstat` provided no valid heap/GC samples. No memory reduction was measured.
- **Conclusion:** these runs establish neither a reliable CPU advantage nor a RAM saving over Paper. Comparison covers 1.21.11 only.
- **Raw runs:** `Test Server/release-v0.0.1/results/1.21.11/`.

## BeefMC v0.0.0

Initial release for the four supported versions. No BeefMC optimization gain was established.

### Earlier low-load reference

BeefMC v0.0.0, Leaf 1.21.11 build 179, and Paper 1.21.11 build 132 were compared with 10 bots and a fixed 4 GiB heap. BeefMC and Leaf both used about 0.137 CPU cores; Paper used 0.122. Median working set was 3.641 GiB for BeefMC and 3.584 GiB for Paper; private bytes were 4.621 and 4.609 GiB. Load was too light to identify a meaningful bottleneck; these small differences do not show a BeefMC performance or memory benefit.

## Other measured candidates

### `optimize-waypoint` — 50 bots

On the same BeefMC JAR, three setting-off/on pairs produced 17.8% lower mean MSPT and an estimated 43.1% lower server-thread allocation traffic with the setting on. CPU changed inconsistently; working set and private bytes showed no meaningful change. This preliminary result is superseded by the 100-bot comparison above. Allocation weights are sampled JFR estimates, not retained heap. Raw data: `Test Server/benchmark-50-20261030/results/1.21.11/`.

### Light-buffer reference cleanup — rejected

Three source-matched pairs showed no repeatable benefit. Mean MSPT changed by −0.2%; working set rose 3.7%; private bytes changed by −0.3%; sparse after-GC heap snapshots were 5.0% higher. Candidate was excluded from v0.0.2. Raw data: `Test Server/benchmark-v0.0.2/results-source-matched/1.21.11/`.

## Limits

All comparisons above use synthetic local bot workloads without plugins or a proxy. Results do not establish performance for real player activity, production networks, Minecraft versions other than 1.21.11, or other JVM settings. BeefMC v0.0.2 has no separate direct Paper comparison. Measure the exact version, configuration, and workload before deployment decisions.
