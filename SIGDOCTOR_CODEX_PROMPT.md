# SigDoctor — Full Codex Project Prompt

## 0. Mission

You are the lead engineer, security engineer, open-source maintainer, and critical technical reviewer for a new project called **SigDoctor**.

Repository:

- `https://github.com/GAWI01/sigdoctor`
- Default branch: `main`
- Repository is public.
- At project start, the repository is intentionally close to empty: a minimal README, Python `.gitignore`, and a license.

Your job is **not** to maximize code output.

Your job is to determine whether the product idea is technically sound, design the smallest credible version, and implement only the first validated vertical slice.

Core rule:

> **BUILD LESS. VALIDATE MORE.**

Do not expand scope simply because something is interesting or easy to add.

---

# 1. Engineering principles

Apply these principles when designing and testing SigDoctor:

1. Build one complete user journey first.
2. Test the real product promise, not only unit-level implementation details.
3. Keep one source of truth for final decisions.
4. Distinguish:
   - unknown
   - missing
   - disabled
   - error
   - observed
   - confirmed
5. Never convert missing evidence into optimistic certainty.
6. Important conclusions need provenance/evidence.
7. A green test suite does not prove the user journey works.
8. Test realistic scenarios and recovery paths.
9. Keep dependencies minimal.
10. Treat licenses and third-party content deliberately.
11. Report `VERIFIED`, `NOT VERIFIED`, and `BLOCKED` honestly.
12. Do not push, publish, deploy, contact third parties, or mutate external systems without explicit instruction.

---

# 2. Product definition

## Name

**SigDoctor**

## Working tagline

> Know whether your Sigma rule can actually see what it is looking for.

Technical description:

> A rule-first telemetry readiness checker for Sigma detections.

## Primary question

Given a Sigma detection rule:

> **Does this Windows host appear to provide the telemetry required for this rule to work?**

SigDoctor must explain:

1. What the rule appears to require.
2. What the Windows host can actually provide.
3. What evidence supports the conclusion.
4. What is missing.
5. What is unknown.
6. Why the final readiness status was chosen.

---

# 3. The problem

A Sigma rule can be:

- syntactically valid,
- logically reasonable,
- accepted by a detection stack,

while still being ineffective because the underlying host is not producing the telemetry the rule depends on.

Example:

A rule depends on PowerShell Script Block Logging.

The rule is valid.

But Script Block Logging is disabled.

The user may wrongly believe that PowerShell activity is covered.

SigDoctor should expose that gap.

Conceptually:

```text
Sigma rule
    ↓
What telemetry does this rule need?
    ↓
What can this host provide?
    ↓
Compare requirements with evidence
    ↓
READY / PARTIAL / BLIND / UNKNOWN
    ↓
Explain why
```

---

# 4. Product wedge

SigDoctor must remain **rule-first**.

Do not drift into building a generic Windows logging auditor or hardening tool.

The distinction is:

```text
Generic logging audit:

Windows host
    ↓
Are my logging settings good?
```

versus:

```text
SigDoctor:

Sigma rule
    ↓
What does THIS rule require?
    ↓
Can THIS host provide it?
    ↓
Why / why not?
```

Existing adjacent tools such as WELA should be treated as competitors / neighboring solutions during feasibility research.

If an existing project already solves the same rule-first workflow better, state that clearly.

---

# 5. Primary users

Primary users include:

- detection engineers
- SOC analysts
- blue teamers
- DFIR / security engineers
- security students and lab users working with Sigma and Windows telemetry

The expected user wants a fast answer to:

> “Can this rule realistically work on this host?”

---

# 6. What SigDoctor is NOT

Do **not** build any of the following in v0.1:

- SIEM
- Sigma query converter
- Sigma execution engine
- detection engine
- EDR
- endpoint agent
- Windows hardening suite
- general compliance scanner
- vulnerability scanner
- threat intelligence platform
- SOC dashboard
- web application
- REST API
- cloud backend
- database
- user accounts
- authentication
- telemetry collector daemon
- remote host scanner
- Active Directory scanner
- AI / LLM feature
- automated remediation
- Group Policy editor
- auto-installation of Sysmon
- auto-download of Sigma rule packs
- Linux support
- macOS support
- dashboards
- MITRE visualization
- billing / subscriptions

