import json

import pytest

from sigdoctor.models import Evidence
from sigdoctor.output import render_json, render_terminal
from sigdoctor.workflow import check_rule


class FakeHost:
    def __init__(self, policy="ENABLED", channel="ENABLED", event="OBSERVED", field="OBSERVED"):
        self.states = (policy, channel, event, field)

    def collect(self):
        return tuple(
            Evidence(capability, state, "test-host", "2026-10-14T10:00:00+00:00", {})
            for capability, state in zip(
                (
                    "script_block_logging",
                    "powershell_channel",
                    "event_4104",
                    "field_ScriptBlockText",
                ),
                self.states,
                strict=True,
            )
        )


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        (("DISABLED", "ENABLED", "OBSERVED", "OBSERVED"), "BLIND"),
        (("ENABLED", "ENABLED", "OBSERVED", "OBSERVED"), "READY"),
        (("UNKNOWN", "UNKNOWN", "NOT_OBSERVED", "UNKNOWN"), "UNKNOWN"),
        (("ENABLED", "ENABLED", "NOT_OBSERVED", "UNKNOWN"), "PARTIAL"),
        (("ERROR", "ENABLED", "OBSERVED", "OBSERVED"), "UNKNOWN"),
        (("ENABLED", "DISABLED", "OBSERVED", "OBSERVED"), "BLIND"),
        (("ENABLED", "ENABLED", "OBSERVED", "UNKNOWN"), "PARTIAL"),
        (("ENABLED", "ERROR", "OBSERVED", "OBSERVED"), "UNKNOWN"),
    ],
)
def test_complete_journey_one_decision_for_both_renderers(rule_path, states, expected):
    assessment = check_rule(rule_path, probe=FakeHost(*states))
    payload = json.loads(render_json(assessment))
    assert payload["schema_version"] == "1"
    assert payload["result"]["status"] == expected
    assert expected in render_terminal(assessment)
    assert payload["result"]["reasons"]
    assert len(payload["evidence"]) == 4
    assert payload["rule"]["required_fields"] == ["ScriptBlockText"]
    assert "Windows PowerShell 5.1" in payload["scope"]
    assert {r["provenance"] for r in payload["requirements"]} == {"DIRECT", "DERIVED"}


class NoProbe:
    def collect(self):
        pytest.fail("Unsupported rules must not probe the host")


@pytest.mark.parametrize(
    ("old", "new", "reason"),
    [
        ("product: windows", "product: linux", "UNSUPPORTED_PLATFORM"),
        ("category: ps_script", "category: process_creation", "UNSUPPORTED_LOGSOURCE"),
        ("category: ps_script", "category: ps_module", "UNSUPPORTED_LOGSOURCE"),
        (
            "category: ps_script",
            "category: ps_script\n  service: security",
            "UNSUPPORTED_LOGSOURCE",
        ),
        ("ScriptBlockText|contains", "CustomField|contains", "UNSUPPORTED_FIELD"),
        ("ScriptBlockText|contains", "ScriptBlockText|fieldref", "UNSUPPORTED_SEMANTICS"),
        ("ScriptBlockText|contains", "ScriptBlockText|base64", "UNSUPPORTED_SEMANTICS"),
    ],
)
def test_unsupported_is_unknown_without_probes(rule_path, rule_text, old, new, reason):
    rule_path.write_text(rule_text.replace(old, new), encoding="utf-8")
    result = check_rule(rule_path, probe=NoProbe())
    assert result.result.status == "UNKNOWN"
    assert reason in render_json(result)


def test_missing_or_duplicate_evidence_cannot_be_ready(rule_path):
    class Missing:
        def collect(self):
            return ()

    class Duplicate:
        def collect(self):
            return FakeHost().collect() + FakeHost().collect()[:1]

    assert check_rule(rule_path, probe=Missing()).result.status == "UNKNOWN"
    assert check_rule(rule_path, probe=Duplicate()).result.status == "UNKNOWN"


def test_control_characters_in_rule_title_cannot_control_terminal(rule_path, rule_text):
    rule_path.write_text(
        rule_text.replace("Example Script Block Marker", '"Example\\u001b[2J\\nSpoofed"'),
        encoding="utf-8",
    )
    terminal = render_terminal(check_rule(rule_path, probe=FakeHost()))
    assert "\x1b" not in terminal
    assert "\nSpoofed" not in terminal
