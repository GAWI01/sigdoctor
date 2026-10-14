# Controlled Windows validation

Date: 2026-10-14. Product baseline: `d541593d2f8235269523d7f5115d7c9d9dfa6d06`.
This validates the existing Windows PowerShell 5.1 slice, not detection efficacy.

## Inspection and plan

Reviewed windows.py, evaluator.py, the existing Windows integration test,
FEASIBILITY.md and VERIFICATION.md before changing code. The existing integration
test checks a live observation contract but is not an independent known-state
test: it injects the same probe snapshot and conditionally checks READY. The CLI
experiments below are the independent product-hypothesis tests.

Core assumptions under examination:

* 64-bit HKLM DWORD 1/0 is explicit machine logging configuration; absence and
  access denial cannot establish disabled logging. Computer policy takes
  precedence over user policy, but existing PowerShell sessions may cache it.
* The named channel/provider/GUID correspond to Windows PowerShell 5.1, not Core.
* The newest matching event within 24 hours needs a nonempty plaintext field.
  Events do not establish current full-logging policy or detection effectiveness.
* BLIND requires an explicitly disabled core capability. UNKNOWN applies to
  missing core configuration evidence. PARTIAL requires verified enabled policy
  and channel but unresolved recent usable telemetry.

PARTIAL is conceptually legitimate for a newly configured host before telemetry
arrives, or for a caller who can read configuration but not event records. It
describes incomplete observation, not proof of partial capture or disabled logging.
Test the natural no-event state if available; otherwise use a temporary event-read
denial in a disposable runner while independently confirming policy/channel reads.
If that setup also prevents configuration reads, it does not qualify as PARTIAL.

## Environment and safety boundary

Developer host: Windows 11 Home 25H2, build 26200.9457, x64;
Windows PowerShell 5.1.26100.9444 Desktop, 64-bit. Process is not elevated.
WindowsSandbox.exe, standard VirtualBox/VMware binaries and Hyper-V tooling were
not available. Home does not support Windows Sandbox. No developer-host logging,
registry, ACL, channel or unrelated security settings were modified.

Use GitHub's `windows-2025` hosted runner as the disposable controlled environment.
Its VM is dedicated to the job and discarded afterward. The separate validation
harness must refuse local execution before any configuration access/mutation;
it requires an explicit argument plus GitHub-hosted Windows environment guards.
It lives outside src and the runtime wheel; the source archive includes it only
to reproduce the safety test. It is not a SigDoctor command/remediation feature.
No events are cleared, no security service is disabled, and no real event
payload is uploaded. Only controlled-run metadata and SigDoctor's safe JSON survive.

Within that VM, save the original DWORD presence/type/value, created-key ancestry,
channel enablement and ACLs. Use try/finally to restore ACLs before policy/channel
configuration, verify rollback, then discard the VM. Record rollback failure as
a failed validation run; never silently claim a clean restoration.

## Scenario matrix

| Scenario | Known state | Expected | Actual | Verified |
|---|---|---|---|---|
| A | Machine DWORD 1, channel enabled, fresh PS5.1 action emits plaintext 4104 | READY | READY | VERIFIED on disposable VM |
| B | Machine DWORD 0; prior plaintext events retained | BLIND | BLIND | VERIFIED on disposable VM |
| C | DWORD 1 + enabled channel; no recent 4104 before first test action | PARTIAL | PARTIAL | VERIFIED on disposable VM |
| D1 | Missing machine policy; enabled channel and recent field | UNKNOWN | UNKNOWN | VERIFIED on developer host and disposable VM |
| D2 | Existing DWORD 1, but Registry QueryValues denied; channel remains enabled | UNKNOWN | UNKNOWN | VERIFIED on disposable VM |

Run C before A when testing natural absence; use fresh PowerShell processes after
policy transitions. Execute the actual installed `sigdoctor check` CLI in every
case. The existing self-authored example is the fixture; its SHA-256 is
`7946fbb5c5d05b3c3f3a2263cdf3b21017b19d7c29c476ec24febdb3b0f8ab9c`.

