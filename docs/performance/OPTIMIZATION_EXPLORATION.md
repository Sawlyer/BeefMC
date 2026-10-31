# BeefMC Optimization Exploration

This log tracks source research, profiling observations, optimization candidates, changes made, and unresolved checks. It complements [`PERFORMANCE.md`](../../PERFORMANCE.md), which remains the record for quantitative comparisons.

## Rules

- Treat upstream benchmark claims as hypotheses, not BeefMC results.
- Preserve Paper behavior and plugin compatibility by default.
- Rank candidates using BeefMC profiles and relevant workload, not patch count or upstream popularity.
- Change one behavior or setting at a time. Build every affected version and compare identical baseline/candidate runs.
- Record neutral and negative results. Keep unmeasured candidates marked `Not measured`.
- Do not enable experimental behavior by default until runtime behavior and compatibility are checked.

## Scope and environment

- **Active versions:** 1.8.8, 1.21.11, 26.1.2, 26.3. Apply optimization work only where the source and build pipeline support it.
- **Profiling reference:** 1.21.11, 50 local Mineflayer bots, no plugins, shared world snapshot, Temurin Java 21.0.12.1, fixed `-Xms4G -Xmx4G`, Ryzen 9 9950X, Windows 11 build 26300.
- **Reference profiles:** steady-world and exploration, each one 20-second warm-up plus 60-second measured window. Full metrics and limits live in [`PERFORMANCE.md`](../../PERFORMANCE.md).
- **Current status:** `optimize-waypoint` has a repeated workload-specific MSPT/allocation result; CPU and process RAM benefits are unproven. No new server patch has qualified for v0.0.2.

## Findings from BeefMC profiles

The 50-bot profiles recorded frequent server-thread samples in `ChunkMap$TrackedEntity.updatePlayerMulti`, `ChunkEntitySlices$EntityCollectionBySection.getEntities`, `Entity.getBukkitEntity`, and Leaf's `ChunkCache.get`. Allocation samples repeatedly included `ServerWaypointManager.updatePlayer` / `updateWaypoint`, Guava `StandardTable` / `ImmutableSet`, and collision `AABB.inflate`.

These are sampling observations, not exact CPU shares or allocation totals. The workload had no plugins, only one run per scenario, and low average tick time. Findings prioritize focused A/B tests; they do not justify broad rewrites or changed defaults.

The fixed 4 GiB heap had JFR post-GC snapshots near 0.50 GiB, while pre-GC snapshots reached 2.69–2.87 GiB. This does not prove a smaller production heap is safe: only a few collection points were captured, and the test omitted plugins and production data.

## Ranked candidates

### P1 — `optimize-waypoint` A/B

- **Evidence:** waypoint update methods appear repeatedly in allocation samples. BeefMC already carries Leaf's experimental `optimize-waypoint` switch, default `false`.
- **Expected effect:** avoid some waypoint tracking work when entity movement does not change block position. Likely workload-specific; strongest case is many tracked entities and locator-bar updates.
- **Compatibility risk:** low-to-medium, because locator-bar visibility and tracking are player-visible behavior. Setting must remain opt-in unless tests establish correctness and compatibility.
- **Status:** three runs per setting complete. MSPT averages and JFR waypoint-stack allocation weights decreased in every pair; CPU result mixed and process memory unchanged. Promising for this workload, not proof for production. See `PERFORMANCE.md` for per-run figures.
- **Decision:** keep default `false`. Locator-bar behavior with a real client remains unverified. Owner excluded plugin compatibility checks from this roadmap.
- **Review note:** Leaf's upstream commit [`3606c2f`](https://github.com/Winds-Studio/Leaf/commit/3606c2f) corrected a condition so waypoint connections can be cleared when the locator bar is disabled. Verify this behavior in BeefMC's exact patch before accepting any result.

### P2 — Entity tracking and nearby-entity lookup

