# BeefMC Performance and Memory Measurements

This file records reproducible BeefMC-specific memory and performance comparisons. It is not a general development history.

No BeefMC-specific memory or performance gain has been established. Results inherited from PandaSpigot, Leaf, Paper, or other upstream projects are not BeefMC measurements.

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

## 5-second TPS lagging check — not measured

- **Affected versions:** 1.21.11, 26.1.2, and 26.3. Version 1.8.8 has no matching 5-second TPS API path.
- **Implementation:** the tick loop reads only the 5-second TPS window instead of calculating and discarding the 1-minute, 5-minute, and 15-minute averages on every lagging check. No plugin API changes.
- **Compatibility:** intended to preserve the same 5-second threshold value. Tick-rate changes use the current interval for the next check. Build and runtime compatibility checks remain pending.
- **Measurement method:** compare BeefMC before and after with the short 1.21.11 steady-world profile: 25 bots, 60-second warm-up, 180-second sample, 2 sequential repetitions. Capture server CPU and memory separately; heap/GC and TPS/MSPT remain unavailable until their samplers are fixed.
- **Environment and workload:** baseline environment above; no plugins, pre-generated shared world snapshot, Java 21.0.12.1, 4 GiB fixed heap.
- **Results:** Not measured. The source PR reports a JFR hotspot reduction, but that result is not a BeefMC measurement and is not claimed here.
- **Remaining checks:** apply patches and compile all three modern branches; complete the before/after profile on 1.21.11; verify plugin behavior and confirm no lag-threshold regression.

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