If implementation begins drifting into these areas, stop and correct scope.

---

# 7. v0.1 product behavior

The first meaningful UX should be:

```bash
sigdoctor check suspicious_powershell.yml
```

Conceptual output:

```text
SigDoctor

Rule
────────────────────────────────────
Suspicious PowerShell Execution

Platform
Windows

Log source
PowerShell Script Block Logging

MITRE
T1059.001 — PowerShell


Telemetry readiness
────────────────────────────────────

✓ PowerShell Operational channel
  Enabled

✗ Script Block Logging
  Disabled

? Required field: ScriptBlockText
  Cannot verify field availability because
  Script Block Logging is disabled.


Result
────────────────────────────────────

✗ BLIND

This host cannot currently provide the
telemetry required by this Sigma rule.

Missing:
PowerShell Script Block Logging
```

Also support machine-readable output:

```bash
sigdoctor check suspicious_powershell.yml --json
```

Do not implement multiple major commands before `check` is reliable.

---

# 8. Status model

SigDoctor must never give false confidence.

The final rule readiness statuses are:

## READY

SigDoctor has sufficient evidence that the required telemetry capabilities are available.

READY does **not** mean the rule is guaranteed to detect a real attack.

It means the host appears telemetry-ready for the rule within SigDoctor's supported knowledge.

## PARTIAL

Some relevant telemetry exists, but one or more required or important capabilities are missing, incomplete, or unresolved.

## BLIND

At least one capability required by the detection logic is confirmed absent or disabled.

## UNKNOWN

SigDoctor cannot safely determine readiness.

UNKNOWN is a valid and important result.

Examples:

- unsupported logsource
- unsupported field semantics
- insufficient permissions
- probe failure
- no telemetry profile
- ambiguous provider mapping
- insufficient evidence

Never silently convert `UNKNOWN` to `READY`.

---

# 9. Internal evidence states

Keep low-level evidence states separate from final rule readiness.

Potential evidence states include:

- ENABLED
- DISABLED
- PRESENT
- MISSING
- OBSERVED
- NOT_OBSERVED
- UNKNOWN
- ERROR
- UNSUPPORTED

Do not conflate:

- configured
- available
- observed
- effective
- guaranteed

They are different concepts.

---

# 10. Evidence and provenance

Every important conclusion should be explainable.

Example:

```text
Capability:
powershell_script_block_logging

State:
DISABLED

Source:
registry

Observed value:
0
```

Or:

```text
Capability:
powershell_event_4104

State:
OBSERVED

Source:
windows_event_log

Details:
count: 17
latest_timestamp: ...
```

A result such as:

```text
Script Block Logging: Disabled
```

is insufficient unless SigDoctor can explain how it knows.

---

# 11. Architecture responsibility boundaries

Keep responsibilities clear.

```text
Probe
    ↓
observes facts

Evidence model
    ↓
stores structured observations

Evaluator
    ↓
owns final READY / PARTIAL / BLIND / UNKNOWN decision

Renderer
    ↓
presents terminal / JSON output
```

Important rule:

> Only the evaluator may determine the final rule readiness status.

Do not allow:

- probes
- CLI layer
- renderer
- Sigma adapter
- telemetry profile

to independently invent final readiness classifications.

---

# 12. Sigma parsing

Do not manually reimplement Sigma unless technically necessary.

Research the current:

- Sigma specification
- pySigma documentation
- pySigma API
- current supported Python versions
- pySigma license

Prefer pySigma if it provides reliable parsing and validation.

However, isolate it behind a SigDoctor adapter.

Conceptually:

```text
Sigma YAML
    ↓
pySigma
    ↓
SigDoctor Sigma adapter
    ↓
NormalizedRuleRequirements
    ↓
SigDoctor domain logic
```

Do not spread third-party pySigma objects through the entire codebase.

SigDoctor should own its internal contract.

Potential internal model:

```text
NormalizedRuleRequirements

- id
- title
- product
- category
- service
- definition
- detection_fields
- required_fields
- tags
- mitre_techniques
- source_metadata
```

This exact schema is not mandatory.

Use current Sigma semantics to design the correct minimal model.

---

# 13. Sigma semantics to research

