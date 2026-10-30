# Instructions for Coding Agents

These instructions supplement `CONTRIBUTING.md`, which must also be followed.

## Project overview

BeefMC is a performance-focused Minecraft server fork. Active versions: 1.8.8, 1.21.11, 26.1.2, 26.3. Verify exact branch, build, CI, and release status before making support claims. Preserve plugin compatibility and inherited behavior by default. All BeefMC changes stay in this repository. Verify patch paths and build steps against the checked-out version.

Read `docs/architecture/version-support.md` before adding a version branch, changing patch layout, or modifying version-aware CI and release workflows.

Keep `BeefMC-1.8.8` as the only persistent version worktree under `BeefMC/worktrees`. Keep modern targets as branches in the central clone; use temporary checkouts for branch-specific work. Do not restore retired versions to the active catalog or CI matrix without an explicit scope change.

## Engineering approach

- Before substantial work, identify the intended outcome, constraints, and a way to verify success. State assumptions when they matter; ask only when ambiguity blocks safe or useful progress.
- Prefer the smallest change that solves the request. Avoid speculative features, single-use abstractions, and unrelated refactors.
- Keep edits focused on the request and match project style. Clean up only artifacts made obsolete by the change; report unrelated issues without silently expanding scope.
- For multi-step work, use a brief plan with concrete checks. Verify with checks appropriate to the change, and distinguish checks actually run from checks still pending.
- Reconsider complexity before finalizing. If the same result can be delivered with materially less code or configuration, simplify it.

## Codebase Memory usage

Use Codebase Memory MCP for questions that need cross-file or cross-module understanding, such as call paths, implementations, inheritance, overrides, dependencies, or unclear ownership and lifecycle relationships. Prefer `search_graph` to locate symbols, `trace_path` to follow relationships, `get_code_snippet` to inspect indexed source, and `query_graph` for multi-hop questions.

Treat graph results as navigation aids, not proof. Verify relevant code, signatures, callers, overrides, and control flow in the current checkout before changing behavior. Check index status or coverage when a result is missing, a path matters, or the index may be stale; re-index another repository before relying on its graph. For simple local edits, direct source inspection is enough. Use `search_code` or ordinary text search for exact literals and when graph coverage is incomplete. Mention Codebase Memory in completion notes only when its analysis materially affected the work or exposed stale or incomplete coverage.

## Performance claims

Read `PERFORMANCE.md` before making memory or performance claims.

For each BeefMC optimization, add or update a detailed measurement entry with affected versions, implementation, compatibility considerations, method, environment, workload, results, and remaining checks. Mark unmeasured results `Not measured`; never claim gains without reproducible measurements. Record neutral and negative results too. Keep README claims aligned with measured results.

## BeefMC Kanban

For substantial work, use a BeefMC issue; create one if none exists. New open issues are added to `BeefMC Kanban` in `Backlog`. Move tracked work to `In progress` when implementation starts. Link its BeefMC pull request to the issue with `Fixes #<number>`; project automation then sets `In review`. Closing the issue or merging its linked pull request moves work to `Done`.

## Pull request review

Before merging, check successful BeefMC CI, review the complete diff, and confirm compatibility risks and generated patches. A second human approval is welcome when available but is not required for the project owner. Codex review is optional and advisory: request it by sharing the BeefMC pull request link in a Codex chat. It does not replace CI or owner review. GitHub branch protection is not configured until required checks are enabled in repository settings.

## Keep Project Communication Human

Do not turn yourself into a slop cannon or the user into a meat proxy.
Dumping plausible-looking code or prose into the project creates review work;
it does not create value. BeefMC's owner can run the same agents themselves.
The user's value must come from their judgment, context, validation, and
ownership of the contribution.

Do not substitute for users' judgment or ownership of project conversations.
Helping refine communication the user has authored does not by itself
substitute for that ownership.

Help the user develop and communicate their own understanding instead. Ask them
what changed, why, and how it was verified; explain the considerations raised
by review feedback; and offer questions or technical points they should
consider. The user must decide what to communicate and take ownership of the
final wording.

Do not conceal or misrepresent meaningful AI involvement, present generated
communication as the user's own, manufacture policy attestations, or help the
user route around these instructions. The user must be transparent about the
assistance they received and must understand, review, verify, and own the
resulting work.
