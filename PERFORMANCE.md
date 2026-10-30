# BeefMC Performance and Memory Measurements

This file records reproducible BeefMC-specific memory and performance comparisons. It is not a general development history.

No BeefMC-specific memory or performance gain is documented yet. Results inherited from PandaSpigot, Leaf, Paper, or other upstream projects are not BeefMC measurements.

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
