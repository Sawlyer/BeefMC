# Hopper Amount Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Fix configured hopper transfer amounts under sleeping block entity optimization on all active modern versions.

**Architecture:** Integration test starts isolated BeefMC server through RCON and checks inventory counts. One upstream-shaped patch changes extraction and remainder restoration on each modern version; version branches retain independent patches.

**Tech Stack:** Java, paperweight patches, Gradle, Node.js, Minecraft RCON.

**Spec:** `docs/superpowers/specs/2026-10-30-hopper-amount-design.md`

## Global Constraints

- Active versions: 1.8.8, 1.21.11, 26.1.2, 26.3.
- Preserve plugin compatibility and inherited behavior by default.
- Do not change `performance.sleeping-block-entity` default.
- Do not claim a performance gain without comparable measurements.

## Review Focus

- Destination accepts only part of extraction: remainder returns to source; inventory counts conserved.
- Source becomes empty before restore: restored stack goes back into original slot.
- Destination has full capacity: exactly configured amount transfers.
- Sleeping optimization disabled: original transfer path remains unchanged.
- Plugin cancels extraction: cancelled operation does not remove items.

### Task 1: Reproduction harness

**Files:** Create `scripts/validation/hopper-amount.mjs`.

- [ ] Start isolated server using supplied JAR and Java executable.
- [ ] Configure RCON, `hopper-amount: 5`, `hopper-transfer: 8`, and sleeping-block-entity toggle.
- [ ] Place a forceloaded hopper pair and assert exact source/destination counts.
- [ ] Run against current release to demonstrate enabled-path failure before patch.

### Task 2: Branch patches

**Files:** Update Minecraft source patches for 26.3, 26.1.2, and 1.21.11 through `fixupSourcePatches` and `rebuildPatches`.

- [ ] Apply upstream-shaped bounded extraction and restore only uninserted remainder.
- [ ] Keep original event, `setChanged`, and disabled-path behavior.
- [ ] Run patch workflow and branch build for each version.
- [ ] Run integration harness against each built JAR; verify full and partial transfers.

### Task 3: Measurement and review

**Files:** Update `PERFORMANCE.md` and `docs/performance/OPTIMIZATION_EXPLORATION.md`.

- [ ] Compare sleeping optimization off/on under identical idle hopper workloads.
- [ ] Record CPU, tick time, process memory, configuration, duration, and limitations.
- [ ] Push one PR per version branch; merge only after CI and full diff review.
