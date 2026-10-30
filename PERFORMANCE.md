# BeefMC Performance and Memory Measurements

This file records reproducible BeefMC-specific memory and performance comparisons. It is not a general development history.

No BeefMC-specific memory or performance gain is documented yet. Results inherited from PandaSpigot, Leaf, Paper, or other upstream projects are not BeefMC measurements.

## Temporary light-update buffer references — implemented, not measured

- **Status:** Implemented; BeefMC-specific memory gain is Not measured.
- **Date and reference:** 2026-10-30; issue #7.
- **Minecraft versions:** 1.21.11, 26.1.2, and 26.3. Version 1.8.8 does not use this packet implementation.
- **Changed area:** ClientboundLightUpdatePacketData; clear used ThreadLocal sky/block buffer slots immediately after cloning section arrays into packet-owned arrays.
- **Hypothesis:** long-lived server threads stop retaining references to light arrays after packet construction. Packet payloads remain backed by independent clones.
- **Compatibility:** no plugin API, configuration, world data, gameplay rule, or packet format change expected. Chunk-light packet behavior still needs runtime confirmation.
- **Method:** Not measured. Planned focused comparison: identical chunk-exploration workload and JVM settings; capture heap histogram after warm-up and after repeated chunk movement, plus working set and GC data. Current benchmark does not expose ThreadLocal retained bytes.
- **Environment:** Not measured. Intended host: Windows 11, Ryzen 9 9950X, 61.6 GiB RAM; Java 21 for 1.21.11 and Java 25 for 26.x.
- **Workload:** Not measured. Planned offline Mineflayer exploration bots in a shared pre-generated world; no plugins.
- **Results:** Not measured. No memory or performance gain claimed.
- **Conclusion:** The code now releases temporary buffer references after cloning. Effect size and client-visible behavior remain unverified at runtime.
- **Remaining checks:** runtime chunk-light behavior on all three versions; heap retention comparison; plugin compatibility sampling. No equivalent backport planned for 1.8.8.
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
