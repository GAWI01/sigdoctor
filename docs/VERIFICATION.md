# Verification record — 2026-10-14

Original pre-push verification at base commit `57e21c6`, on
`codex/powershell-slice`. That first iteration was subsequently committed and
pushed as `d541593d2f8235269523d7f5115d7c9d9dfa6d06`. No release, deployment or
publication occurred. Existing MIT LICENSE unchanged.

Environment: Windows x64, Python 3.13. Commands below run from the repository
unless noted. No Windows logging or security policy was modified.

## Commands and outcomes

| Command | Actual result |
|---|---|
| `.\.venv\Scripts\python -m pytest -q` | 92 passed, 1 opt-in Windows test skipped. |
| `$env:SIGDOCTOR_WINDOWS_TESTS='1'; .\.venv\Scripts\python -m pytest -q -m windows_integration` | 1 passed; other tests deselected. Environment variable removed afterward. |
| `.\.venv\Scripts\python -m ruff check .` | All checks passed. |
| `.\.venv\Scripts\python -m ruff format --check .` | All checked Python files formatted. |
| `.\.venv\Scripts\python -m mypy src` | No issues in 10 source files. |
| `.\.venv\Scripts\python -m sigdoctor --help` | Exit 0; one command (`check`) plus help/version. |
| `.\.venv\Scripts\sigdoctor --version` | Exit 0; sigdoctor 0.1.0. |
| `.\.venv\Scripts\sigdoctor check examples/powershell_script.yml` | Exit 0; timestamped terminal assessment UNKNOWN. |
| `.\.venv\Scripts\python -m sigdoctor check examples/powershell_script.yml --json` | Exit 0; valid schema-version-1 JSON, UNKNOWN. |
| `.\.venv\Scripts\python -m build` | Built sdist and wheel successfully. |
| `.\.venv\Scripts\python -m pip check` | No broken requirements. |
| `.\.venv\Scripts\python -m pip install -r requirements-dev.lock` | Locked development environment installed/requirements satisfied. |
| `python -m venv .venv-package-check` | Created clean package-verification environment. |
| `.\.venv-package-check\Scripts\python -m pip install -r requirements.lock` | Exact runtime dependencies installed successfully. |
| `.\.venv-package-check\Scripts\python -m pip install --no-deps dist/sigdoctor-0.1.0-py3-none-any.whl` | Wheel installed successfully. |
| `.\.venv-package-check\Scripts\python -m pip check` | No broken requirements. |
| `git diff --check` | No whitespace errors. Git reported its normal LF/CRLF conversion warning. |

Wheel entrypoint smoke checks were executed from the system temporary directory,
using the absolute `.venv-package-check\Scripts\sigdoctor.exe` path. Import was
confirmed from its `Lib/site-packages/sigdoctor`, not `src`. Exact invocations:

* `sigdoctor.exe --help` and `sigdoctor.exe --version`: exit 0.
* `sigdoctor.exe check <absolute examples/powershell_script.yml> --json`: exit 0,
  schema_version 1, UNKNOWN; evidence matches the real-host observations below.
* `sigdoctor.exe check <temporary malformed.yml> --json`: exit 2,
  RULE_PARSE_ERROR; no traceback or raw YAML.
* `sigdoctor.exe check <temporary linux.yml> --json`: exit 0, UNKNOWN.

Those temporary fixtures were removed. No event content was retained. Build
artifacts are local in dist; no package was uploaded. The wheel contains only
SigDoctor code, profile, metadata and project license, not upstream rules or
dependency code.

## Real Windows evidence

Observed during this session:

| Capability | Observation |
|---|---|
| HKLM 64-bit machine Script Block Logging policy | UNKNOWN, value not established |
| Microsoft-Windows-PowerShell/Operational | ENABLED |
| Latest 4104 within 24 hours | OBSERVED |
| Nonempty plaintext ScriptBlockText in sample | OBSERVED |
| Final assessment | UNKNOWN |

This validates the real registry/channel/event path and the refusal to substitute
historical event evidence for missing policy. It does not validate every host
configuration, Windows version or user privilege state.

## Product and safety scenarios

Self-authored fixtures test READY/PARTIAL/BLIND/UNKNOWN through adapter, profile,
fake host evidence, evaluator and both renderers. Coverage includes malformed
YAML, missing logsource, unknown categories/fields/modifiers, Linux input, tags,
definition, active versus unused selectors, display-field separation, Boolean
conditions, explicit/negated/alternative event IDs, null/field-reference semantics,
duplicate observations, missing policy, permissions, timeouts, native failures,
XML bounds, stale/future/foreign/encrypted/empty-field events and safe command
arguments. CLI tests check status-independent completion exits and structured
input/internal errors.