- **Evidence:** with `optimize-waypoint` enabled, JFR's top server-thread frames across three runs included `ChunkEntitySlices$EntityCollectionBySection.getEntities` (73 samples), `ChunkCache.get` (62), `ChunkMap$TrackedEntity.updatePlayerMulti` (52), and `BlockStateBase.randomTick` (51). Counts describe samples, not CPU percentages.
- **Expected effect:** possible CPU reduction with many moving entities or dense player/entity visibility overlap.
- **Complexity and risk:** high. Entity visibility is observable to plugins and players; tracker changes touch concurrency, lifecycle, and spawn/despawn semantics.
- **Status:** source-level follow-up only. The 50-bot workload does not isolate a dense-entity case. Leaf's historical [NPC compatibility report](https://github.com/Winds-Studio/Leaf/issues/44) describes disappearing NPCs with its async tracker and a maintainer advised disabling it at that time. This is a caution, not proof of current Leaf behavior. Keep BeefMC's async tracker disabled.

### P3 — Chunk-cache lookup

- **Evidence:** `ChunkCache.get` was the second most frequent top frame in the combined waypoint-on samples. Its current code already uses a last-entry key/value fast path and a fastutil open-addressing long-key map.
- **Expected effect:** limited to code paths that repeatedly resolve nearby chunks; likely dependent on player movement and chunk churn.
- **Complexity and risk:** medium-to-high. Cache invalidation and world/chunk lifecycle must stay correct.
- **Status:** profile a movement/chunk-loading workload before considering code changes. Current steady-world results do not quantify benefit.

### P4 — Heap sizing and allocation reduction

- **Evidence:** JFR allocation samples include waypoint tracking and collision lookup; post-GC heap snapshots are much lower than pre-GC snapshots.
- **Expected effect:** allocation reductions may reduce collection frequency under matching workloads. Lowering `-Xmx` may save reserved/committed memory only depending on JVM flags, and may cause more frequent or longer GC pauses.
- **Complexity and risk:** low for a startup-flag experiment, high operational impact if production plugins or peak workloads exceed the test.
- **Status:** do not recommend a smaller heap from current data. Capture continuous heap/GC telemetry under representative plugins and peak activity first.

### P5 — Collision and mob-tick paths

- **Evidence:** `AABB.inflate`, `randomTick`, and `NaturalSpawner.spawnForChunk` occur in samples, but not enough to establish dominant cost.
- **Expected effect:** workload-dependent; dense entities, farms, and exploration may differ substantially.
- **Status:** defer until a targeted workload and repeated profile show a stable hotspot. Changes can alter gameplay or farm behavior.

### P6 — 5-second TPS lagging check

- **Evidence:** existing patch avoids computing unused 1-minute, 5-minute, and 15-minute TPS windows in a frequent check. It did not stand out in current 50-bot samples.
- **Expected effect:** small CPU reduction if the path runs frequently under lagging conditions.
- **Compatibility risk:** low if the same 5-second value and threshold are preserved.
- **Status:** merged on 1.21.11, 26.1.2, and 26.3; build and available runtime workflows passed. No BeefMC before/after performance profile exists. See [`PERFORMANCE.md`](../../PERFORMANCE.md).

### P7 — Temporary light-buffer reference cleanup

- **Evidence:** PRs #8–#10 clear used ThreadLocal buffer slots after cloning light packet arrays. The original hypothesis is lower retained heap on long-lived threads.
- **Test:** source-matched 1.21.11 A/B, three paired 50-bot exploration runs, 20-second warm-up, 60-second measurement, fixed Java/JVM/world, six JFR after-GC snapshots per variant. All six runs completed with 50 bots and 12 MSPT samples.
- **Result:** no repeatable memory reduction. Mean working set was 4,062 MiB baseline versus 4,212 MiB candidate; mean post-GC heap was 0.531 versus 0.558 GiB. Private bytes were effectively unchanged. CPU/MSPT pairs were mixed.
- **Decision:** do not merge for v0.0.2. Close PR #8; PRs #9 and #10 have no version-specific measurement. Full figures and raw run paths are in [`PERFORMANCE.md`](../../PERFORMANCE.md).

## Upstream review

### Leaf

