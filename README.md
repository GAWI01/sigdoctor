# SigDoctor

**Your Sigma rule is valid. But is your telemetry?**

[![Checks](https://github.com/GAWI01/sigdoctor/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/GAWI01/sigdoctor/actions/workflows/ci.yml)

A valid detection rule still needs the right logs. SigDoctor is a read-only CLI
that checks local Windows configuration and event evidence against the telemetry
requirements of a supported Sigma rule.

**Current scope: a prototype for Windows PowerShell 5.1 Script Block Logging only.**
It checks telemetry readiness; it does not run detections or change host settings.

[Try it](#try-it) · [Results](#results) · [Supported scope](#supported-scope) · [Validation](#validation)

## Example

Check your own supported rule after installation:

```powershell
sigdoctor check suspicious_powershell.yml
sigdoctor check suspicious_powershell.yml --json
```

Example output excerpt when machine Script Block Logging is explicitly disabled:

```text
SigDoctor
Rule: Example Script Block Marker

Result: BLIND
  CAPABILITY_DISABLED: Required capability script_block_logging is explicitly disabled for this provider.
```

The excerpt uses the bundled example rule and a controlled disabled-policy test
fixture. Full output includes the assessment scope, timestamped evidence, sources,
and limitations. Your host may return a different result.

## Try it

You need **Windows**, **Python 3.11 or newer (below 4)**, and Git for the clone step.
Install from source; no SigDoctor package or release has been published.

Run these commands in PowerShell:

```powershell
git clone https://github.com/GAWI01/sigdoctor.git
cd sigdoctor
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pip install --no-deps .
.\.venv\Scripts\sigdoctor check examples/powershell_script.yml
```

The bundled rule is a self-authored telemetry example, not a production detection.
Use `.\.venv\Scripts\sigdoctor --help` for CLI help, or add `--json` to a check.
The explicit executable path above works without activating the virtual environment.
Alternatively, `pipx install .` installs from an existing checkout.

Installation downloads dependencies. **Checks run locally without network requests.**
You can run without administrator privileges; unreadable evidence remains unresolved.
On non-Windows hosts, checks return UNKNOWN rather than attempting Windows probes.

## Results

Every classification applies only to the supported Windows PowerShell 5.1 scope.

| Result | What the evidence establishes |
|---|---|
| **READY** | Machine Script Block Logging and the event channel are enabled, and a recent 4104 event contains usable plaintext `ScriptBlockText`. |
| **PARTIAL** | Logging and the channel are verified as enabled, but recent usable script telemetry cannot be confirmed. This does not measure partial capture. |
| **BLIND** | A required logging capability is explicitly disabled: the machine policy or the event channel. Missing events alone never establish BLIND. |
| **UNKNOWN** | Core configuration evidence is missing or inaccessible, or the rule, semantics, or platform is unsupported. |

**READY does not prove that an attack will be detected.** It does not establish
rule correctness, complete capture, forwarding, SIEM normalization, or detection
effectiveness.

SigDoctor keeps uncertainty visible:

- A missing policy value or permission failure is not treated as disabled logging.
- No recent event does not prove logging is disabled.
- Historical events cannot override missing or explicitly disabled current policy.
- Unsupported rule semantics cannot become READY through a fallback.

For example, the development host returned UNKNOWN despite a recent plaintext
4104 event because its machine logging policy could not be established.

## Supported scope

| Supported today | Boundary |
|---|---|
| One local Sigma rule per check | Default `sigma` taxonomy and supported native `ScriptBlockText` predicates |
| Windows PowerShell 5.1 | Machine Script Block Logging policy and `Microsoft-Windows-PowerShell/Operational` |
| Native Event ID 4104 evidence | Newest matching event within 24 hours; usable plaintext `ScriptBlockText` |
| Terminal and JSON output | Reasons, evidence sources, timestamps, scope, and limitations |

**Outside the current scope:** PowerShell 7, process creation, authentication,
bulk coverage, remote hosts, custom or normalized fields, SIEM integration,
remediation, and a web UI. User-only policy, encrypted-content decryption, and
script-fragment reassembly are not assessed.

<details>
<summary>Exact supported Sigma input</summary>

- One UTF-8 rule with `product: windows`, `category: ps_script`, no service, and
  native `ScriptBlockText` detection predicates.
- `service: powershell` is accepted only with an explicit positive conjunctive
  `EventID: 4104` and no conflicting category.
- Native string predicates and wildcards, `contains`, `startswith`, `endswith`,
  `all`, and Boolean combinations on `ScriptBlockText` are supported. Top-level
  `fields` are display hints, not detection requirements.
- Non-default taxonomies and unsupported fields or semantics return UNKNOWN.
  Unsupported transformations are rejected before expansion, including in unused
  selectors; such a result does not certify that full Sigma validation completed.
  Unknown modifiers and malformed rules are input errors.

See [architecture](docs/ARCHITECTURE.md) for the full interpretation contract.

</details>

## How it works

SigDoctor reads the rule's active detection condition through pySigma, maps its
requirements to one reviewed telemetry profile, then compares them with local
policy, channel, and event observations. One evaluator produces the result for
both output formats.

Checks are snapshots: running sessions may cache earlier policy, and recent
events can predate configuration changes. A compromised host can also falsify
observations. SigDoctor is not an attestation or anti-tamper tool.

<details>
<summary>Probe, input safety, and automation details</summary>

The probe reads the 64-bit HKLM machine policy and uses fixed `wevtutil` XML
queries. It examines only the newest matching 4104 within 24 hours. Event contents
are discarded after parsing; output contains field-presence metadata, not script
text or raw event payloads. Rule metadata remains part of the report.

Input is limited to 256 KiB with nesting, node, condition, and modifier limits.
UNC/device paths, mapped network drives, symlinks, and reparse points are rejected.
Use an ordinary local file. No rule values are executed or references fetched.

JSON uses `schema_version: "1"`. Assessments include `rule`, `requirements`,
`evidence`, `scope`, `limitations`, and `result`. Tool/input errors include
`error.code` and `error.message`.

| Exit code | Meaning |
|---|---|
| `0` | Assessment completed, including BLIND and UNKNOWN |
| `2` | Invalid input or CLI usage |
| `1` | Internal or tool failure |

Automation must inspect **`result.status`**; exit 0 does not mean READY.
See [SECURITY.md](SECURITY.md) for the trust boundary and reporting guidance.

</details>

## Validation

Controlled CLI tests on a disposable Windows Server 2025 host matched all five
known states: READY with fresh plaintext telemetry, BLIND with disabled policy,
PARTIAL before a recent event existed, and UNKNOWN for both missing policy and
registry permission denial. Rollback was verified. A read-only Windows 11 check
also confirmed UNKNOWN for missing machine policy.

These are specific host experiments, not proof of every Windows version,
permission context, or detection outcome. See the
[Windows validation matrix and evidence](docs/WINDOWS_VALIDATION.md) and
[verification record](docs/VERIFICATION.md) for configurations, results, and limits.
Regular CI checks tests, lint, formatting, types, and packaging on Linux and Windows;
passing Linux CI does not make Linux telemetry supported.

## Documentation

| Document | What it covers |
|---|---|
| [Feasibility](docs/FEASIBILITY.md) | Product hypothesis, existing tools, and why the scope is narrow |
| [Architecture](docs/ARCHITECTURE.md) | Rule interpretation, evidence ownership, and status decisions |
| [Windows validation](docs/WINDOWS_VALIDATION.md) | Controlled host scenarios, rollback, evidence, and untested states |
| [Verification](docs/VERIFICATION.md) | Test commands, observed results, and review findings |
| [Security](SECURITY.md) | Trust boundary, sensitive data, and vulnerability reporting |
| [Contributing](CONTRIBUTING.md) | Development expectations and scope decisions |
| [Dependency notices](docs/THIRD_PARTY.md) | Dependency licenses and distribution boundaries |

## Development

From the checkout and virtual environment created above:

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.lock
.\.venv\Scripts\python -m pip install --no-deps -e .
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m mypy src
.\.venv\Scripts\python -m build
```

The default tests use fake Windows boundaries and run without Windows access.
The separate read-only integration test requires Windows and an explicit opt-in:

```powershell
$env:SIGDOCTOR_WINDOWS_TESTS = '1'
try {
    .\.venv\Scripts\python -m pytest -q -m windows_integration
} finally {
    Remove-Item Env:SIGDOCTOR_WINDOWS_TESTS
}
```

That test checks live observations; it does not create controlled host states or
change logging policy. Controlled-state testing belongs in a disposable environment.
Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing broader telemetry support.

## License

SigDoctor's own code is [MIT licensed](LICENSE). Dependencies retain their own
licenses, including pySigma's LGPL-2.1-only license; see
[dependency notices](docs/THIRD_PARTY.md).
