# BeefMC Version Support

BeefMC currently targets Minecraft 1.8.8, 1.21.11, 26.1.2, and 26.3. Each version follows its own upstream source, Java toolchain, and patch workflow. A version is supported only to the extent recorded in `versions/catalog.yml`.

| Minecraft | Branch | Base | Build JDK | Catalog status |
|---|---|---|---:|---|
| 1.8.8 | `version/1.8.8` | Legacy baseline | 17 | `build-checked` |
| 1.21.11 | `version/1.21.11` | Modern baseline | 21 | `branch-ready` |
| 26.1.2 | `version/26.1.2` | Modern baseline | 25 | `branch-ready` |
| 26.3 | `main` | Modern baseline | 25 | `branch-ready` |

BeefMC does not describe branch-ready builds as production-ready. The active scope excludes 26.2, 26.1.3, and other Minecraft versions.

## Branch and patch layout

- `main` tracks Minecraft 26.3.
- `version/1.8.8` keeps its native `patches/api` and `patches/server` layout.
- `version/1.21.11`, `version/26.1.2`, and `main` keep the modern patch layout defined by the version catalog.
- Keep `BeefMC-1.8.8` as the only persistent version worktree. Work on modern branches through temporary checkouts from the central repository.
- Keep unrelated source and test-server clones intact.

The upstream repository, ref, and commit for each target are recorded in `versions/catalog.yml` and `versions/upstream-versions.yml`. Do not copy patches between versions without checking target behavior, APIs, and compatibility.

## Toolchains and commands

Version 1.8.8 uses JDK 17 to build Java 8 compatible server classes. Apply patches and build the final jar with `./beefmc setup` and `./beefmc jar`.

Modern versions use JDK 21 for 1.21.11 and JDK 25 for 26.1.2/26.3. Apply patches with `./gradlew applyAllPatches` and build with `./gradlew build`. Create the 1.21.11 jar with `./gradlew :beefmc-server:createMojmapPaperclipJar`; create 26.1.2 and 26.3 jars with `./gradlew :beefmc-server:createPaperclipJar`.

Modern builds generate `config/beefmc-global.yml`. Configuration settings are not imported automatically from other server formats. The administration command is `/beefmc`, with BeefMC permission nodes and `BeefMC.*` JVM properties.

## Catalog and CI

`versions/catalog.yml` maps versions to branches, upstream pins, JDKs, patch roots, commands, status, and artifact names. `versions/upstream-versions.yml` records upstream pins. Keep both files aligned with CI and release automation.

BeefMC CI validates the catalog, selects the branch toolchain, applies upstream patches and BeefMC branding, then runs available build checks. CI does not publish jars or deploy to either Minecraft network. A successful compile does not establish runtime stability or plugin compatibility.

## Releases

Create a GitHub release with a `vMAJOR.MINOR.PATCH` tag on `main`. Publishing the release triggers a build matrix for all catalog versions. The workflow builds each version from its matching BeefMC branch, then attaches one jar and one SHA-256 checksum per version.

`v0.0.0` is an initial pre-release. It may include versions at `branch-ready` or `build-checked` status, and must remain marked as a pre-release. Later releases require every catalog version to be `runtime-checked` or `released`. Release automation does not claim plugin compatibility or performance gains beyond recorded checks and measurements.

## HAProxy and performance

BeefMC-owned HAProxy PROXY protocol support applies only to 1.8.8. Preserve inherited behavior on modern versions and distinguish it from BeefMC changes.

Record memory and performance results in `PERFORMANCE.md`. Compare equivalent workloads on the same machine and configuration. Keep results version-specific; make no gain claims without reproducible measurements.
