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
| A | Machine DWORD 1, channel enabled, fresh PS5.1 action emits plaintext 4104 | READY | Pending disposable run | NOT VERIFIED |
| B | Machine DWORD 0; prior events may still exist | BLIND | Pending disposable run | NOT VERIFIED |
| C | DWORD 1 + enabled channel; no recent event, or independently confirmed event-read denial | PARTIAL | Pending disposable run | NOT VERIFIED |
| D1 | Independently confirmed missing machine policy; enabled channel and recent field | UNKNOWN | UNKNOWN on developer host | VERIFIED for missing-policy gap |
| D2 | Explicit logging policy exists but registry query is denied; channel remains enabled | UNKNOWN | Pending disposable run | NOT VERIFIED |

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

## Current decision

VALIDATION INCOMPLETE — D1 matches, A/B/C/D2 await actual disposable-host evidence.