Verify current semantics for:

- `logsource.product`
- `logsource.category`
- `logsource.service`
- `logsource.definition`
- `detection`
- `fields`
- field modifiers
- conditions
- tags
- MITRE ATT&CK tags
- explicit event IDs where present
- custom fields
- provider-specific fields
- transformed / normalized backend fields

For every inferred requirement, distinguish:

## DIRECT

The information is explicitly contained in the rule.

## DERIVED

SigDoctor derives the requirement using its telemetry knowledge base.

## UNKNOWN

The requirement cannot be safely determined.

Preserve this provenance when useful.

---

# 14. Telemetry Knowledge Base

This is likely the core domain asset of SigDoctor.

Sigma logsources are abstract.

SigDoctor needs a small, explicit mapping layer from Sigma concepts to concrete Windows telemetry capabilities.

Prefer human-readable, reviewable data files.

Possible structure:

```text
src/sigdoctor/telemetry/profiles/
    windows_process_creation.yml
    windows_powershell.yml
    windows_authentication.yml
```

A telemetry profile should be capable of describing:

- Sigma logsource matching
- required capabilities
- alternative providers
- relevant channels
- relevant event IDs
- audit policy prerequisites
- registry / policy prerequisites
- field capabilities
- conditional capabilities
- references / provenance
- limitations

Avoid large Python `if/elif` hardcoded knowledge trees if data-driven profiles are clearer.

Do not over-engineer a generic plugin system in v0.1.

---

# 15. Initial supported telemetry families

v0.1 supports only **Windows**.

Begin with only three telemetry families.

## A. PowerShell Script Block Logging

Relevant concepts may include:

- `product: windows`
- PowerShell-related category/service semantics
- `Microsoft-Windows-PowerShell/Operational`
- Event ID 4104
- Script Block Logging policy
- ScriptBlockText or equivalent rule fields

This is the **first vertical slice**.

## B. Process Creation

Relevant concepts may include:

- `product: windows`
- `category: process_creation`
- Security Event ID 4688
- Sysmon Event ID 1
- Audit Process Creation
- command-line inclusion
- process image
- parent process
- user
- hashes where provider supports them

Important:

A rule requiring `CommandLine` must not automatically be considered equally supported by telemetry that only provides process image information.

## C. Windows Authentication

Start narrowly.

Potential concepts:

- Security log
- Event ID 4624
- Event ID 4625
- relevant Logon/Logoff audit settings
- fields actually required by representative rules

Do not attempt to support every Windows Security event.

---

# 16. Read-only safety boundary

SigDoctor v0.1 must be **read-only**.

It must never automatically:

- enable logging
- modify registry
- modify Group Policy
- install Sysmon
- change Sysmon configuration
- start/stop services
- enable event channels
- change audit policy
- execute remediation
- download rules
- send telemetry externally

It may explain what appears to be missing.

It must not fix it.

---

# 17. Windows probes

Use small isolated probes.

Potential sources:

- Windows Registry
- Windows Event Log APIs
- `auditpol`
- `wevtutil`
- Sysmon presence / channel
- service status

Do not assume administrator privileges.

Permission failure must produce evidence such as:

```text
UNKNOWN
reason: permission denied
```

Never:

```text
DISABLED
```

unless the disabled state is actually confirmed.

---

# 18. Windows localization and subprocess safety

Windows may be localized.

Avoid relying on English display strings where stable identifiers or APIs are available.

All subprocess execution must:

- avoid `shell=True` unless absolutely unavoidable and justified
- use argument arrays
- have explicit timeouts
- capture stdout
- capture stderr
- handle exit codes
- have bounded parsing
- avoid command construction from Sigma input
- avoid shell injection

Prefer APIs / structured machine-readable mechanisms over fragile text parsing where feasible.

---

# 19. CLI behavior

Use Python.

Keep the CLI dependency small and mature.

Required commands/options initially:

```bash
sigdoctor check <rule.yml>
sigdoctor check <rule.yml> --json
sigdoctor --help
sigdoctor --version
```

Do not add large command trees in v0.1.

Terminal output must:

- remain useful without color
- work in redirected output
- be CI-friendly
- be screenshot-friendly
- avoid unnecessary marketing text

---

# 20. JSON contract

