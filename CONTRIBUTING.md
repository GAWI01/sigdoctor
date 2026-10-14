# Contributing

This iteration ends at a reliable single-rule PowerShell telemetry assessment.
Read docs/FEASIBILITY.md and docs/ARCHITECTURE.md before proposing changes.
Process creation, authentication, PowerShell 7 and bulk coverage require a new
scope decision; they are not unfinished tasks to fill in automatically.

Create a virtual environment and install requirements-dev.lock, then install
the checkout with `python -m pip install --no-deps -e .`. Run pytest, ruff check,
ruff format --check, mypy src and python -m build as documented in README.md.
The development lock uses mypy's official pure-Python wheel because a compiled
wheel was blocked by Windows application control on the development machine.

For behavior changes, first write a failing scenario with independently expected
results, then implement the fix. Mock only external boundaries. Do not equate
fake evidence with real Windows validation. Keep evaluator ownership and source
provenance intact. Missing information must never become READY through fallback.

Use self-authored fixtures. Do not add upstream rule packs, real event contents,
credentials or sensitive host metadata. Update dependency/version and license
records together; requirements.lock is a tested exact resolution, not a claim
of byte-identical builds or a vulnerability audit. Preserve the existing license.

Open PRs with the problem, resulting behavior, verification and remaining limits.
No project release, publish, deploy or automatic remediation is part of this work.