BeefMC's current codebase already includes Leaf-derived work for waypoint tracking, entity tracking, chunk handling, mob spawning, packet paths, and other areas. Inspect current BeefMC patches first; do not re-port duplicates from temporary clones or archives. The upstream waypoint fix above is specifically relevant to the correctness review.

#### Sleeping block entity hopper amount compatibility

- **Finding:** the cached Lithium extraction path removes exactly one item with `from.removeItem(fromSlot, 1)`, bypassing `world.spigotConfig.hopperAmount` whenever `performance.sleeping-block-entity` is enabled. The option defaults to `false`, so normal defaults do not activate this path.
- **Affected BeefMC patches:** 1.21.11 `0327-Leaves-Lithium-Sleeping-Block-Entity.patch`, 26.1.2 `0307-Leaves-Lithium-Sleeping-Block-Entity.patch`, 26.3 `0285-Leaves-Lithium-Sleeping-Block-Entity.patch`. Same extraction logic appears in all three.
- **Upstream reference:** [Leaf PR #952](https://github.com/Winds-Studio/Leaf/pull/952) adds bounded multi-item extraction and restores any uninserted remainder. Its author reports compile and RCON testing with `hopper-amount: 5`, `hopper-transfer: 8`, and the sleeping block entity option enabled. PR remains review evidence, not BeefMC verification.
- **Risk:** gameplay/config compatibility, not a performance opportunity. Fix should preserve item counts when destination accepts only part of transfer, plus inventory dirty/update callbacks.
- **Status:** implemented on 1.21.11, 26.1.2, and 26.3; CI integration checks passed with sleeping mode both disabled and enabled. Item conservation and configured transfer amounts passed for empty and nearly-full destinations. See [`PERFORMANCE.md`](../../PERFORMANCE.md). Compatibility fix only; no performance gain claimed. Plugin behavior remains outside owner-approved scope.

### SparklyPaper

The [SparklyPaper source repository](https://github.com/SparklyPower/SparklyPaper) describes targeted changes such as avoiding a `distanceToSqr` call when an entity's delta movement object is reused, avoiding map updates when a custom renderer replaces the default renderer, and optional hopper-check throttling. These are candidate patterns, not automatic ports:

- The entity-motion optimization is worth revisiting only if BeefMC profiling shows `ServerEntity.sendChanges` distance checks in a representative entity-motion workload.
- The map optimization has a custom-renderer-specific compatibility contract and should be tested with map plugins before porting.
- Hopper throttling can change timing/gameplay behavior; defer unless container-heavy profiling shows a need and farm/plugin checks are defined.

No SparklyPaper code was copied as part of this exploration.

### Pufferfish

Pufferfish-derived behavior controls such as dynamic activation or asynchronous mob spawning can affect mob timing, farms, and plugins. Current BeefMC profiles do not show enough mob-tick cost to justify changing defaults. Revisit only with a farm/mob-density workload and explicit behavior checks.

### Open Leaf optimization PR review — 2026-10-31

Upstream PR descriptions and benchmarks are evidence for deciding what to inspect, not BeefMC results.

- [Leaf #972 — Optimize structure layout](https://github.com/Winds-Studio/Leaf/pull/972): targets jigsaw generation on 26.3, adds about 350 lines and an opt-in setting. Upstream reports lower time in jigsaw placement but says overall pregeneration time stayed about the same because the path used less than 0.5% of worker time. High implementation cost for negligible whole-workload return; defer.
- [Leaf #961 — Skip nearby-player checks when fire spreading is disabled](https://github.com/Winds-Studio/Leaf/pull/961): five-line guard for fire-spread radius zero; applies only when that gamerule is disabled. Upstream reports about 0.52 ms/tick on a server with roughly 230 players. Low code cost, but conditional relevance and no BeefMC workload measurement; revisit only if supported network configs disable fire spread.
- [Leaf #928 — Defer container item decoding](https://github.com/Winds-Studio/Leaf/pull/928): targets branch `ver/26.2`, outside active support scope. The multi-class lazy-loading change needs inventory lifecycle and data compatibility review before any port; defer.
- [Leaf #919 — Bellows optimization](https://github.com/Winds-Studio/Leaf/pull/919): also targets `ver/26.2`; PR author marks NBT work and performance-impact testing incomplete. Defer.
- [Leaf #854 — Optimize tickPrecipitation](https://github.com/Winds-Studio/Leaf/pull/854): targets `ver/26.2`, has a dirty merge state and no passing build check in its current open PR. No port.
- [Leaf #537 — Cache `Entity#isAlive`](https://github.com/Winds-Studio/Leaf/pull/537): targets 26.3 and has a passing upstream build, but no workload measurement in its PR record; caching entity lifecycle state adds correctness risk. Defer pending BeefMC profile and transition tests.
- [Leaf #970 — Compute only 5-second TPS for lag checks](https://github.com/Winds-Studio/Leaf/pull/970): duplicates the already merged BeefMC TPS patch. No additional port needed.

## Changes and corrective work

### Benchmark collection fixes

These changes improve measurement collection; they do not change server behavior:

- `scripts/benchmark/lib/metrics.mjs`: convert `jstat` memory values from KiB to bytes; parse MSPT output when Windows console rendering removes the marker glyph.
- `scripts/benchmark/lib/profiler.mjs`: start Java Flight Recorder with the JVM instead of attaching later through `jcmd`, avoiding the Windows loopback attach failure encountered in this environment.
- `scripts/benchmark/lib/metrics.mjs` and `scripts/benchmark/lib/profiler.mjs`: parse time-bounded `jdk.GCHeapSummary` after-GC events from JFR when `jstat` cannot attach.
- `scripts/benchmark/run.mjs`: record JFR from startup, collect `/mspt`, retain raw heap snapshots, and keep tick metrics distinct from process CPU and memory.
- `tests/benchmark/`: regression coverage for metrics parsing and profiler arguments. Current run: `node --test tests/benchmark/*.test.mjs`, 37 tests passed.

The 50-bot run logs were parsed after the MSPT marker fallback was added. The measured profile values are in `PERFORMANCE.md`; no raw result artifacts were rewritten.

### Server behavior changes

No new server behavior change was applied during this audit. The source-matched light-buffer comparison did not support the expected memory benefit; no candidate was added to the release branch. Benchmark runs and one-bot startup/shutdown smoke now complete in the local Test Server environment. No plugin, proxy, or real-client compatibility tests were run.

## Next work

1. Profile entity tracking, chunk loading/generation, and container/redstone work as separate workloads before proposing another source change.
2. Review upstream optimization PRs only where supported versions and BeefMC workload match; do not import version-specific or unmeasured work as a release quick win.
3. Keep plugin, proxy, and real-client tests omitted per owner decision; record those limits without claiming compatibility evidence.
4. Select next release candidate only after repeated BeefMC measurements show relevant improvement without unacceptable regressions.

## Research log

- **2026-10-30:** reviewed the 1.21.11 50-bot JFR samples, server CPU/MSPT and memory data, active BeefMC patch coverage, Leaf waypoint condition fix, Leaf async-tracker NPC report, and SparklyPaper's documented patch targets. Added this log and linked future updates through `AGENTS.md`.
- **2026-10-30:** initial waypoint A/B and one confirmation pair completed from normal PowerShell. Six runs passed validity checks. MSPT and waypoint-stack JFR allocation weights moved down in all three pairs; CPU and process-memory evidence does not establish a general gain. Codex-launched attempt before these runs failed on Windows loopback selector initialization and produced no valid samples.
- **2026-10-30:** verified generated config directory differences; only `optimize-waypoint` differed in server configuration. JFR profiling after waypoint optimization shifted leading samples to entity lookup/tracking and chunk-cache paths.
- **2026-10-31:** added `jdk.GCHeapSummary` parsing to the benchmark harness after `jstat` produced no samples. Six source-matched 1.21.11 light-buffer runs completed; memory and performance benefit was not demonstrated, so patch was excluded from release scope.
- **2026-10-31:** reviewed open Leaf optimization PRs #972, #961, #928, #919, #854, and #537. No immediate cross-version candidate met BeefMC evidence and compatibility criteria; see PR inventory in this log.