Provide a small stable machine-readable format.

Conceptually:

```json
{
  "schema_version": "1",
  "rule": {},
  "requirements": [],
  "evidence": [],
  "result": {
    "status": "BLIND",
    "reasons": []
  }
}
```

Include `schema_version` from the beginning.

Do not overdesign the schema.

---

# 21. Security requirements

Sigma/YAML input is untrusted local input.

Requirements:

- no `eval`
- no dynamic code execution from YAML
- safe parser behavior
- bounded input file size
- malformed YAML handling
- defensive path handling
- no command execution from rule content
- no network fetch triggered by rule content
- subprocess timeouts
- `shell=False` where possible
- no automatic download of referenced resources
- no secret leakage in logs

SigDoctor should work offline.

---

# 22. Privacy

Default operation is local-only.

Do not add:

- analytics
- cloud error tracking
- remote telemetry
- AI providers
- external event upload

No local event data should leave the machine in v0.1.

---

# 23. Logging

Internal logging must not dump full sensitive Windows events by default.

Support debug/verbose output if useful, but keep default operation minimal.

If event samples are inspected, minimize what is retained and displayed.

---

# 24. Dependencies

Keep the dependency tree small.

For every runtime dependency, document:

- package
- pinned / constrained version strategy
- why it is needed
- license
- distribution implications

Create:

`docs/THIRD_PARTY.md`

Do not add a dependency merely to avoid a few simple lines of standard-library code.

---

# 25. Third-party rules and licensing

Do not bundle the full SigmaHQ rule repository into SigDoctor.

Do not copy large third-party rule packs into the repo.

Use small self-authored rule fixtures for tests where possible.

During research, public rules may be studied subject to their license.

Document relevant license findings.

Do not make legal conclusions beyond what the sources support.

---

# 26. Project license

The repository may currently contain a license chosen at repository creation.

Do not assume that choice is automatically correct for the final dependency setup.

Review:

- pySigma license
- runtime dependencies
- third-party data/content
- any redistribution obligations

Document whether the current project license is compatible with the planned implementation.

Do not change the repository license without explicit approval unless the task specifically authorizes it.

---

# 27. Packaging

Use a normal modern Python package structure.

Expected direction:

- `pyproject.toml`
- `src/` layout if appropriate
- explicit supported Python version
- deterministic development setup
- lock/version strategy
- CLI entry point

Longer-term install UX should aim for:

```bash
pipx install sigdoctor
```

or:

```bash
pip install sigdoctor
```

Do not publish to PyPI in this task.

---

# 28. Suggested repository structure

Use this only as a starting point:

```text
sigdoctor/
├── src/
│   └── sigdoctor/
│       ├── cli.py
│       ├── sigma/
│       │   ├── adapter.py
│       │   ├── models.py
│       │   └── requirements.py
│       ├── telemetry/
│       │   ├── loader.py
│       │   ├── models.py
│       │   └── profiles/
│       │       ├── windows_process_creation.yml
│       │       ├── windows_powershell.yml
│       │       └── windows_authentication.yml
│       ├── windows/
│       │   ├── audit_policy.py
│       │   ├── event_channels.py
│       │   ├── registry.py
│       │   ├── sysmon.py
│       │   └── observations.py
│       ├── evaluation/
│       │   ├── models.py
│       │   └── evaluator.py
│       └── output/
│           ├── terminal.py
│           └── json_output.py
├── tests/
├── examples/
├── docs/
├── pyproject.toml
├── README.md
├── LICENSE
├── SECURITY.md
└── CONTRIBUTING.md
```

Simplify it if a smaller structure is more appropriate.

YAGNI.

---

# 29. Feasibility gate — mandatory before substantial implementation

Before building the full architecture, test whether the core idea is valid.

Research current primary / authoritative sources for:

- Sigma specification
- pySigma
- Microsoft Windows audit policy
- relevant event channels
- PowerShell Script Block Logging
- Event ID 4104
- Event ID 4688
- Event ID 4624 / 4625
- Sysmon Event ID 1
- nearby open-source tools, especially WELA or direct equivalents

Study at least **10 representative Windows Sigma rules**.

Prefer 10–20 if efficient.

Do not bundle those rules into the final product merely because they were used for research.

