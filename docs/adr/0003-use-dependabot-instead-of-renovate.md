# 3. Use Dependabot instead of Renovate
Date: 2026-08-11
## Status
Accepted
## Context
The original plan named Renovate for automated dependency updates. Renovate is
capable and widely used, but it requires installing the Mend Renovate GitHub
App to the account or repository before it runs, which is an extra external
signup step outside plain git and GitHub.
Dependabot is built into GitHub itself. A single `dependabot.yml` file is
enough; there is no app to install and no third-party service to trust with
repository access. For a solo portfolio project with three simple update
surfaces — pip requirements, Docker base images per service, and pinned
GitHub Actions versions — Dependabot's feature set is sufficient.
## Decision
Use Dependabot, configured for the `pip`, `docker` and `github-actions`
ecosystems, instead of Renovate.
## Consequences
Positive: zero external setup, one file, native GitHub PR checks apply to
Dependabot's PRs the same as any other PR.
Negative: Dependabot's grouping and scheduling options are less flexible than
Renovate's. If update PR volume becomes noisy as the platform grows, Renovate
remains a reasonable future migration and this ADR should be superseded rather
than silently ignored.
