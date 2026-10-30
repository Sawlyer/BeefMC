# BeefMC Performance and Memory Measurements

This file records reproducible BeefMC-specific memory and performance comparisons. It is not a general development history.

No BeefMC-specific memory or performance gain is documented yet. Results inherited from PandaSpigot, Leaf, Paper, or other upstream projects are not BeefMC measurements.

## Compatibility fixes

### Sleeping hopper transfer amount

- **Status:** Implemented; performance not measured.
- **Date and reference:** 2026-10-30; BeefMC issue #11.
- **Minecraft versions:** 1.21.11, 26.1.2, and 26.3.
- **Changed area:** Lithium cached hopper extraction used by sleeping block entities.
- **Hypothesis:** Restore `spigot.yml` `hopper-amount` behavior when the optional sleeping block entity path is enabled. This fixes configuration compatibility; no CPU or memory gain is expected from this correction itself.
- **Compatibility:** Default remains disabled. Sleeping mode with `hopper-amount: 1` retains one-item extraction. Larger values restore configured transfer count; partial destination capacity must restore uninserted items.
- **Method:** Isolated RCON integration test with a source hopper, destination hopper, `hopper-amount: 5`, and `hopper-transfer: 8`; check full and partially occupied destinations with sleeping mode both disabled and enabled.
- **Environment:** Local Windows runtime unavailable because Java fails to create the loopback connection; Linux GitHub Actions provides integration verification. Exact JDK versions recorded by the CI matrix.
- **Workload:** Synthetic hopper transfer, no players or plugins.
- **Results:** Not measured for CPU or memory. Functional results pending successful branch CI.
- **Conclusion:** Correctness fix only. No optimization claim.
- **Remaining checks:** All modern branch patch/build/integration jobs; production plugin and real-world hopper scenarios.

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
## 1.21.11 — 5-second TPS lag check (implemented, not measured)

- **Status:** Implemented in patch source; patch application and build pending.
- **Date and reference:** 2026-10-30; BeefMC issue #1.
- **Minecraft versions:** 1.21.11.
- **Changed area:** `leaf-server/minecraft-patches/features/0337-BeefMC-Optimize-5-second-TPS-lag-check.patch`.
- **Hypothesis:** The lagging check needs only the 5-second TPS window. Reading it directly avoids calculating the 1-minute, 5-minute, and 15-minute windows on each check.
- **Compatibility:** No plugin API or configuration changes. Existing lock and TPS calculation are reused. Runtime and plugin behavior checks remain pending.
- **Method:** Compare identical BeefMC baseline and candidate artifacts with the short 1.21.11 steady-world profile; sequential runs, 25 local bots, 60-second warm-up, 180-second sample, 2 repetitions. No comparison has been run for this change.
- **Environment:** Windows 11, 32 logical CPUs, 64 GiB RAM, Java 21.0.12.1, `-Xms4G -Xmx4G`.
- **Workload:** Pre-generated shared world snapshot, steady-world movement, no plugins.
- **Results:** Not measured. Local Gradle daemon failed before project configuration with `Unable to establish loopback connection`.
- **Conclusion:** Not measured; no gain claim.
- **Remaining checks:** Patch application, branch build, candidate artifact, before/after profile, lag-threshold behavior, and plugin compatibility review.
