"""Lab-only state validation, outside the package. Refuses normal-host execution."""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

CHANNEL = "Microsoft-Windows-PowerShell/Operational"
KEY = r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging"
VALUE = "EnableScriptBlockLogging"
QUERY = "*[System[(EventID=4104) and TimeCreated[timediff(@SystemTime) <= 86400000]]]"
ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def hosted_runner_guard():
    require(
        sys.platform == "win32"
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
        and os.environ.get("RUNNER_OS") == "Windows"
        and os.environ.get("GITHUB_REPOSITORY") == "GAWI01/sigdoctor"
        and os.environ.get("GITHUB_REF") == "refs/heads/codex/powershell-slice",
        "REFUSED: controlled mutations require the authorized disposable GitHub-hosted Windows runner.",
    )


def native(executable, *args, allow_failure=False):
    binary = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / executable
    result = subprocess.run(  # noqa: S603 -- fixed lab commands, guarded hosted runner
        [str(binary), *args],
        capture_output=True,
        timeout=30,
        check=False,
    )
    require(len(result.stdout) <= 2 * 1024 * 1024, "Lab output exceeded bound")
    if not allow_failure:
        require(
            result.returncode == 0,
            f"Lab command {executable} failed with code {result.returncode}; raw output suppressed",
        )
    return result


def ps(script):
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return (
        native(
            r"WindowsPowerShell\v1.0\powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded,
        )
        .stdout.decode("utf-8-sig")
        .strip()
    )


def quote_ps(value):
    return "'" + value.replace("'", "''") + "'"


def read_policy():
    """Native CLI oracle; distinguish absence/denial with independent narrow Win32 read."""
    result = native("reg.exe", "query", "HKLM\\" + KEY, "/v", VALUE, "/reg:64", allow_failure=True)
    if result.returncode == 0:
        text = result.stdout.decode("utf-8", errors="replace")
        match = re.search(r"EnableScriptBlockLogging\s+REG_DWORD\s+0x([0-9a-fA-F]+)", text)
        require(match is not None, "Unsupported original policy type; will not overwrite it")
        return {
            "state": "PRESENT",
            "kind": "REG_DWORD",
            "value": int(match.group(1), 16),
            "native_exit": 0,
        }
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, KEY, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_WOW64_64KEY
        ) as key:
            winreg.QueryValueEx(key, VALUE)
    except FileNotFoundError:
        return {"state": "MISSING", "kind": None, "value": None, "native_exit": result.returncode}
    except PermissionError as exc:
        return {
            "state": "PERMISSION_DENIED",
            "native_error": exc.winerror,
            "native_exit": result.returncode,
        }
    raise RuntimeError("Native and registry policy oracles disagree")


def channel_xml():
    raw = native("wevtutil.exe", "gl", CHANNEL, "/f:xml", "/uni:true").stdout
    return ET.fromstring(raw.decode("utf-16"))  # noqa: S314 -- bounded fixed local XML


def read_channel():
    root = channel_xml()
    require(
        root.get("name") == CHANNEL and root.get("enabled") in ("true", "false"),
        "Channel oracle invalid",
    )
    return {"name": CHANNEL, "enabled": root.get("enabled") == "true"}


def read_recent_event():
    """Return metadata only. Raw event text never escapes this helper."""
    result = native(
        "wevtutil.exe",
        "qe",
        CHANNEL,
        "/q:" + QUERY,
        "/rd:true",
        "/c:1",
        "/f:xml",
        "/e:Events",
        "/uni:true",
        allow_failure=True,
    )
    if result.returncode:
        return {"native_exit": result.returncode, "state": "UNREADABLE"}
    root = ET.fromstring(result.stdout.decode("utf-16"))  # noqa: S314 -- bounded fixed local XML
    events = list(root)
    require(len(events) <= 1, "Event oracle exceeded requested bound")
    if not events:
        return {"native_exit": 0, "state": "NOT_OBSERVED", "count": 0}
    event = events[0]
    provider = event.find("./{*}System/{*}Provider")
    created = event.find("./{*}System/{*}TimeCreated")
    value = event.find("./{*}EventData/{*}Data[@Name='ScriptBlockText']")
    return {
        "native_exit": 0,
        "state": "OBSERVED",
        "count": 1,
        "event_id": event.findtext("./{*}System/{*}EventID"),
        "provider": provider.get("Name") if provider is not None else None,
        "timestamp": created.get("SystemTime") if created is not None else None,
        "usable_plaintext": value is not None
        and bool((value.text or "").strip())
        and "-----BEGIN CMS-----" not in (value.text or ""),
    }


