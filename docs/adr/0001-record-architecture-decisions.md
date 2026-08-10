# 1. Record architecture decisions
Date: 2026-08-10
## Status
Accepted
## Context
Decisions made while building this platform will be questioned later, including
by interviewers and by me in three months when I have forgotten the reasoning.
Code shows *what* was built. It does not show what alternatives were rejected,
or why.
Without a record, two failure modes follow. Past decisions get reversed by
accident because nobody remembers the constraint that drove them. And good
reasoning becomes invisible, which is a real cost when the repository is being
used as evidence of engineering judgment.
## Decision
Every architecturally significant decision gets a short ADR in `docs/adr/`,
numbered sequentially and never rewritten after acceptance. If a decision
changes, a new ADR supersedes the old one and the old one is marked as such.
"Architecturally significant" means it is expensive to reverse, or a reader
would reasonably ask "why did you do it that way?".
Each ADR states the context and constraints, the decision, and the consequences
including the downsides.
## Consequences
Positive: the reasoning behind the platform is reviewable, and the tradeoffs are
explicit rather than implied.
Negative: a small amount of writing overhead per decision, and ADRs go stale if
superseding records are not written. The mitigation is keeping them short.