An independent review reproduced three defects: multi-value modifier provenance
could be lost; pySigma could eagerly expand unsupported modifiers before checks;
UNC resolution preceded rejection. Regression tests failed before correction and
passed after it. Reviewer rechecked the fixes and ran 62 focused tests with no
material regression. Follow-up path tests cover mapped drives and reparse points.

The six PowerShell rules listed in FEASIBILITY.md were fetched at the pinned
SigmaHQ commit into a temporary directory during research, passed through the
actual adapter, and all produced the single ScriptBlockText requirement with no
support issues. This checks generic mapping, not host readiness or attack
detection. Research files were removed and are not bundled.

## Environment issues and unverified areas

The compiled mypy 2.4.0 wheel initially failed to import because Windows
application control blocked its DLL. Installing the official pure-Python wheel
resolved this; type checks passed. No security setting was disabled. The exact
pure wheel URL/hash is in the development lock.

An oversized pytest parameter initially exceeded Windows' environment-variable
length when used as its test name. Short explicit IDs fixed the harness; the
application's oversized-input test then ran and passed.

NOT VERIFIED: controlled real-host READY/BLIND/PARTIAL/permission-denied/encrypted
logging and policy-transition experiments; other Windows/Python versions; Linux
CI execution; actual detection effectiveness; user demand; future bundled-binary
license obligations. Main tests use fakes for these host states. The CI workflow
had not run when the original record was written. Subsequent CI and controlled
validation are recorded below.

## Controlled Windows validation follow-up

See WINDOWS_VALIDATION.md and its metadata-only evidence. An independent .NET
Registry64 oracle confirmed the missing machine-policy key before and after the
actual CLI check on Windows 11 Home 25H2 build 26200.9457 / Windows PowerShell
5.1.26100.9444 x64. Expected UNKNOWN matched actual UNKNOWN. A/B/C and denied-policy
states are tested separately on a disposable hosted Windows runner; do not infer
their completion from the local result or fixture suite.

The [initial GitHub CI run](https://github.com/GAWI01/sigdoctor/actions/runs/38592912614)
failed Linux mypy with six Windows-registry attribute errors. Root cause:
read_machine_policy imported/used winreg without an explicit platform guard, so
the Linux type environment could not validate it. Added an early non-Windows
rejection and regression test. The test failed before the fix and passed after
it; `python -m mypy --platform linux src` then passed. Runtime unsupported-platform
handling remains conservative. The original Windows job's test/lint/type/build
steps passed, although its overall result was cancelled by the matrix failure.

The lab harness's normal-host refusal is tested before native access. It is
outside the runtime wheel. Controlled changes occur only in the authorized
disposable GitHub-hosted Windows VM, with explicit rollback checks. No developer
machine policy or ACL was changed.

Local follow-up commands (before disposable run):

| Command | Actual result |
|---|---|
| `.\.venv\Scripts\python -m pytest -q` | 95 passed, 1 opt-in test skipped |
| `$env:SIGDOCTOR_WINDOWS_TESTS='1'; .\.venv\Scripts\python -m pytest -q -m windows_integration` | 1 passed, 95 deselected; environment restored |
| `.\.venv\Scripts\python -m ruff check .` | Passed |
| `.\.venv\Scripts\python -m ruff format --check .` | Passed |
| `.\.venv\Scripts\python -m mypy src` | Passed, 10 source files |
| `.\.venv\Scripts\python -m mypy --platform linux src` | Passed, 10 source files; previously reproduced six errors |
| `.\.venv\Scripts\python -m build` | Built wheel and sdist |
| `.\.venv-package-check\Scripts\python -m pip install --force-reinstall --no-deps dist/sigdoctor-0.1.0-py3-none-any.whl` | Installed rebuilt wheel |
| `.\.venv-package-check\Scripts\sigdoctor --version` | 0.1.0, exit 0 |
| `.\.venv-package-check\Scripts\sigdoctor check examples/powershell_script.yml --json` | UNKNOWN, schema 1, exit 0 |

Wheel inspection confirmed the controlled-mutation harness is absent from the
runtime wheel; it is included only in the source archive to reproduce its tests.
Independent harness review identified an unverified registry-ACL restoration
claim; restoration now requires descriptor readback equality. Its regression
test failed before the helper was added and passed after correction. These local
checks do not yet establish the controlled A/B/C/D2 results; those require the
actual separate disposable-runner experiment.