For each representative rule, answer:

1. What does the rule directly state?
2. What telemetry does it appear to require?
3. What can SigDoctor derive generically?
4. What needs a knowledge profile?
5. What cannot safely be inferred?
6. Which local host evidence could verify the requirement?
7. Is final readiness classification possible without false confidence?

Create:

`docs/FEASIBILITY.md`

---

# 30. FEASIBILITY.md required conclusion

End the feasibility document with exactly one of:

```text
PROCEED
```

```text
PROCEED WITH NARROWER SCOPE
```

```text
DO NOT PROCEED
```

Explain why.

Do not continue substantial implementation if the conclusion is `DO NOT PROCEED`.

---

# 31. Kill criteria

Stop or change direction if research shows:

1. Useful telemetry requirements require rule-by-rule hardcoding.
2. Rule readiness cannot be meaningfully separated from backend/SIEM normalization.
3. An existing open-source tool already solves the same rule-first problem substantially better.
4. SigDoctor would create more false confidence than value.
5. The required knowledge base becomes effectively a new detection framework.
6. The product promise cannot be tested reliably on real Windows hosts.
7. The core workflow is too backend-specific to remain a focused CLI.

Do not continue just because code has already been written.

---

# 32. Architecture document

If feasibility passes, create:

`docs/ARCHITECTURE.md`

Keep it concise.

It should define:

- product boundary
- core domain models
- responsibility boundaries
- evidence model
- evaluator ownership
- telemetry profile model
- supported v0.1 scope
- unsupported scope
- error model
- security boundary
- test strategy

Do not create a long architecture essay merely for documentation volume.

---

# 33. First vertical slice

After feasibility and architecture:

Implement only the first full user journey:

```text
PowerShell Sigma rule
    ↓
parse rule
    ↓
normalize requirements
    ↓
map to Script Block Logging requirements
    ↓
probe host / fake host evidence
    ↓
evaluate
    ↓
READY / PARTIAL / BLIND / UNKNOWN
    ↓
render terminal output
    ↓
render JSON output
```

Do **not** continue directly into every other telemetry family.

---

# 34. PowerShell vertical-slice acceptance scenarios

## Scenario A — BLIND

Rule requires Script Block telemetry.

Host evidence:

- Script Block Logging confirmed disabled.

Expected:

```text
BLIND
```

The result must explain exactly which capability is missing.

## Scenario B — READY

Host evidence:

- Script Block Logging enabled
- PowerShell Operational channel enabled
- Event ID 4104 observed

Expected:

```text
READY
```

Evidence must show why.

## Scenario C — UNKNOWN

Host evidence:

- policy cannot be read
- event channel cannot be verified
- no reliable alternate evidence exists

Expected:

```text
UNKNOWN
```

Never READY.

Never DISABLED without proof.

## Scenario D — malformed rule

Expected:

- understandable parse error
- non-zero tool error code
- no traceback by default

## Scenario E — unsupported Linux rule

Expected:

- clear unsupported / unknown result
- no crash
- no fake Windows interpretation

---

# 35. Process Creation acceptance scenario

Only implement after the PowerShell slice is stable.

Example:

Rule uses:

```text
CommandLine
```

Host:

- Security 4688 available
- Process Creation auditing enabled
- command-line inclusion disabled

SigDoctor must understand that event presence alone does not guarantee required field availability.

Do not classify based only on Event ID 4688 existing.

---

# 36. Authentication scope

Only after prior slice stability.

Keep authentication support narrow.

Do not attempt to model every Windows authentication edge case in v0.1.

---

# 37. Test strategy

Use tests to validate product behavior, not only implementation details.

Required categories:

## Domain / evaluator tests

- READY
- PARTIAL
- BLIND
- UNKNOWN
- UNKNOWN must never become READY through fallback logic

## Sigma contract tests

- valid supported rule
- malformed YAML
- empty file
- missing logsource
- unsupported product
- unknown category
- service
- definition
- tags
- MITRE tags
- field modifiers
- custom fields

## Probe tests

Main tests must not require a real Windows machine.

Abstract / inject:

- subprocess execution
- registry access
- event log access
- event channel state
- Sysmon checks
- permission states

Use fixtures/fakes.

## Windows integration tests