## Executed D1: developer-host evidence gap

Independent .NET Registry64 read-only APIs confirmed MISSING_KEY, before and after
the product CLI. Independent .NET EventLogConfiguration confirmed channel enabled.
`reg.exe query ... /reg:64` separately returned key/value-not-found, not access
denied. Windows/PowerShell versions are listed above.

Command: `.\.venv\Scripts\sigdoctor.exe check examples/powershell_script.yml --json`.
Expected/actual: UNKNOWN / UNKNOWN, exit 0. Probe evidence: policy UNKNOWN,
channel ENABLED, event_4104 OBSERVED, plaintext field OBSERVED. No deliberate test
marker or logging change was needed; existing and inspection activity may produce
events. Raw scripts, usernames, paths from events and event XML were not retained.
The [sanitized evidence](validation/windows_unknown_2026-10-14.json) records the
independent before/after oracle and real CLI response.

Limit: this proves a naturally present missing-policy gap; it does not prove the
denied-permission path or the enabled/disabled states.

## Executed controlled experiment

[GitHub Actions run 38596950991](https://github.com/GAWI01/sigdoctor/actions/runs/38596950991)
passed on a fresh Windows Server 2025 Datacenter x64 VM, Windows version
10.0.26100, build **26100.33438**, Windows PowerShell **5.1.26100.33438** Desktop,
64-bit. Product/test commit: `432aeba43de12a570ea836479fa1171a85602429`.
Experiment ran from 2026-10-14 16:19:24 to 16:19:33 UTC. The normal
[Windows/Linux checks](https://github.com/GAWI01/sigdoctor/actions/runs/38596950906)
also passed. This is hosted Server evidence, not a claim that all Windows
editions/builds or non-administrative caller contexts have been validated.

All scenarios called `python -m sigdoctor check examples/powershell_script.yml
--json` as an external process using the installed package, real pySigma adapter,
profile and native probes. The fixture was unchanged. Independent setup oracles
used native `reg.exe` readback, channel XML, a separate recent-event read and a
Get-WinEvent marker check. No evaluator/probe was mocked in the experiment.
The [complete metadata-only report](validation/windows_hosted_2026-10-14.json)
contains each known state, CLI assessment and rollback result.

* **C ran first.** Original logging policy was absent. After native DWORD 1 and
  channel enablement, a native event query returned zero recent 4104 records.
  No logs were cleared and no clock was changed. CLI evidence was policy ENABLED,
  channel ENABLED, event NOT_OBSERVED, field UNKNOWN; result PARTIAL. This is a
  legitimate newly enabled configuration before its first observed event. The
  planned alternative event-read-denial branch was not needed or executed.
* **A:** a fresh 64-bit Windows PowerShell process executed Write-Output with a
  unique benign marker. A separate Get-WinEvent query confirmed one matching
  4104; the oracle script read the marker from its environment rather than
  embedding it, so logging the oracle could not satisfy this check. The newest
  event had usable plaintext. CLI evidence was ENABLED/ENABLED/OBSERVED/OBSERVED;
  result READY. Marker text and raw event contents were not retained.
* **B:** native DWORD 0 was confirmed while the channel remained enabled and A's
  plaintext events still existed. CLI policy was DISABLED despite OBSERVED event
  and field evidence; result BLIND. This demonstrates that retained events do not
  override confirmed disabled full-logging configuration.
* **D1:** only the machine policy value was removed and absence independently
  confirmed. The enabled channel and recent plaintext remained observable; CLI
  result UNKNOWN, policy UNKNOWN. Absence was not reported as disabled.
* **D2:** DWORD 1 was confirmed, then the current disposable-runner account was
  temporarily denied Registry QueryValues on the specific policy key. Native
  Win32 read returned access-denied code 5; channel/event reads still succeeded.
  CLI policy UNKNOWN with PERMISSION_DENIED, result UNKNOWN. It was never BLIND
  or DISABLED merely because the query was denied.

No classification discrepancy occurred. The evaluator/telemetry interpretation
needed no change. The only product-code correction was the explicit non-Windows
registry boundary guard needed by the existing cross-platform type check.

### Rollback evidence and limitations

The runner restored and read back the registry DACL, original policy absence,
original enabled channel and original channel ACL, then removed two newly created
empty policy keys. The report records rollback verified=true. The VM was discarded
at job completion. No developer-machine settings were changed. The review's
registry-ACL readback gap was corrected before the hosted experiment.

Not verified here: protected/encrypted-event scenarios; the alternate event-read
permission path for C; policy propagation races/cached old sessions; every Windows
version; uniform behavior across real standard-user accounts; tamper resistance,
forwarding, normalization, fragment reassembly or detection effectiveness. The
permission experiment uses a real temporary deny ACL on the hosted administrator
account, not a separate non-administrator deployment. No upstream rule engine was
executed and the benign marker is not an attack simulation.

## Manual alternative — approval required for developer-host changes

Use an isolated Windows VM and take a checkpoint before setup. Install the
existing package and copy the example, then record OS/PS versions, machine DWORD
presence/type/value and channel configuration before changing anything. Run these
native commands from the VM's elevated **cmd.exe**, with the repo as CWD:

```bat
reg query "HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" /v EnableScriptBlockLogging /reg:64
wevtutil gl Microsoft-Windows-PowerShell/Operational /f:xml
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" /v EnableScriptBlockLogging /t REG_DWORD /d 1 /f /reg:64
wevtutil sl Microsoft-Windows-PowerShell/Operational /e:true
python -c "from validation.controlled_windows import read_recent_event; print(read_recent_event())"
sigdoctor check examples\powershell_script.yml --json
```

The read-only helper retains only count/provider/time/field-presence metadata.
Do not save/display an event payload on a normal host. For C, use a
VM with genuinely no recent 4104 before invoking any new PowerShell session;
do not clear logs or alter the clock to force the precondition. If recent events
exist, leave C unexecuted or use the disposable-run event-permission procedure.

For A, start a fresh 64-bit Windows PowerShell process after DWORD 1 is confirmed:

```bat
%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -Command "Write-Output 'SigDoctorValidationMarker'"
sigdoctor check examples\powershell_script.yml --json
```

Independently verify a new 4104 contains that benign marker (retain only boolean,
provider, event ID and timestamp). For B, explicitly set DWORD 0 and rerun CLI:

```bat
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" /v EnableScriptBlockLogging /t REG_DWORD /d 0 /f /reg:64
sigdoctor check examples\powershell_script.yml --json
```

For D1 in the disposable VM, remove only the named value and verify absence:

```bat
reg delete "HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" /v EnableScriptBlockLogging /f /reg:64
sigdoctor check examples\powershell_script.yml --json
```

Rollback: restore the VM checkpoint (includes registry, ACLs, channel state and
history), or close the Sandbox instance on a supported edition. If a separately
approved normal-host experiment is used, restore the original typed value (or
delete only the experiment's value if originally absent), original channel
enablement/ACL, and only newly created empty keys. Verify the saved baseline;
never recursively delete unknown values or clear event history. Changes in that
normal-host fallback require explicit approval under step 3 of the user's request.
No such approval has been assumed or used.

## Sources

* [Microsoft Windows PowerShell logging](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_logging?view=powershell-5.1)
* [Machine/user policy mapping and precedence](https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-windowspowershell)
* [wevtutil XML queries and channel settings](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/wevtutil)
* [Windows Sandbox requirements](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/)
* [Disposable GitHub-hosted Windows VMs](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

## Decision

The known real-host states support the narrow status semantics, including a
natural PARTIAL state and genuine access-denied UNKNOWN. This strengthens the
existing PowerShell hypothesis sufficiently for review within the stated scope.
It does not justify additional telemetry families or detection-effectiveness
claims. No merge, publication, deployment or release is included.

VALIDATED — READY FOR REVIEW
