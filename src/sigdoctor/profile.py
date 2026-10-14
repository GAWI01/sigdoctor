import json
from importlib.resources import files

from sigdoctor.models import Issue, RuleRequirements, TelemetryProfile, ToolError


def load_profile() -> TelemetryProfile:
    try:
        data = json.loads(
            files("sigdoctor")
            .joinpath("profiles/windows_powershell.json")
            .read_text(encoding="utf-8")
        )
        strings = ("id", "scope", "product", "category", "service", "channel", "provider")
        lists = ("fields", "capabilities", "references", "limitations")
        if any(not isinstance(data.get(key), str) or not data[key] for key in strings):
            raise ValueError("Invalid profile strings")
        if any(
            not isinstance(data.get(key), list)
            or not data[key]
            or any(not isinstance(x, str) for x in data[key])
            for key in lists
        ):
            raise ValueError("Invalid profile lists")
        if data["event_id"] != 4104 or data["capabilities"] != [
            "script_block_logging",
            "powershell_channel",
            "event_4104",
            "field_ScriptBlockText",
        ]:
            raise ValueError("Unsupported profile contract")
        for key in lists:
            data[key] = tuple(data[key])
        return TelemetryProfile(**data)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ToolError(
            "INVALID_PROFILE",
            "The bundled telemetry profile is missing or invalid. Reinstall SigDoctor.",
            1,
        ) from exc


def support_issues(rule: RuleRequirements, profile: TelemetryProfile) -> tuple[Issue, ...]:
    issues = list(rule.issues)
    if rule.product != profile.product:
        issues.append(Issue("UNSUPPORTED_PLATFORM", "Only Windows rule input is supported."))
    category_match = rule.category == profile.category and rule.service is None
    service_match = (
        rule.service == profile.service
        and rule.category in (None, profile.category)
        and rule.event_ids == (4104,)
    )
    if not (category_match or service_match):
        issues.append(
            Issue(
                "UNSUPPORTED_LOGSOURCE",
                "No unambiguous supported Windows PowerShell 5.1 Script Block profile.",
            )
        )
    if not rule.required_fields or "ScriptBlockText" not in rule.required_fields:
        issues.append(
            Issue("UNSUPPORTED_FIELD", "This slice requires a native ScriptBlockText predicate.")
        )
    if set(rule.required_fields) - set(profile.fields):
        issues.append(
            Issue(
                "UNSUPPORTED_FIELD",
                "Detection uses fields outside the native ScriptBlockText profile.",
            )
        )
    return tuple(issues)
