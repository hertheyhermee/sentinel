# 4. Feature-branch workflow with required status checks
Date: 2026-08-11
## Status
Accepted
## Context
Phase 1 was committed directly to `main` in small, sequential commits. That
was reasonable for standing up the first working slice alone, but it does not
reflect how teams actually ship, and it does not let CI act as a real gate:
a broken commit could land on `main` with nothing stopping it, and reviewers
have nothing meaningful to look at because the change is already merged.
From Phase 2 onward, changes go through a pull request instead. That only
matters if merging is actually blocked on the checks passing; a convention
that is not enforced by branch protection is not a gate, it is a suggestion.
## Decision
Work happens on branches named `feat/<short-description>`, `fix/<short-description>`
or `chore/<short-description>`, never directly on `main`. Each lands as a pull
request into `main`.
Branch protection on `main` requires: the `Lint`, `Unit tests`, `Build and scan
(api)`, `Build and scan (worker)`, `Build and scan (scheduler)` and
`Integration test (docker compose)` checks to pass, the branch to be up to date
with `main` before merging, and at least one approving review (self-approval is
not possible on GitHub, so in practice this means either a collaborator reviews
it, or, working solo, the rule is relaxed to "checks must pass" without a
required-reviewer count — recorded honestly below rather than pretended).
Direct pushes to `main`, including from an administrator, are blocked.
## Consequences
Positive: `main` is always the thing CI most recently validated, not just the
thing that was typed most recently. Pull requests give a natural place to
attach validation evidence, and the required-checks list is a direct,
inspectable statement of what "done" means for this repository.
Negative: solo development through PRs is slower than pushing straight to
`main`, and a required-reviewer rule is not meaningful with a single
contributor — that requirement is deliberately left off rather than satisfied
by self-approval, which would defeat its purpose. If a collaborator joins
later, a required-reviewer count should be added and this ADR superseded.
