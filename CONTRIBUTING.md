# Contributing to BeefMC

BeefMC is a Minecraft server fork focused on performance, memory use, and plugin compatibility. The project is primarily maintained by its owner. External contributions are welcome, but discuss significant changes before starting work.

## Before you start

- Read [AGENTS.md](AGENTS.md) for instructions intended for coding agents.
- For an optimization, describe the observed problem, workload, and expected result. An assumed improvement is not a substitute for measurement.
- For a change visible to plugins or server administrators, document the expected behavior and any compatibility concerns.
- Keep each change focused on one clear goal. Avoid unrelated edits.

## Set up the repository

Requirements: Git and the JDK required by the targeted Minecraft version. Java versions and exact commands can vary between branches; check the Gradle files in your checkout before building.

```powershell
git clone https://github.com/Sawlyer/BeefMC.git
cd BeefMC
```

Use the patch workflow for the checked-out version. For 1.8.8, run `./beefmc setup`; for modern versions, run `./gradlew applyAllPatches`. On Windows, use `gradlew` rather than `./gradlew`.

Changes to applied Minecraft sources must be recorded in BeefMC patches using the tasks provided by the repository, including `gradlew fixupSourcePatches` and `gradlew rebuildPatches` when required by the change. Do not edit a generated patch directly without following the project workflow.

## Branches and continuous integration

All BeefMC pull requests target this repository. Do not open pull requests against source repositories.

The active support scope is 1.8.8, 1.21.11, 26.1.2, and 26.3. `main` tracks 26.3. The other branches are `version/1.8.8`, `version/1.21.11`, and `version/26.1.2`. Versions 26.2, 26.1.3, and all other versions are outside current scope. See the [version support guide](docs/architecture/version-support.md) for source mapping, patch layout, JDK selection, CI, and release policy.

GitHub Actions selects the JDK and patch workflow from `versions/catalog.yml`. CI runs `./beefmc setup` for 1.8.8 and `./gradlew applyAllPatches` followed by `build` for modern branches. Keep the catalog, CI, release workflow, and support guide aligned when changing a selected version. A successful build alone does not establish runtime or plugin compatibility.

For substantial work, use a BeefMC issue. The `BeefMC Kanban` board automatically adds new open issues to `Backlog`. Move an issue to `In progress` when work starts. Link the BeefMC pull request with `Fixes #<number>`; the issue then moves to `In review` and reaches `Done` when closed or merged.

CI checks the build and project validations. It does not publish artifacts or deploy to the Minecraft networks. A successful CI build is not a benchmark and does not, by itself, prove compatibility with every plugin.

## Verification

Run checks appropriate to the change and targeted version. For optimizations, compare the same workload before and after with the same hardware, configuration, Java version, plugins, and measurement duration. At a minimum, examine tick times, GC pauses, and memory use; report the method and limitations of the results.

Changes should preserve upstream behavior, API contracts, persisted formats, and plugin compatibility by default. Describe and justify any intentional deviation.

## Review before merge

Do not merge a pull request until BeefMC CI has completed successfully and its changes have been reviewed. As the project owner, review your own pull request's full diff, CI results, compatibility risks, and any generated patches before merging. A second human approval is welcome when a reviewer is available, but is not required for the owner to merge.

Codex review is optional and is not installed as a GitHub bot or automatic workflow. To request one, share the BeefMC pull request link in a Codex chat. Codex can inspect the diff and available checks, then report findings for the owner to assess. This review does not replace CI or the owner's decision to merge.

GitHub branch protection is not configured yet. Until required status checks are enabled in repository settings, the CI requirement is documented workflow guidance rather than a GitHub-enforced merge block.

## Pull requests

A pull request should explain the problem, solution, affected versions, checks performed, and measured results for optimizations. Clearly identify behavior changes and compatibility risks. Do not claim builds, tests, or benchmarks were run if they were not.

Documentation changes do not require a build. Code changes should be checked on the branches and versions they actually target; support for historical versions must not be assumed.
