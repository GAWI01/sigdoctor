# PowerShell slice implementation plan

**Goal:** Prove the scoped feasibility hypothesis with one offline `check` flow.
**Architecture:** See ARCHITECTURE.md. One adapter, profile, probe, evaluator and
two renderers; immutable domain records. No later telemetry families.
**Stack:** Python 3.11+, pySigma 2.0.1, PyYAML, stdlib; pytest, ruff, mypy, build.
**Spec:** FEASIBILITY.md and ARCHITECTURE.md.

## Constraints and review focus

Read-only, offline at runtime, bounded untrusted inputs, no copied upstream rule
packs, no push/publish/deploy. User explicitly authorized continued implementation
after feasibility, so no additional design approval is needed. Work stays in the
existing clean checkout on `codex/powershell-slice`; no extra worktree needed.
Implement inline and obtain a final independent review.

Review traps: unused selectors mistaken for requirements; OR/NOT EventID semantics;
missing policy mistaken for disabled; historical/foreign/encrypted events mistaken
for current plaintext capability; malformed input or native errors leaking content.

## Tasks

1. [x] Write end-to-end/domain/adapter tests with literal expected statuses and
   reasons, including unsupported semantics and malformed input. Run and observe
   missing implementation failure, then implement the minimal package/domain,
   strict YAML adapter, profile, evaluator and renderers. Run full test suite.
2. [x] Write probe tests using injected registry and subprocess boundaries for
   enabled/disabled/missing/denied/timeout/XML/stale/protected cases. Observe
   failures, implement fixed read-only probes, then run full test suite.
3. [x] Write CLI tests for check/JSON/help/version/errors and no sensitive output.
   Observe failures, implement argparse entry point, then run full test suite.
4. [x] Verify actual Windows probe behavior without changing policy. Build and
   install wheel into a clean environment. Run format/lint/types/tests/CLI/build.
   Record exact outcomes, dependency licenses, README/security/contribution docs
   and a minimal CI workflow. Review the full implementation and fix material
   findings with regression tests. Stop with the specified handoff.

Interfaces: adapter `load_rule(Path) -> RuleRequirements`; profile
`load_profile() -> TelemetryProfile`; probe `collect() -> tuple[Evidence, ...]`;
orchestrator `check_rule(Path, probe=None) -> Assessment`; renderer
`render_terminal(Assessment) -> str`, `render_json(Assessment) -> str`; CLI
`main(argv=None) -> int`. Evaluator alone owns final status.

## Execution record

* Inspection and feasibility complete. Sources and 12-rule study in FEASIBILITY.md.
* Ruling: narrow provider/field support rather than speculative general inference;
  cost is more UNKNOWN results, explicitly preferable to false confidence.
* Ruling: use JSON for the one internal telemetry profile; keeps readable data
  without a second YAML entrypoint or generic plugin infrastructure.
* Task 1/2/3 tests were written before their implementation; first runs failed
  collection because the relevant modules did not yet exist. Subsequent runs:
  43 core tests, 73 with probes, 85 with CLI, then review regressions added.
* Test-harness correction: short pytest IDs prevent a large input from exceeding
  Windows' 32767-character environment-variable limit. The input bound itself
  was then tested, rather than treating harness failure as application evidence.
* Independent review identified multi-value modifier false READY, pre-validation
  expansion risk and UNC resolution before rejection. All reproduced with failing
  tests, corrected, then independently rechecked (62 focused tests passed).
* Ruling: known unsupported modifiers cause UNKNOWN before full Sigma validation,
  including unused selectors, to prevent eager expansion. The result states this
  limitation. Unknown modifier names still fail as invalid input.
* Ruling: reject reparse points and network drives, not merely explicit UNC syntax.
  More restrictive local paths are preferable to implicit remote authentication.
* Native mypy wheel blocked by Windows application control. Official pure-Python
  wheel installed successfully; type checking passes without changing policy.
* Real Windows observation: policy UNKNOWN, channel ENABLED, event and native
  plaintext field OBSERVED; overall UNKNOWN as required. No policy changes made.
* Task 4 complete: 92 default tests passed, one opt-in skipped; real Windows
  integration passed separately. Ruff, format, mypy, build and dependency checks
  passed. Clean wheel install and smoke checks passed outside the checkout.
  Six pinned research rules mapped generically. Exact commands and remaining
  unverified behavior are recorded in VERIFICATION.md. Stop at this iteration.
