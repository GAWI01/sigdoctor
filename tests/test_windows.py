import subprocess
from datetime import UTC, datetime

import pytest

from sigdoctor.windows import ProbeError, WindowsProbe, run_command

NOW = datetime(2026, 10, 14, 10, 0, tzinfo=UTC)
CHANNEL = '<channel xmlns="http://schemas.microsoft.com/win/2004/08/events" name="Microsoft-Windows-PowerShell/Operational" enabled="true" />'
EVENT = """<Events><Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
<System><Provider Name="Microsoft-Windows-PowerShell" Guid="{a0c1853b-5c40-4b15-8766-3cf1c58f985a}"/><EventID>4104</EventID>
<Channel>Microsoft-Windows-PowerShell/Operational</Channel><TimeCreated SystemTime="2026-10-14T09:00:00.1234567Z"/></System>
<EventData><Data Name="ScriptBlockText">PRIVATE SCRIPT MUST NOT LEAK</Data><Data Name="Path">PRIVATE PATH</Data></EventData>
</Event></Events>"""


def collect(policy=1, channel=CHANNEL, event=EVENT):
    def read():
        if isinstance(policy, Exception):
            raise policy
        return policy

    def run(args):
        # Wrong query shape should not accidentally satisfy the fixture.
        assert args[0] in ("gl", "qe")
        assert args[1] == "Microsoft-Windows-PowerShell/Operational"
        assert "/uni:true" in args
        if args[0] == "qe":
            assert "/c:1" in args and "/rd:true" in args
            assert any("EventID=4104" in value and "86400000" in value for value in args)
        output = channel if args[0] == "gl" else event
        if isinstance(output, Exception):
            raise output
        return output.encode("utf-16")

    return WindowsProbe(read_policy=read, runner=run, clock=lambda: NOW, platform="win32").collect()


def states(evidence):
    return {item.capability: item.state for item in evidence}


def test_real_probe_logic_produces_safe_evidence():
    evidence = collect()
    assert states(evidence) == {
        "script_block_logging": "ENABLED",
        "powershell_channel": "ENABLED",
        "event_4104": "OBSERVED",
        "field_ScriptBlockText": "OBSERVED",
    }
    assert "PRIVATE" not in repr(evidence)
    assert all(item.observed_at == "2026-10-14T10:00:00+00:00" for item in evidence)


@pytest.mark.parametrize(
    ("value", "state"),
    [(0, "DISABLED"), (None, "UNKNOWN"), (2, "UNKNOWN"), ("1", "UNKNOWN"), (True, "UNKNOWN")],
)
def test_registry_requires_explicit_valid_dword(value, state):
    assert states(collect(policy=value))["script_block_logging"] == state


def test_registry_permission_denied_is_not_disabled():
    evidence = collect(policy=PermissionError("PRIVATE registry details"))
    assert evidence[0].state == "UNKNOWN"
    assert evidence[0].error_code == "PERMISSION_DENIED"
    assert "PRIVATE" not in repr(evidence)


@pytest.mark.parametrize(
    ("output", "state"),
    [
        (CHANNEL.replace('enabled="true"', 'enabled="false"'), "DISABLED"),
        (CHANNEL.replace('enabled="true"', ""), "UNKNOWN"),
        (CHANNEL.replace("Microsoft-Windows-PowerShell/Operational", "Other"), "UNKNOWN"),
        ("not XML", "ERROR"),
        (ProbeError("PERMISSION_DENIED"), "UNKNOWN"),
        (ProbeError("PROBE_TIMEOUT"), "ERROR"),
    ],
)
def test_channel_structured_states(output, state):
    assert states(collect(channel=output))["powershell_channel"] == state


@pytest.mark.parametrize(
    ("event", "event_state", "field_state"),
    [
        ("<Events />", "NOT_OBSERVED", "UNKNOWN"),
        (EVENT.replace("2026-10-14", "2026-10-10"), "NOT_OBSERVED", "UNKNOWN"),
        (EVENT.replace("2026-10-14", "2026-10-15"), "UNKNOWN", "UNKNOWN"),
        (EVENT.replace("PRIVATE SCRIPT MUST NOT LEAK", ""), "OBSERVED", "UNKNOWN"),
        (EVENT.replace("ScriptBlockText", "OtherField"), "OBSERVED", "UNKNOWN"),
        (
            EVENT.replace(
                "PRIVATE SCRIPT MUST NOT LEAK", "-----BEGIN CMS-----SECRET-----END CMS-----"
            ),
            "OBSERVED",
            "UNKNOWN",
        ),
        (EVENT.replace("Microsoft-Windows-PowerShell", "PowerShellCore"), "UNKNOWN", "UNKNOWN"),
        (EVENT.replace("4104", "4103"), "UNKNOWN", "UNKNOWN"),
        ("<!DOCTYPE x [<!ENTITY x 'bad'>]><Events>&x;</Events>", "ERROR", "UNKNOWN"),
        (ProbeError("PROBE_TIMEOUT"), "ERROR", "UNKNOWN"),
    ],
)
def test_event_sample_cannot_supply_false_confidence(event, event_state, field_state):
    result = states(collect(event=event))
    assert result["event_4104"] == event_state
    assert result["field_ScriptBlockText"] == field_state


def test_output_parsing_bound():
    assert states(collect(event="x" * (2 * 1024 * 1024)))["event_4104"] == "ERROR"


def test_non_windows_host_does_not_call_native_boundaries():
    def forbidden(*args):
        pytest.fail("Native access on unsupported platform")

    result = WindowsProbe(read_policy=forbidden, runner=forbidden, platform="linux").collect()
    assert all(e.state == "UNSUPPORTED" for e in result)


def test_subprocess_has_fixed_executable_timeout_and_no_shell(monkeypatch):
    def fake_run(args, **kwargs):
        assert args[0].lower().endswith("wevtutil.exe")
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 10
        assert kwargs["capture_output"] is True
        return subprocess.CompletedProcess(args, 0, b"data", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert (
        run_command(("gl", "Microsoft-Windows-PowerShell/Operational", "/f:xml", "/uni:true"))
        == b"data"
    )


@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (subprocess.TimeoutExpired("wevtutil", 10), "PROBE_TIMEOUT"),
        (PermissionError("PRIVATE"), "PERMISSION_DENIED"),
        (OSError("PRIVATE"), "WINDOWS_API_ERROR"),
    ],
)
def test_native_execution_errors_are_structured(monkeypatch, failure, code):
    def fake_run(*args, **kwargs):
        raise failure

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ProbeError) as exc:
        run_command(("gl", "Microsoft-Windows-PowerShell/Operational"))
    assert exc.value.code == code
    assert "PRIVATE" not in str(exc.value)


def test_nonzero_exit_does_not_parse_output(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 5, b"PRIVATE", b"PRIVATE"),
    )
    with pytest.raises(ProbeError) as exc:
        run_command(("gl", "Microsoft-Windows-PowerShell/Operational"))
    assert exc.value.code == "PERMISSION_DENIED"
