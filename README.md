# SigDoctor

Your Sigma rule is valid. But is your telemetry?

SigDoctor checks whether a supported Windows host appears to provide the
telemetry required by a Sigma rule. This first prototype assesses **Windows
PowerShell 5.1 Script Block Logging only**. It does not run detections or change
Windows settings.

```powershell
sigdoctor check examples/powershell_script.yml
sigdoctor check examples/powershell_script.yml --json
```

Example result from a **controlled disabled-policy test fixture**:

```text
SigDoctor
Rule: Example Script Block Marker
Scope: Windows PowerShell 5.1, machine policy, native plaintext 4104 ScriptBlockText only

Result: BLIND
  CAPABILITY_DISABLED: Required capability script_block_logging is explicitly disabled for this provider.
```

Actual output also includes timestamped evidence, sources and limitations.
On the development host, the actual result was **UNKNOWN** despite a recent
4104 event: the machine policy could not be established. That is intentional.

## Install from this checkout

Python 3.11 or newer, below 4. Tested locally with Python 3.13 on Windows x64.
There is no published SigDoctor package from this iteration.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pip install --no-deps .
.\.venv\Scripts\sigdoctor --help
.\.venv\Scripts\sigdoctor check examples/powershell_script.yml
```

Alternatively, `pipx install .` installs from the checkout. Installation needs
access to dependencies; **checks run locally without network requests**.
Administrator privileges are not required. An unreadable source becomes
unresolved evidence rather than a claim that logging is disabled.

## Supported input and results

* One UTF-8 rule using the default `sigma` taxonomy (absent or explicit), with
  `product: windows`, `category: ps_script`, and native
  `ScriptBlockText` detection predicates. `service: powershell` is accepted only
  with an explicit positive conjunctive `EventID: 4104` and no conflicting category.
* Native string predicates, `contains`, `startswith`, `endswith`, `all`, and
  Boolean combinations on ScriptBlockText. Top-level `fields` are display hints.
* READY: machine logging and channel enabled, recent plaintext field observed.
* PARTIAL: configuration verified, usable recent telemetry still unresolved.
* BLIND: a required comprehensive logging capability is explicitly disabled.
* UNKNOWN: insufficient core evidence, unsupported source/semantics or platform.

Unsupported transformations are rejected before expansion, including in unused
selectors; the UNKNOWN result explicitly says full Sigma validation was not
completed. Unknown modifiers and malformed rules are input errors.
Non-default taxonomies return UNKNOWN before host probing; their field names,
values and logsource names cannot be assumed to describe native Windows telemetry.

READY is **not** proof of rule correctness, complete capture, successful forwarding,
correct SIEM normalization or detection effectiveness. BLIND is scoped to Windows
PowerShell 5.1; it is not a statement about PowerShell 7 or other telemetry providers.

## How it works

Bounded YAML → pySigma adapter → one reviewed telemetry profile → read-only
registry/channel/event observations → one evaluator → terminal or JSON.

The probe reads the 64-bit HKLM Script Block Logging policy and uses fixed
`wevtutil` XML queries. It examines only the newest 4104 within 24 hours, discards
event contents, and emits field-presence metadata. No recent event is not proof
of disabled logging. No registry value is not proof of disabled logging either.

Checks are snapshots. Existing sessions may cache policies; a recent event can
predate a configuration change. Fragment reassembly, protected-event decryption,
HKCU-only policies, PowerShell 7, process creation, authentication, custom fields,
SIEM backends and remote hosts are outside this iteration.

Input is limited to 256 KiB with nesting/node/condition/modifier limits. UNC and
device paths, mapped network drives, symlinks and reparse points are rejected.
Use an ordinary local file. No rule references are fetched.

JSON uses `schema_version: "1"`; successful assessments include `rule`,
`requirements`, `evidence`, `scope`, `limitations`, and `result`. Tool/input errors
include `error.code` and `error.message`. Exit codes: **0** completed assessment
(including UNKNOWN/BLIND), **2** invalid input/usage, **1** internal/tool failure.
Automation must inspect `result.status`, not assume exit 0 means READY.

## Development and verification

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.lock
.\.venv\Scripts\python -m pip install --no-deps -e .
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m mypy src
.\.venv\Scripts\python -m build
```

The default suite uses fake Windows boundaries and runs without Windows access.
Opt into the separate read-only host test with `$env:SIGDOCTOR_WINDOWS_TESTS='1'`
and `python -m pytest -q -m windows_integration`. It checks this host's observation
contract; it does not create controlled enabled/disabled hosts or change policies.

See [feasibility](docs/FEASIBILITY.md), [architecture](docs/ARCHITECTURE.md),
[verification](docs/VERIFICATION.md), [security](SECURITY.md),
[contributing](CONTRIBUTING.md), and [dependency notices](docs/THIRD_PARTY.md).
Project code remains MIT; dependencies retain their own licenses.