Separate tests may run on actual Windows.

If the current environment is not Windows:

mark them `NOT VERIFIED` or `BLOCKED`.

Do not pretend they were tested.

## End-to-end test

At least one test must exercise:

```text
rule.yml
    → Sigma adapter
    → normalized requirements
    → telemetry profile
    → fake host evidence
    → evaluator
    → final result
    → terminal / JSON rendering
```

This test is more important than arbitrary line-coverage percentage.

---

# 38. Error model

Use structured internal errors.

Potential error codes:

- RULE_PARSE_ERROR
- UNSUPPORTED_PLATFORM
- UNSUPPORTED_LOGSOURCE
- PERMISSION_DENIED
- PROBE_TIMEOUT
- WINDOWS_API_ERROR
- PROFILE_NOT_FOUND
- INVALID_PROFILE
- INTERNAL_ERROR

Human CLI output should explain the problem.

JSON output should expose stable machine-readable codes.

Do not expose huge stack traces by default.

---

# 39. Exit-code policy

Define a minimal exit-code strategy.

At minimum distinguish:

- normal tool completion
- invalid user input
- internal/tool failure

Be cautious about assigning special exit codes to READY/PARTIAL/BLIND in v0.1.

CI-specific status semantics can come later.

Document the decision.

---

# 40. Open-source quality

Once the first slice works, make the repository understandable in seconds.

README should eventually communicate:

```text
Your Sigma rule is valid.
But is your telemetry?

$ sigdoctor check suspicious_powershell.yml

✗ BLIND

Missing:
PowerShell Script Block Logging
```

README should include:

- problem
- solution
- one strong example
- installation
- supported telemetry
- limitations
- how it works
- security model
- contribution basics

Do not spend time on README polish before the core workflow works.

---

# 41. Avoid overclaiming

Never write marketing claims such as:

> SigDoctor tells you whether your rule will detect an attack.

That is too strong.

Prefer:

> SigDoctor checks whether a supported Windows host appears to provide the telemetry required by a Sigma rule.

Clearly distinguish:

- telemetry readiness
- rule correctness
- backend translation correctness
- actual detection effectiveness

SigDoctor only evaluates the first within its supported scope.

---

# 42. Future feature — NOT NOW

Potential future feature:

```bash
sigdoctor coverage ./rules/
```

Conceptual output:

```text
Sigma Doctor — Coverage Report

Rules analyzed: 247

READY        141   57%
PARTIAL       51   21%
BLIND         38   15%
UNKNOWN       17    7%

Biggest telemetry gaps

PowerShell Script Block Logging
Impacts 31 rules

Process Command Line Logging
Impacts 24 rules
```

This may eventually become the most shareable feature.

Do not implement it until single-rule `check` is reliable.

---

# 43. Other future ideas — DO NOT IMPLEMENT

Potential future features:

```text
sigdoctor explain rule.yml
sigdoctor coverage ./rules
sigdoctor export host-profile
sigdoctor check rule.yml --host-profile host.json
sigdoctor compare host1.json host2.json
```

Potential future platforms/backends:

- Linux
- macOS
- Splunk
- Elastic
- Microsoft Sentinel

All are out of scope for the first implementation.

---

# 44. CI and development quality

After the core workflow works, set up minimal CI.

Potential checks:

- formatter
- lint
- type checking
- unit tests
- package build

Use a Windows runner later if it materially verifies real probes.

Keep CI simple.

---

# 45. Code quality principles

Prefer:

- explicit types
- small modules
- pure evaluator logic where possible
- dependency injection for host probes
- human-readable telemetry profiles
- clear internal contracts
- standard-library solutions where adequate

Avoid:

- microservices
- database
- enterprise repository patterns
- DI frameworks
- large plugin architectures
- abstract factories without need
- premature extensibility
- speculative architecture

---

# 46. Git safety

Inspect repository state before changing anything.

Report:

```bash
git status
git branch --show-current
git log --oneline -n 5
```

or the equivalent available through the environment.

Do not:

- force push
- reset user work
- delete unknown work
- rewrite history
- push to remote
- publish a release

without explicit user instruction.

Small local commits are acceptable only if the working environment and task permit them.

Do not push them.

---

# 47. Verification before completion

