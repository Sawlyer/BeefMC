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
## 26.1.2 — 5-second TPS lag check (implemented, not measured)

- **Status:** Patch application and CI build passed; CPU and memory effect not measured.
- **Date and reference:** 2026-10-30; BeefMC issue #2.
- **Minecraft versions:** 26.1.2.
- **Changed area:** `leaf-server/minecraft-patches/features/0316-BeefMC-Optimize-5-second-TPS-lag-check.patch`.
- **Hypothesis:** Lag check reads only 5-second TPS. Dedicated helper skips 1-minute, 5-minute, and 15-minute calculations and array creation.
- **Compatibility:** Same 5-second formula, tick interval, and lock. No plugin API or configuration change. CI applied patches and compiled target; focused runtime threshold check not run.
- **Method:** Compile this branch and run focused lag-threshold checks. Intensive before/after profiling remains scoped to 1.21.11; no 26.1.2 profile has run.
- **Environment:** GitHub Actions, Java 25; patch application and CI build passed.
- **Workload:** Focused tick-loop behavior check; no server workload executed for this change.
- **Results:** Not measured. No CPU, memory, or MSPT gain claimed.
- **Conclusion:** Not measured; no gain claim.
- **Remaining checks:** Focused lag-threshold behavior and before/after profile; plugin compatibility review.
