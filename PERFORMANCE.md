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
- **Method:** Isolated RCON integration test with `hopper-amount: 5` and `hopper-transfer: 8`; check empty and nearly full destination hoppers with sleeping mode both disabled and enabled.
- **Environment:** Linux GitHub Actions; Java 21 for 1.21.11, Java 25 for 26.1.2 and 26.3. Local Windows runtime unavailable because Java fails to create the loopback connection.
- **Workload:** Synthetic hopper transfer, no players or plugins.
- **Results:** Functional checks passed on all three versions, with sleeping mode both disabled and enabled. Empty destination: source 63 to 58, destination 0 to 5. Nearly full destination: source 63 to 59, destination 316 to 320; item count conserved. CPU and memory not measured.
- **Conclusion:** Correctness fix only. No optimization claim.
- **Remaining checks:** Production plugin compatibility and real-world hopper scenarios.

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