def set_policy(value):
    if value is None:
        result = native(
            "reg.exe", "delete", "HKLM\\" + KEY, "/v", VALUE, "/f", "/reg:64", allow_failure=True
        )
        require(
            result.returncode == 0 or read_policy()["state"] == "MISSING",
            "Could not remove only the lab policy value",
        )
    else:
        native(
            "reg.exe",
            "add",
            "HKLM\\" + KEY,
            "/v",
            VALUE,
            "/t",
            "REG_DWORD",
            "/d",
            str(value),
            "/f",
            "/reg:64",
        )
        require(read_policy().get("value") == value, "Policy write/readback mismatch")


def set_channel_access(sddl):
    native("wevtutil.exe", "sl", CHANNEL, "/ca:" + sddl)


def deny_event_read(original):
    sddl = ps(
        "$ErrorActionPreference='Stop';"
        "$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;"
        "$sd=[Security.AccessControl.RawSecurityDescriptor]::new(" + quote_ps(original) + ");"
        "$ace=[Security.AccessControl.CommonAce]::new([Security.AccessControl.AceFlags]::None,[Security.AccessControl.AceQualifier]::AccessDenied,1,$sid,$false,$null);"
        "$sd.DiscretionaryAcl.InsertAce(0,$ace);"
        "$sd.GetSddlForm([Security.AccessControl.AccessControlSections]::All)"
    )
    set_channel_access(sddl)


def registry_acl_script(body):
    return (
        "$ErrorActionPreference='Stop';"
        "$base=[Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine,[Microsoft.Win32.RegistryView]::Registry64);"
        "$rights=[Security.AccessControl.RegistryRights]::ReadPermissions -bor [Security.AccessControl.RegistryRights]::ChangePermissions;"
        "$key=$base.OpenSubKey("
        + quote_ps(KEY)
        + ",[Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree,$rights);"
        "try{" + body + "}finally{$key.Dispose();$base.Dispose()}"
    )


def read_registry_acl():
    return ps(
        registry_acl_script(
            "$key.GetAccessControl().GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Access)"
        )
    )


def set_registry_acl(original, deny=False):
    body = (
        "$security=[Security.AccessControl.RegistrySecurity]::new();$security.SetSecurityDescriptorSddlForm("
        + quote_ps(original)
        + ",[Security.AccessControl.AccessControlSections]::Access);"
    )
    if deny:
        body += "$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;$rule=[Security.AccessControl.RegistryAccessRule]::new($sid,[Security.AccessControl.RegistryRights]::QueryValues,[Security.AccessControl.AccessControlType]::Deny);$security.AddAccessRule($rule);"
    ps(registry_acl_script(body + "$key.SetAccessControl($security)"))


def restore_registry_acl(original):
    set_registry_acl(original)
    require(read_registry_acl() == original, "Registry ACL rollback readback mismatch")


def missing_ancestors():
    import winreg

    missing = []
    parts = KEY.split("\\")
    for index in range(1, len(parts) + 1):
        path = "\\".join(parts[:index])
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_WOW64_64KEY
            ):
                pass
        except FileNotFoundError:
            missing.append(path)
    return missing


def remove_created_empty_keys(paths):
    import winreg

    for path in reversed(paths):
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        ) as key:
            subkeys, values, _ = winreg.QueryInfoKey(key)
            require(subkeys == 0 and values == 0, "New key is no longer empty; refusing deletion")
        winreg.DeleteKeyEx(winreg.HKEY_LOCAL_MACHINE, path, winreg.KEY_WOW64_64KEY)


