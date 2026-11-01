# BeefMC Performance and Memory Measurements

This file records reproducible BeefMC-specific memory and performance comparisons. It is not a general development history.

No general BeefMC CPU or memory gain has been established. Repeated `optimize-waypoint` comparisons show lower CPU and MSPT under synthetic movement loads, but no process-memory reduction or release-wide benefit. Results inherited from PandaSpigot, Leaf, Paper, or other upstream projects are not BeefMC measurements.

## Runtime qualification for v0.0.1

- **Status:** Targeted CI runtime checks passed for all four catalog versions. These checks establish only the listed behaviors; they do not establish server-wide performance gains or general plugin compatibility.
- **1.8.8:** [runtime workflow #41197321808](https://github.com/Sawlyer/BeefMC/actions/runs/41197321808) built the legacy jar with JDK 17, launched it with Java 8, observed startup readiness, and shut it down cleanly. Downloaded JAR SHA-256 matched its sidecar: `e5515f89f11c6a21bb33af32826142c2e507a460ba497d87ef6a43666593d8c1`.
- **1.21.11:** [runtime workflow #41149392437](https://github.com/Sawlyer/BeefMC/actions/runs/41149392437) built and packaged the jar; hopper integration checks passed with the sleeping optimization off and on. Downloaded JAR SHA-256 verified: `21126391863d94e5aa8aab5eeda5edf36e6fff5df2c7c784d126ea0e739e8684`.
- **26.1.2:** [runtime workflow #41192097663](https://github.com/Sawlyer/BeefMC/actions/runs/41192097663) built and packaged the jar; both hopper integration modes passed. Downloaded JAR SHA-256 verified: `7bfcb9d326e5940516a01af06d8519949c9377fcdc7c746723ab59532baa99ea`.
- **26.3:** [runtime workflow #41192872053](https://github.com/Sawlyer/BeefMC/actions/runs/41192872053) built and packaged the jar; both hopper integration modes passed. Downloaded JAR SHA-256 verified: `4c128e9ba7ebb91f308bc540e9e1f801e68a5d8e569390dcfdde0c3306c5c127`.
- **Limits:** GitHub-hosted CI, no plugins or player workload. No CPU, RAM, MSPT, TPS, proxy-routing, or broad gameplay measurements. These checks do not justify a performance claim.

## 1.21.11 steady-world baseline — 2026-10-30

- **Status:** reference baseline only; no gain demonstrated.
- **Artifacts:** BeefMC v0.0.0 (`2df769b87dfa2710869e5cf79bfb3d8249a8aac4973763b45c03d94316800886`); Leaf 1.21.11 build 179, commit `12f438e06b8a35d6584687565ec5eeacb373972c`; Paper 1.21.11 build 132 (`5ffef465eeeb5f2a3c23a24419d97c51afd7dbb4923ff42df9a3f58bba1ccfba`).
- **Environment:** AMD Ryzen 9 9950X, 32 logical CPUs, 61.6 GiB RAM, Windows 11 build 26300, Temurin Java 21.0.12.1, `-Xms4G -Xmx4G`.
- **Method:** 10 offline Mineflayer bots, steady-world, shared generated snapshot, 120-second warm-up, 480-second measurement, 3 sequential repetitions per variant with rotated order. Each run completed and shut down cleanly. Raw JSON/CSV remain under `Test Server/results/1.21.11/`.
- **Server CPU:** median of the three per-run median readings, normalized to all 32 logical CPUs: BeefMC 0.427% (0.137 core); Leaf 0.429% (0.137 core); Paper 0.382% (0.122 core). Repetition ranges were 0.335–0.430%, 0.333–0.472%, and 0.380–0.428%, respectively.
- **Working set:** median of per-run medians: BeefMC 3.641 GiB; Leaf 3.612 GiB; Paper 3.584 GiB. These small differences do not establish a memory reduction.
- **Private bytes:** BeefMC 4.621 GiB; Leaf 4.619 GiB; Paper 4.609 GiB. Fixed 4 GiB minimum heap limits interpretation of private-memory differences.
- **Limits:** 465–468 of 480 expected process samples per run. `jstat` returned no valid heap/GC samples; TPS/MSPT were not captured. Workload used no plugins and kept server CPU below 0.14 core, too light to identify a useful CPU bottleneck. Plugin compatibility was not tested.
- **Conclusion:** this records a 1.21.11 reference point only. CPU readings are close at low load; BeefMC shows no measured memory saving over Leaf or Paper. No optimization claim follows from this run.

## 5-second TPS lagging check — merged, runtime gain not measured

- **Status:** Implemented and merged on all three modern targets; GitHub CI build and test jobs passed. No server-wide CPU, memory, or MSPT gain measured.
- **References:** [1.21.11 PR #4](https://github.com/Sawlyer/BeefMC/pull/4), [26.1.2 PR #5](https://github.com/Sawlyer/BeefMC/pull/5), [26.3 PR #6](https://github.com/Sawlyer/BeefMC/pull/6).
- **Affected versions:** 1.21.11, 26.1.2, and 26.3. Version 1.8.8 has no matching 5-second TPS API path.
- **Implementation:** lag checks calculate only 5-second TPS instead of calculating all four TPS windows and allocating a four-value result array. Work reduction applies to this check path only; no whole-server percentage is inferred.
- **Compatibility:** formula, tick interval, threshold, and lock remain unchanged. No plugin API change. CI validated patch application, compilation, and available tests; runtime threshold behavior remains unverified.
- **Measurement method:** planned repeated baseline/candidate profile on 1.21.11 using identical JAR, JVM, world snapshot, and focused workload. Capture process CPU, MSPT, heap/GC, and JFR when available.
- **Environment and workload:** intended host is Windows 11, Ryzen 9 9950X, 61.6 GiB RAM, Java 21.0.12.1, 4 GiB fixed heap, no plugins, pre-generated world.
- **Results:** Not measured. The local Test Server now starts from the benchmark harness, but completed profiles did not isolate the lag-check path or compare pre-change and post-change builds.
- **Remaining checks:** run a focused lagging-workload comparison and verify threshold behavior. Plugin and proxy checks are outside owner-approved scope.

## Compatibility fixes

### Sleeping hopper transfer amount

- **Status:** Implemented; performance not measured.
- **Date and reference:** 2026-10-30; BeefMC issue #11.
- **Minecraft versions:** 1.21.11, 26.1.2, and 26.3.
- **Changed area:** Lithium cached hopper extraction used by sleeping block entities.
- **Hypothesis:** Restore `spigot.yml` `hopper-amount` behavior when the optional sleeping block entity path is enabled. This fixes configuration compatibility; no CPU or memory gain is expected from this correction itself.
- **Compatibility:** Default remains disabled. Sleeping mode with `hopper-amount: 1` retains one-item extraction. Larger values restore configured transfer count; partial destination capacity must restore uninserted items.
- **Method:** Isolated RCON integration test with `hopper-amount: 5` and `hopper-transfer: 8`; check empty and nearly full destination hoppers with sleeping mode both disabled and enabled.
- **Environment:** Linux GitHub Actions; Java 21 for 1.21.11, Java 25 for 26.1.2 and 26.3. Local Windows benchmark startup now works; hopper compatibility evidence remains from CI integration runs.
- **Workload:** Synthetic hopper transfer, no players or plugins.
- **Results:** Functional checks passed on all three versions, with sleeping mode both disabled and enabled. Empty destination: source 63 to 58, destination 0 to 5. Nearly full destination: source 63 to 59, destination 316 to 320; item count conserved. CPU and memory not measured.
- **Conclusion:** Correctness fix only. No optimization claim.
- **Remaining checks:** Other container edge cases remain untested. Plugin checks are outside owner-approved scope; no general plugin compatibility claim follows.

## Entry template

### [ID] Optimization name

- **Status:** proposed / implemented, not measured / measured / abandoned.
- **Date and reference:** commit, pull request, or version tag.
- **Minecraft versions:** versions affected and tested.
- **Changed area:** modules, classes, patches, or settings.
- **Hypothesis:** behavior targeted and expected effect.
- **Compatibility:** plugin, API, configuration, world, or gameplay risks.
- **Method:** commands, duration, repetitions, and collection method.
- **Environment:** CPU, memory, operating system, Java version, and JVM options.
- **Workload:** player count, plugins, world, scenario, and duration.
- **Results:** comparable baseline and BeefMC values, with units and variation.
- **Conclusion:** measured gain, no change, or regression under listed conditions.
- **Remaining checks:** versions and scenarios not covered.

Mark missing measurements `Not measured`. Compare baseline and BeefMC on the same machine, workload, and configuration. Do not generalize results beyond the conditions recorded.

## 1.21.11 50-bot diagnostic profiles — 2026-10-30

- **Status:** exploratory baseline; no before/after comparison and no gain established.
- **Artifact:** BeefMC baseline JAR, SHA-256 `2df769b87dfa2710869e5cf79bfb3d8249a8aac4973763b45c03d94316800886`.
- **Environment:** AMD Ryzen 9 9950X, 32 logical CPUs, 61.6 GiB RAM, Windows 11 build 26300, Temurin Java 21.0.12.1, `-Xms4G -Xmx4G`.
- **Method:** 50 local Mineflayer bots, no plugins, same generated world snapshot, 20-second warm-up, 60-second measurement, one run per scenario. JFR recorded from JVM startup and filtered to the measured window. `/mspt` sampled every five seconds. Process CPU, working set, and private bytes sampled once per second.
- **Steady-world:** 58 server samples; 57 CPU intervals; median CPU 0.528 core, p95 0.884 core; median working set 3.81 GiB and private bytes 4.70 GiB. Twelve 5-second MSPT averages had mean 6.87 ms, range 6.4–8.1 ms; highest reported 5-second-window maximum was 46 ms.
- **Exploration:** 58 server samples; 57 CPU intervals; median CPU 0.542 core, p95 0.758 core; median working set 3.80 GiB and private bytes 4.69 GiB. Twelve 5-second MSPT averages had mean 6.46 ms, range 6.0–7.4 ms; highest reported 5-second-window maximum was 17.7 ms.
- **JFR heap snapshots:** steady-world had two collections, with heap usage 2.69/2.86 GiB before and 0.53/0.51 GiB after GC; exploration had one collection, 2.87 GiB before and 0.50 GiB after GC. Pauses were about 7.3/7.2 ms and 5.7 ms. These are GC-time snapshots, not continuous heap measurements.
- **JFR observations:** repeated server-thread work in `ChunkMap$TrackedEntity.updatePlayerMulti` and `ChunkEntitySlices`; allocation samples repeatedly pointed to `ServerWaypointManager.updatePlayer` / `updateWaypoint`, Guava `StandardTable` / `ImmutableSet`, and entity collision (`AABB.inflate`). JFR allocation weights estimate allocation traffic; they do not measure retained heap or exact allocation totals.
- **Limits:** one run per scenario; no plugins; `jstat -gc` returned no valid samples. Working set/private bytes are process memory, not used Java heap. Results identify candidates only and do not establish comparative gains.

## `optimize-waypoint` A/B — 1.21.11, 50 bots — 2026-10-30

- **Status:** repeated workload-specific result; three runs per setting; no default change and no production-wide claim.
- **Artifact:** same BeefMC JAR SHA-256 `2df769b87dfa2710869e5cf79bfb3d8249a8aac4973763b45c03d94316800886`, world snapshot, seed, Java 21.0.12.1, and `-Xms4G -Xmx4G`; only `optimize-waypoint` differed (`false` versus `true`).
- **Method:** 50-bot movement workload, 20-second warm-up, 60-second measured window, 12 `/mspt` samples per run, JFR from JVM startup filtered to the measured window. Runs rotated order across three pairs. No plugins.
- **Run validity:** all six runs completed and shut down gracefully, recorded 50 spawns, 59 server samples, 12 MSPT samples, complete JFR, and no server `[ERROR]` entries. `jstat` heap/GC remained unavailable.
- **Server CPU:** mean of run medians was 0.575 core with the option off versus 0.563 core with it on (2.1% lower). Paired changes were +2.2%, −13.2%, and +6.0%; CPU effect is inconclusive.
- **MSPT:** mean of per-run 5-second averages was 6.809 ms off versus 5.597 ms on (17.8% lower). All paired runs moved down: 18.3%, 22.2%, and 12.7%. Mean p95 was 7.667 versus 6.300 ms (17.8% lower). This is a short synthetic workload result.
- **Process memory:** mean run-median working set was 3.849 versus 3.834 GiB; private bytes were 4.715 GiB for both. No memory reduction established.
- **JFR allocation samples:** server-thread allocation weights averaged 2,585 MiB off versus 1,470 MiB on (estimated 43.1% lower allocation traffic). Samples with `ServerWaypointManager` stacks averaged 1,412 versus 281 MiB (estimated 80.1% lower for those stacks). These are sampled estimates, not exact totals or retained heap.
- **Compatibility:** no plugins or real client were used; locator-bar rendering was not asserted. Setting remains experimental and defaults to `false`.
- **Conclusion:** consistent sampled tick-time and waypoint-allocation reduction for this workload; CPU inconclusive; process memory unchanged. Keep default `false`; no general performance claim.
- **Raw runs:** `Test Server/benchmark-50-20261030/results/1.21.11/`.

## `optimize-waypoint` A/B — 1.21.11, 100 bots — 2026-10-31

- **Status:** three paired runs completed against BeefMC v0.0.1; CPU and MSPT were lower in every pair. Process memory did not improve. This is a workload-specific result, not a release-wide claim.
- **Artifact and configuration:** same v0.0.1 JAR in both variants, SHA-256 `c98f8031826246e15f4a2e386314b14458336491d907787eaadafef8b09e8392`; only `beefmc-global.yml` `optimize-waypoint` differed (`false` versus `true`).
- **Environment and method:** Ryzen 9 9950X, 32 logical CPUs, 61.6 GiB RAM, Windows 11 build 26300, Temurin Java 21.0.12.1, `-Xms4G -Xmx4G`; 100 local Mineflayer bots on the same world snapshot, steady-world movement, 20-second warm-up and 60-second measurement, three pairs with order alternated. No plugins.
- **Run validity:** all six measured runs recorded 100 bot spawns, 57–59 server CPU intervals, 12 MSPT samples, complete JFR, no server errors, and graceful shutdown. Rejected path/hash/whitelist attempts, an incomplete baseline run, and a complete but unpaired waypoint-on run were excluded.
- **Server CPU:** mean of per-run median CPU was 1.001 core with the setting off versus 0.807 core with it on (−19.4%). Paired changes were −14.4%, −34.1%, and −2.7%.
- **MSPT:** mean of 12 five-second readings per run was 13.19 ms off versus 8.20 ms on (−37.8%). Paired changes were −32.0%, −46.3%, and −34.2%.
- **Process memory:** mean run-median working set was 4.027 GiB off versus 4.067 GiB on (+1.0%). Private bytes were 4.748 versus 4.747 GiB (−0.01%). No process-memory reduction established. JFR after-GC snapshots were sparse and uneven, so they do not support a retained-heap conclusion.
- **JFR allocation samples:** estimated server-thread allocation traffic averaged 7,510 MiB off versus 3,264 MiB on (−56.5%). Estimated `ServerWaypointManager.update*` traffic averaged 1,978 versus 509 MiB (−74.3%). JFR weights are sampled estimates, not exact allocation totals or retained heap.
- **Conclusion:** measured CPU and tick-time benefit under this 100-moving-bot workload; no RAM benefit. A separate protocol check below found matching vanilla waypoint packets with the setting on and off. The setting is enabled by default for newly generated modern configs; existing explicit config values remain unchanged. This remains a synthetic workload result, not a release-wide gain. Plugin and proxy checks remain outside owner-approved scope.
- **Raw runs:** `Test Server/benchmark-v0.0.2/waypoint-100/results/1.21.11/`. The initial whitelist-limited run and incomplete run are retained but excluded from results.

## `optimize-waypoint` vanilla protocol check — 1.21.11 — 2026-10-31

- **Method:** started the same v0.0.1 JAR four times with two local Mineflayer clients, toggling `optimize-waypoint` and the vanilla `locator_bar` gamerule. Moved one client through three positions while recording clientbound `tracked_waypoint` packets on both clients. No plugins.
- **Locator bar enabled:** baseline and optimized variants emitted matching packet sequences: observer saw 10 packets and moving player saw 2. Both included waypoint tracking and movement updates.
- **Locator bar disabled:** both variants emitted zero `tracked_waypoint` packets.
- **Validity:** both clients spawned in every run; all four runs shut down cleanly; no server errors. This confirms protocol-level waypoint behavior for this 1.21.11 scenario. It does not verify vanilla GUI rendering or plugin compatibility.
- **Config behavior:** new modern configs default `performance.optimize-waypoint` to `true` for 1.21.11, 26.1.2, and 26.3. Existing configs with an explicit value keep that value; set it to `true` manually to opt an existing server in.

## BeefMC v0.0.1 vs Paper 1.21.11 build 132 — 2026-10-31

- **Status:** release JAR smoke and three paired 50-bot runs completed. CPU direction was inconsistent; no CPU or RAM gain established.
- **Artifacts:** BeefMC v0.0.1 SHA-256 `c98f8031826246e15f4a2e386314b14458336491d907787eaadafef8b09e8392`; Paper build 132 SHA-256 `5ffef465eeeb5f2a3c23a24419d97c51afd7dbb4923ff42df9a3f58bba1ccfba`.
- **Environment:** AMD Ryzen 9 9950X, 32 logical CPUs, 61.6 GiB RAM, Windows 11 build 26300, Temurin Java 21.0.12.1, `-Xms1G -Xmx4G`.
- **Method:** 50 offline Mineflayer bots, steady-world, same snapshot, Java/JVM arguments and server properties except non-functional MOTD and generated management secret. `allow-flight=true` for synthetic movement. 20-second warm-up, 60-second measured window, three sequential repetitions per server with alternating order. One-bot smoke checks started, accepted a bot, and shut down cleanly on both JARs.
- **Validity:** all six measured runs completed with 50 spawns, 59 server samples, 58 CPU intervals, no bot failures, no server `[ERROR]`, and graceful shutdown. An initial run with `allow-flight=false` was excluded after the synthetic bot was kicked for floating.
- **Server CPU:** mean run average was 0.523 core BeefMC versus 0.554 core Paper (observed 5.6% lower); paired changes were −15.6%, −8.8%, and +8.9%. CPU result is inconclusive.
- **Process RAM:** mean working set was 1.523 GiB BeefMC versus 1.512 GiB Paper (+11.3 MiB, +0.7%). Private bytes were 1.588 versus 1.575 GiB (+13.3 MiB, +0.8%). No RAM reduction measured.
- **Limits:** `jstat` returned no valid heap/GC samples; TPS was not collected. No external plugins, Velocity routing, or production player workload tested. Comparison covers 1.21.11 only.
- **Raw runs:** `Test Server/release-v0.0.1/results/1.21.11/`.

## Temporary light-buffer reference cleanup A/B — 1.21.11 — 2026-10-31

- **Status:** measured in three paired runs; no repeatable memory or performance benefit; excluded from v0.0.2 scope.
- **Compared artifacts:** BeefMC v0.0.0 baseline SHA-256 `2df769b87dfa2710869e5cf79bfb3d8249a8aac4973763b45c03d94316800886`; PR #8 candidate SHA-256 `0518f8ffc8d4b632b5ca76f07ffd54b877d3c73d37e50e2d6f42f036ac3e5dc6`. Candidate PR changes only the 1.21.11 light-update patch and its performance record, on parent `d254aa0f9e`.
- **Source matching:** an earlier exploratory run compared the PR candidate to v0.0.1, whose source included additional changes absent from the candidate. That comparison is excluded. The recorded comparison below uses the v0.0.0 artifact from the PR's base period and same source branch parent.
- **Environment and workload:** Ryzen 9 9950X, Windows 11, Temurin Java 21.0.12.1, `-Xms4G -Xmx4G`, 50 Mineflayer bots, exploration scenario, shared snapshot, 20-second warm-up and 60-second measurement. Three sequential pairs with rotated order; no plugins.
- **Run validity:** all six runs completed, shut down gracefully, recorded 50 spawns, 59 server samples and 12 MSPT samples, and had no server `[ERROR]` entries. JFR provided six after-GC snapshots per variant. `jstat` did not provide usable heap samples.
- **Server CPU:** mean per-run median was 0.498 core baseline versus 0.440 core candidate (−11.8%). Paired changes were −18.0%, +9.4%, and −25.0%; CPU effect is inconclusive.
- **MSPT:** mean of 12 five-second readings per run was 6.094 ms baseline versus 6.081 ms candidate (−0.2%). Paired changes were +2.5%, +4.4%, and −7.4%; no consistent change.
- **Memory:** mean working-set median was 4,062 MiB baseline versus 4,212 MiB candidate (+150 MiB, +3.7%). Private bytes were 4,836 versus 4,822 MiB (−14 MiB, −0.3%). Mean JFR post-GC heap was 0.531 versus 0.558 GiB (+5.0%); each run contributed two snapshots. Variability and snapshot count do not establish a retained-heap regression or benefit.
- **Conclusion:** no measurable memory reduction; CPU and MSPT effects vary by pair. Do not merge or claim benefit from this candidate. PR #8 is not part of the next release; PRs #9 and #10 remain unmeasured on their versions.
- **Raw runs:** `Test Server/benchmark-v0.0.2/results-source-matched/1.21.11/`. The initial unmatched comparison remains under `Test Server/benchmark-v0.0.2/results/1.21.11/` and is not used for conclusions.

## Waypoint connection iteration — 1.21.11 — 2026-11-01

- **Status:** three paired runs completed against the exact BeefMC v0.0.2 1.21.11 release JAR. CPU median and MSPT favored the candidate overall; process memory did not show a stable reduction. Workload-specific only.
- **Artifacts:** baseline BeefMC v0.0.2 SHA-256 `914684fdfe05fc17c80cc43681f378045df9936c7d0e79d838ef5a381910c940`; candidate with iterator removal in both waypoint update paths SHA-256 `bfb8550363d789acdc47562c5a4598c5094cc29c229574650a72f7050784e47a`.
- **Environment:** AMD Ryzen 9 9950X, 32 logical CPUs, 61.6 GiB RAM, Windows 11 build 26300, Temurin Java 21.0.12.1, `-Xms512M -Xmx4G`.
- **Method:** 100 local Mineflayer bots, steady-world workload, same pre-generated world snapshot and seed `7402981`, 500 benchmark pigs, `allow-flight=true` on both instances, 20-second warm-up and 60-second measurement. Three sequential pairs with order alternated. No plugins or proxy.
- **Validity:** all six measured runs completed with graceful shutdown, 100 bot spawns, 58–59 server CPU intervals, 12 MSPT samples and no server `[ERROR]` entries. The initial baseline run that kicked a bot for floating while `allow-flight=false` was excluded; corrected configuration matched across both variants. No JFR was recorded for this final candidate.
- **Server CPU:** mean of per-run median CPU was 1.085 cores baseline versus 1.032 candidate (−4.9%). Pair changes were +1.6%, −9.3% and −6.0%; one pair moved slightly upward, so treat CPU effect as modest and workload-specific.
- **MSPT:** mean of per-run 12-sample MSPT averages was 9.958 ms baseline versus 9.342 ms candidate (−6.2%). All three pairs improved: −6.1%, −5.5% and −7.0%.
- **Process memory:** mean run-median working set was 2.239 GiB baseline versus 2.219 GiB candidate (−0.9%); private bytes were 2.301 versus 2.282 GiB (−0.8%). One pair was about 16% higher on the candidate and the other two lower. These readings do not establish a RAM reduction or retained-heap change.
- **Implementation:** replace per-update `ImmutableSet.copyOf` snapshots with direct map iteration and iterator removal in `ServerWaypointManager.updatePlayer` and `updateWaypoint`. No config, API, or packet change.
- **Conclusion:** retain as a release candidate for the measured tick-time improvement. Do not claim lower RAM or a general CPU gain. Plugin compatibility and real-client behavior were not retested for this source change.
- **Raw runs:** `Test Server/benchmark-v0.0.3/waypoint-release-qualification/results-both-iterators/1.21.11/`.
