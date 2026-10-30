# Sleeping Hopper `hopper-amount` Compatibility

## Intent

Preserve configured hopper transfer amounts when the experimental sleeping block entity path is enabled. Keep the optimization disabled by default until server-owner compatibility testing supports a default change.

## Goals

- Fix extraction on supported modern branches 1.21.11, 26.1.2, and 26.3.
- Transfer no more than `world.spigotConfig.hopperAmount` items in one hopper operation.
- Restore any item count that destination inventory cannot accept.
- Preserve existing event handling, inventory dirty callbacks, and the non-sleeping path.
- Verify transfer behavior and build every affected branch.

## Non-goals

- Change default config values or enable sleeping block entities automatically.
- Change 1.8.8 behavior, plugin APIs, packets, or persisted data.
- Claim CPU or memory gains without a focused BeefMC comparison.

## Approaches

1. Port Leaf PR #952's bounded extraction and remainder restoration. Preferred because it targets the exact shared bug, keeps single-item insertion rules, and has upstream runtime evidence.
2. Disable sleeping block entities whenever `hopper-amount` differs from one. Rejected because it removes the optimization for valid configurations and hides the broken path.
3. Defer the fix. Rejected because an opt-in performance setting currently changes configured gameplay behavior.

## Constraints

- Patch generated Minecraft sources through BeefMC's patch workflow.
- Target only modern branches where the same extraction and event logic is present.
- Keep `performance.sleeping-block-entity` default `false`.

## Verification

Reproduce before the fix with `hopper-amount: 5`, `hopper-transfer: 8`, and sleeping block entities enabled. Assert full transfer moves five items, partial capacity restores remainder without item loss or duplication, and disabled-path behavior remains unchanged. Run patch application and builds on all three branches. Measure the sleeping-block-entity option separately; functional correction alone is not a performance claim.