def product_cli():
    result = subprocess.run(  # noqa: S603 -- fixed installed product CLI
        [
            sys.executable,
            "-m",
            "sigdoctor",
            "check",
            str(ROOT / "examples/powershell_script.yml"),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    require(result.returncode == 0, "Product CLI tool error; raw output suppressed")
    output = json.loads(result.stdout)
    require(output.get("schema_version") == "1", "Product CLI schema mismatch")
    return output


def record(report, scenario, expected, known_state):
    actual = product_cli()
    row = {
        "scenario": scenario,
        "known_state": known_state,
        "expected": expected,
        "actual": actual["result"]["status"],
        "matched": actual["result"]["status"] == expected,
        "exit_code": 0,
        "cli_assessment": actual,
    }
    report["scenarios"].append(row)
    print(f"{scenario}: expected {expected}, actual {row['actual']}, matched={row['matched']}")


def marker_observation(marker):
    # Marker is passed via the child environment, so the oracle script itself
    # does not contain it and cannot satisfy the generation check by logging itself.
    script = r"""
$ErrorActionPreference='Stop'
$events=Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational';Id=4104;StartTime=(Get-Date).AddMinutes(-5)} -MaxEvents 16
$found=@($events | Where-Object {
    [xml]$xml=$_.ToXml()
    $field=@($xml.Event.EventData.Data | Where-Object { $_.Name -eq 'ScriptBlockText' })
    $field.Count -eq 1 -and $field[0].InnerText.Contains($env:SIGDOCTOR_VALIDATION_MARKER)
})
[pscustomobject]@{marker_event_observed=($found.Count -gt 0);matching_count=$found.Count;event_id=4104;provider='Microsoft-Windows-PowerShell'} | ConvertTo-Json -Compress
"""
    previous = os.environ.get("SIGDOCTOR_VALIDATION_MARKER")
    try:
        os.environ["SIGDOCTOR_VALIDATION_MARKER"] = marker
        return json.loads(ps(script))
    finally:
        if previous is None:
            os.environ.pop("SIGDOCTOR_VALIDATION_MARKER", None)
        else:
            os.environ["SIGDOCTOR_VALIDATION_MARKER"] = previous


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disposable-github-runner", action="store_true", required=True)
    parser.parse_args(argv)
    hosted_runner_guard()  # MUST precede discovery or any modification.
    report = {
        "schema_version": "1",
        "product_commit": os.environ.get("GITHUB_SHA"),
        "run_url": f"https://github.com/GAWI01/sigdoctor/actions/runs/{os.environ.get('GITHUB_RUN_ID')}",
        "started_at": datetime.now(UTC).isoformat(),
        "scenarios": [],
        "rollback": {"verified": False},
    }
    original_policy = None
    original_channel = None
    event_acl = None
    registry_acl = None
    created_keys = []
    modified = False
    try:
        report["environment"] = json.loads(
            ps(
                "$os=Get-CimInstance Win32_OperatingSystem;"
                "$v=Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion';"
                "[pscustomobject]@{caption=$os.Caption;version=$os.Version;build=$os.BuildNumber;ubr=$v.UBR;architecture=$os.OSArchitecture;PowerShellVersion=$PSVersionTable.PSVersion.ToString();PSEdition=$PSVersionTable.PSEdition;Is64Bit=[Environment]::Is64BitProcess} | ConvertTo-Json -Compress"
            )
        )
        require(
            report["environment"]["PowerShellVersion"].startswith("5.1.")
            and report["environment"]["Is64Bit"],
            "Requires actual 64-bit Windows PowerShell 5.1",
        )
        original_policy = read_policy()
        require(
            original_policy["state"] in ("PRESENT", "MISSING"),
            "Original policy is inaccessible; setup not safe",
        )
        original_channel = read_channel()
        event_acl = channel_xml().get("channelAccess")
        require(bool(event_acl), "Cannot preserve original channel ACL")
        created_keys = missing_ancestors()
        report["baseline"] = {"policy": original_policy, "channel": original_channel}
        modified = True
        set_policy(1)
        native("wevtutil.exe", "sl", CHANNEL, "/e:true")

        # C: genuine absence on a newly enabled host; otherwise a real event-read
        # permission gap with independently readable enabled configuration.
        observation = read_recent_event()
        if observation["state"] == "NOT_OBSERVED":
            record(
                report,
                "C",
                "PARTIAL",
                {
                    "policy": read_policy(),
                    "channel": read_channel(),
                    "event": observation,
                    "setup": "Enabled before first recent event; no log clearing",
                },
            )
        else:
            deny_event_read(event_acl)
            try:
                observation = read_recent_event()
                require(
                    observation.get("native_exit") == 5 and read_channel()["enabled"],
                    "Event-denial setup did not preserve configuration readability",
                )
                record(
                    report,
                    "C",
                    "PARTIAL",
                    {
                        "policy": read_policy(),
                        "channel": read_channel(),
                        "event": observation,
                        "setup": "Temporary deny Event Log Read (mask 1) to current lab SID; config remains readable",
                    },
                )
            finally:
                set_channel_access(event_acl)

        marker = "SigDoctorValidationMarker-" + uuid.uuid4().hex
        ps("Write-Output " + quote_ps(marker))
        marker_proof = marker_observation(marker)
        require(
            marker_proof["marker_event_observed"],
            "Fresh action did not yield independently verified 4104",
        )
        require(read_recent_event().get("usable_plaintext") is True, "Newest event lacks plaintext")
        record(
            report,
            "A",
            "READY",
            {
                "policy": read_policy(),
                "channel": read_channel(),
                "event": read_recent_event(),
                "generation": "Fresh 64-bit Windows PowerShell 5.1 Write-Output with unique benign marker",
                "marker_proof": marker_proof,
                "marker_sha256": hashlib.sha256(marker.encode()).hexdigest(),
            },
        )

        set_policy(0)
        record(
            report,
            "B",
            "BLIND",
            {
                "policy": read_policy(),
                "channel": read_channel(),
                "event": read_recent_event(),
                "setup": "Explicit machine REG_DWORD 0; prior events retained",
            },
        )

        set_policy(None)
        require(read_policy()["state"] == "MISSING", "Missing-policy setup failed")
        record(
            report,
            "D1",
            "UNKNOWN",
            {
                "policy": read_policy(),
                "channel": read_channel(),
                "event": read_recent_event(),
                "setup": "Only named machine value removed; recent events retained",
            },
        )

        set_policy(1)
        registry_acl = read_registry_acl()
        set_registry_acl(registry_acl, deny=True)
        try:
            oracle = read_policy()
            require(
                oracle["state"] == "PERMISSION_DENIED" and oracle.get("native_error") == 5,
                "Registry-denial setup failed",
            )
            record(
                report,
                "D2",
                "UNKNOWN",
                {
                    "policy": oracle,
                    "channel": read_channel(),
                    "event": read_recent_event(),
                    "setup": "Temporary deny Registry QueryValues to current lab SID; known value was 1 before deny",
                },
            )
        finally:
            restore_registry_acl(registry_acl)
            registry_acl = None
    except Exception as exc:
        # Lab exceptions are controlled metadata; never print Windows/CLI payloads.
        report["setup_or_execution_error"] = {
            "type": type(exc).__name__,
            "message": str(exc)
            if isinstance(exc, RuntimeError)
            else "Unexpected lab failure; raw details suppressed",
        }
    finally:
        try:
            if modified:
                if registry_acl is not None:
                    restore_registry_acl(registry_acl)
                set_channel_access(event_acl)
                set_policy(original_policy.get("value"))
                native(
                    "wevtutil.exe", "sl", CHANNEL, "/e:" + str(original_channel["enabled"]).lower()
                )
                remove_created_empty_keys(created_keys)
                restored_policy = read_policy()
                restored_channel = read_channel()
                require(
                    restored_policy == original_policy
                    and restored_channel == original_channel
                    and channel_xml().get("channelAccess") == event_acl,
                    "Rollback readback mismatch",
                )
                report["rollback"] = {
                    "verified": True,
                    "policy": restored_policy,
                    "channel": restored_channel,
                    "channel_acl_restored": True,
                    "registry_acl_restored": True,
                    "created_empty_keys_removed": len(created_keys),
                }
            else:
                report["rollback"] = {"verified": True, "configuration_modified": False}
        except Exception:
            report["rollback"] = {
                "verified": False,
                "error": "Rollback failed; disposable VM must be discarded",
            }
        report["completed_at"] = datetime.now(UTC).isoformat()
        report["success"] = (
            len(report["scenarios"]) == 5
            and all(row["matched"] for row in report["scenarios"])
            and report["rollback"]["verified"]
            and "setup_or_execution_error" not in report
        )
        path = ROOT / "validation-output" / "controlled-windows.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print(
            "SIGDOCTOR_VALIDATION_REPORT="
            + json.dumps(report, separators=(",", ":"), ensure_ascii=True)
        )
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