Before saying something works, run the relevant verification.

Examples:

```bash
pytest
ruff check .
mypy src
python -m sigdoctor --help
sigdoctor check ...
python -m build
```

Use the actual tools chosen by the project.

Report exact commands and outcomes.

Do not say “all good” without evidence.

---

# 48. Current environment caveat

The development environment may not be a real Windows host.

If Windows probes cannot be executed for real:

- design them behind interfaces
- test them with fixtures/fakes
- document what remains unverified
- mark real Windows probe validation as `NOT VERIFIED` or `BLOCKED`

Never fabricate Windows verification.

---

# 49. Required work order

Follow this sequence.

## Phase 0 — Inspect

1. Inspect repository.
2. Read project instructions.
3. Check git status and current files.
4. Do not overwrite user work.

## Phase 1 — Feasibility

1. Research current Sigma spec.
2. Research current pySigma API/license.
3. Research relevant Microsoft telemetry sources.
4. Research nearby tools / direct competitors.
5. Study at least 10 representative Windows Sigma rules.
6. Write `docs/FEASIBILITY.md`.
7. Conclude:
   - PROCEED
   - PROCEED WITH NARROWER SCOPE
   - DO NOT PROCEED

If `DO NOT PROCEED`, stop.

## Phase 2 — Architecture

If feasibility passes:

1. Define core contracts.
2. Define evidence model.
3. Define evaluator ownership.
4. Define telemetry profile schema.
5. Define supported scope.
6. Write `docs/ARCHITECTURE.md`.

## Phase 3 — Tests first

Write failing tests for the PowerShell vertical slice.

## Phase 4 — Implement first slice

Implement only:

```text
Sigma PowerShell rule
→ requirements
→ evidence
→ evaluator
→ terminal
→ JSON
```

## Phase 5 — Verify

Run:

- tests
- lint
- type checks
- CLI smoke tests
- package build if applicable

## Phase 6 — Handoff

Stop and report.

Do not automatically implement Process Creation / Authentication unless explicitly instructed after review.

---

# 50. Definition of Done — first iteration

The first iteration is complete only when:

1. Feasibility has a documented conclusion.
2. Architecture is documented if feasibility passes.
3. One PowerShell telemetry flow works end-to-end.
4. READY/PARTIAL/BLIND/UNKNOWN exist.
5. UNKNOWN cannot become READY through fallback behavior.
6. Evidence accompanies conclusions.
7. CLI output works.
8. JSON output works.
9. Malformed rules fail cleanly.
10. Unsupported platform input fails cleanly.
11. Main workflow has an end-to-end test.
12. Probes are independently testable.
13. No automatic remediation exists.
14. No telemetry leaves the machine.
15. Third-party dependencies/licenses are documented.
16. Verification commands have actually been run.
17. Unverified Windows behavior is labeled honestly.

---

# 51. Final handoff format

When done, report in this exact structure.

## RESULT

What was actually completed.

## FEASIBILITY

One of:

```text
PROCEED
PROCEED WITH NARROWER SCOPE
DO NOT PROCEED
```

with concise reasoning.

## VERIFIED

Only claims backed by actual tests or inspection.

## NOT VERIFIED

Anything not tested or not proven.

## BLOCKED

Anything the environment prevented.

## ARCHITECTURE

Short explanation of the chosen design.

## FILES CHANGED

List important files created/changed.

## TESTS RUN

Exact commands and actual results.

## END-TO-END STATUS

State whether this path works:

```text
rule
→ requirements
→ evidence
→ evaluator
→ CLI
```

## SECURITY

Relevant security decisions and remaining concerns.

## LICENSES

Dependencies, licenses, and any unresolved issues.

## RISKS

Maximum five major risks.

## NEXT RECOMMENDED STEP

Recommend exactly one next step.

Do not continue into the next phase automatically.

---

# 52. Final product rule

Optimize for proving this hypothesis:

> A supported Sigma rule can be mapped to concrete telemetry requirements, compared against trustworthy local Windows evidence, and presented as an honest readiness assessment without giving the user false confidence.

If the evidence supports this:

continue.

If not:

say so clearly and recommend changing or stopping the project.

A small honest tool is better than a large impressive-looking tool that cannot support its core claim.
