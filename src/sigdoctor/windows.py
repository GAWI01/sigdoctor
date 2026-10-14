"""Read-only Windows boundaries. Rule data never enters a command."""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sigdoctor.models import Evidence, State

CHANNEL = "Microsoft-Windows-PowerShell/Operational"
PROVIDER_GUID = "{a0c1853b-5c40-4b15-8766-3cf1c58f985a}"
POLICY_KEY = r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging"
POLICY_VALUE = "EnableScriptBlockLogging"
CAPABILITIES = ("script_block_logging", "powershell_channel", "event_4104", "field_ScriptBlockText")
MAX_XML = 2 * 1024 * 1024


class ProbeError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def read_machine_policy() -> int | None:
    if sys.platform != "win32":
        raise ProbeError("UNSUPPORTED_PLATFORM")
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, POLICY_KEY, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        ) as key:
            value, kind = winreg.QueryValueEx(key, POLICY_VALUE)
            if kind != winreg.REG_DWORD or type(value) is not int:
                return None
            return value
    except FileNotFoundError:
        return None


def run_command(args: tuple[str, ...]) -> bytes:
    # Absolute system executable: never search the working directory or PATH.
    root = os.environ.get("SystemRoot", r"C:\Windows")
    binary = Path(root) / "System32" / "wevtutil.exe"
    try:
        result = subprocess.run(  # noqa: S603 -- fixed system executable and internal arguments
            [str(binary), *args],
            shell=False,
            capture_output=True,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError("PROBE_TIMEOUT") from exc
    except PermissionError as exc:
        raise ProbeError("PERMISSION_DENIED") from exc
    except OSError as exc:
        raise ProbeError("WINDOWS_API_ERROR") from exc
    if result.returncode:
        raise ProbeError("PERMISSION_DENIED" if result.returncode == 5 else "WINDOWS_API_ERROR")
    if len(result.stdout) > MAX_XML:
        raise ProbeError("PROBE_OUTPUT_LIMIT")
    return result.stdout


def _xml(raw: bytes) -> ET.Element:
    if len(raw) > MAX_XML:
        raise ProbeError("PROBE_OUTPUT_LIMIT")
    try:
        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8")
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise ValueError("XML declarations are unsupported")
        return ET.fromstring(text)  # noqa: S314 -- bounded, no DTD/entities; local fixed command
    except (UnicodeError, ValueError, ET.ParseError) as exc:
        raise ProbeError("INVALID_PROBE_OUTPUT") from exc


def _now() -> datetime:
    return datetime.now(UTC)


class WindowsProbe:
    def __init__(
        self,
        read_policy: Callable[[], object] = read_machine_policy,
        runner: Callable[[tuple[str, ...]], bytes] = run_command,
        clock: Callable[[], datetime] = _now,
        platform: str = sys.platform,
    ) -> None:
        self.read_policy = read_policy
        self.runner = runner
        self.clock = clock
        self.platform = platform

    def collect(self) -> tuple[Evidence, ...]:
        now = self.clock().astimezone(UTC)
        if self.platform != "win32":
            return tuple(
                Evidence(
                    name, "UNSUPPORTED", "platform", now.isoformat(), {}, "UNSUPPORTED_PLATFORM"
                )
                for name in CAPABILITIES
            )
        policy = self._policy(now)
        channel = self._channel(now)
        event, field = self._event(now)
        return policy, channel, event, field

    def _policy(self, now: datetime) -> Evidence:
        source = f"registry:HKLM(64-bit)\\{POLICY_KEY}\\{POLICY_VALUE}"
        try:
            value = self.read_policy()
            state: State = "UNKNOWN"
            if type(value) is int and value in (0, 1):
                state = "ENABLED" if value else "DISABLED"
            details: dict[str, str | int | bool | None] = {
                "value": value if type(value) is int else None,
                "meaning": "Machine policy; absent/invalid is unknown, not disabled.",
            }
            return Evidence("script_block_logging", state, source, now.isoformat(), details)
        except PermissionError:
            return Evidence(
                "script_block_logging", "UNKNOWN", source, now.isoformat(), {}, "PERMISSION_DENIED"
            )
        except OSError:
            return Evidence(
                "script_block_logging", "ERROR", source, now.isoformat(), {}, "WINDOWS_API_ERROR"
            )

    def _channel(self, now: datetime) -> Evidence:
        source = f"wevtutil:gl:{CHANNEL}"
        try:
            root = _xml(self.runner(("gl", CHANNEL, "/f:xml", "/uni:true")))
            state: State = "UNKNOWN"
            if root.tag.rsplit("}", 1)[-1] == "channel" and root.get("name") == CHANNEL:
                enabled = root.get("enabled")
                if enabled in ("true", "false"):
                    state = "ENABLED" if enabled == "true" else "DISABLED"
            return Evidence(
                "powershell_channel", state, source, now.isoformat(), {"channel": CHANNEL}
            )
        except ProbeError as exc:
            return Evidence(
                "powershell_channel",
                "UNKNOWN" if exc.code == "PERMISSION_DENIED" else "ERROR",
                source,
                now.isoformat(),
                {},
                exc.code,
            )

    def _event(self, now: datetime) -> tuple[Evidence, Evidence]:
        source = f"wevtutil:qe:{CHANNEL}"
        event_state: State = "UNKNOWN"
        field_state: State = "UNKNOWN"
        error: str | None = None
        details: dict[str, str | int | bool | None] = {
            "event_id": 4104,
            "window_hours": 24,
            "sample_limit": 1,
        }
        field_details: dict[str, str | int | bool | None] = {"field": "ScriptBlockText"}
        try:
            root = _xml(
                self.runner(
                    (
                        "qe",
                        CHANNEL,
                        "/q:*[System[(EventID=4104) and TimeCreated[timediff(@SystemTime) <= 86400000]]]",
                        "/rd:true",
                        "/c:1",
                        "/f:xml",
                        "/e:Events",
                        "/uni:true",
                    )
                )
            )
            if root.tag != "Events":
                raise ProbeError("INVALID_PROBE_OUTPUT")
            events = list(root)
            if not events:
                event_state = "NOT_OBSERVED"
            elif len(events) != 1 or events[0].tag.rsplit("}", 1)[-1] != "Event":
                raise ProbeError("INVALID_PROBE_OUTPUT")
            else:
                event = events[0]
                provider = event.find("./{*}System/{*}Provider")
                created = event.find("./{*}System/{*}TimeCreated")
                matching = (
                    provider is not None
                    and provider.get("Name") == "Microsoft-Windows-PowerShell"
                    and provider.get("Guid", "").lower() == PROVIDER_GUID
                    and event.findtext("./{*}System/{*}EventID") == "4104"
                    and event.findtext("./{*}System/{*}Channel") == CHANNEL
                    and created is not None
                )
                if matching and created is not None:
                    stamp = datetime.fromisoformat(
                        created.get("SystemTime", "").replace("Z", "+00:00")
                    )
                    if stamp.tzinfo is None:
                        raise ValueError("Missing timezone")
                    age = now - stamp
                    if age > timedelta(hours=24):
                        event_state = "NOT_OBSERVED"
                    elif age >= timedelta(0):
                        event_state = "OBSERVED"
                        details["latest_timestamp"] = stamp.astimezone(UTC).isoformat()
                        values = [
                            node.text or ""
                            for node in event.findall("./{*}EventData/{*}Data")
                            if node.get("Name") == "ScriptBlockText"
                        ]
                        if len(values) == 1 and values[0].strip():
                            if "-----BEGIN CMS-----" in values[0]:
                                field_details["reason"] = (
                                    "Encrypted content; plaintext availability unresolved."
                                )
                            else:
                                field_state = "OBSERVED"
                                field_details["nonempty_plaintext"] = True
                        else:
                            field_details["reason"] = (
                                "Field missing, empty or ambiguous in newest sample; not proof of permanent absence."
                            )
        except ProbeError as exc:
            event_state = "UNKNOWN" if exc.code == "PERMISSION_DENIED" else "ERROR"
            error = exc.code
        except (ValueError, OverflowError):
            event_state = "ERROR"
            error = "INVALID_PROBE_OUTPUT"
        return (
            Evidence("event_4104", event_state, source, now.isoformat(), details, error),
            Evidence(
                "field_ScriptBlockText", field_state, source, now.isoformat(), field_details, error
            ),
        )
