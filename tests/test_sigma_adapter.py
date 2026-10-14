from pathlib import Path

import pytest
from test_workflow import FakeHost, NoProbe

from sigdoctor.adapter import load_rule
from sigdoctor.models import ToolError
from sigdoctor.workflow import check_rule


def test_metadata_and_display_fields_remain_separate(rule_path):
    rule = load_rule(rule_path)
    assert rule.required_fields == ("ScriptBlockText",)
    assert rule.display_fields == ("Computer",)
    assert rule.mitre_techniques == ("T1059.001",)
    assert rule.tags == ("attack.execution", "attack.t1059.001")
    assert rule.definition == "Script Block Logging must be enabled."
    assert len(rule.sha256) == 64


@pytest.mark.parametrize("taxonomy", ["ecs", "custom_native", "null"])
def test_non_default_taxonomy_is_unknown_without_probes(rule_path, rule_text, taxonomy):
    rule_path.write_text(f"taxonomy: {taxonomy}\n" + rule_text, encoding="utf-8")
    assessment = check_rule(rule_path, probe=NoProbe())
    assert assessment.result.status == "UNKNOWN"
    assert any(issue.code == "UNSUPPORTED_TAXONOMY" for issue in assessment.result.reasons)


def test_explicit_sigma_taxonomy_retains_native_support(rule_path, rule_text):
    rule_path.write_text("taxonomy: sigma\n" + rule_text, encoding="utf-8")
    assert check_rule(rule_path, probe=FakeHost()).result.status == "READY"


def test_unused_selection_does_not_add_requirements(rule_path, rule_text):
    rule_path.write_text(
        rule_text.replace(
            "  condition: selection", "  unused:\n    CustomField: x\n  condition: selection"
        ),
        encoding="utf-8",
    )
    assert check_rule(rule_path, probe=FakeHost()).result.status == "READY"


@pytest.mark.parametrize(
    "condition",
    [
        "all of selection*",
        "1 of selection*",
        "selection or selection_b",
        "selection and not selection_b",
    ],
)
def test_boolean_predicates_on_same_native_field(rule_path, rule_text, condition):
    rule_path.write_text(
        rule_text.replace(
            "  condition: selection",
            "  selection_b:\n    ScriptBlockText|endswith: other\n  condition: " + condition,
        ),
        encoding="utf-8",
    )
    assert check_rule(rule_path, probe=FakeHost()).result.status == "READY"


def test_service_mapping_requires_explicit_4104(rule_path, rule_text):
    text = rule_text.replace("category: ps_script", "service: powershell")
    rule_path.write_text(text, encoding="utf-8")
    assert check_rule(rule_path, probe=NoProbe()).result.status == "UNKNOWN"
    rule_path.write_text(
        text.replace("  selection:", "  selection:\n    EventID: 4104"), encoding="utf-8"
    )
    assert check_rule(rule_path, probe=FakeHost()).result.status == "READY"


@pytest.mark.parametrize("event_predicate", ["4103", "[4103, 4104]", "null"])
def test_event_alternatives_never_use_4104_profile(rule_path, rule_text, event_predicate):
    rule_path.write_text(
        rule_text.replace("  selection:", "  selection:\n    EventID: " + event_predicate),
        encoding="utf-8",
    )
    assert check_rule(rule_path, probe=NoProbe()).result.status == "UNKNOWN"


def test_negated_event_id_is_not_positive_4104_requirement(rule_path, rule_text):
    rule_path.write_text(
        rule_text.replace(
            "  condition: selection",
            "  event:\n    EventID: 4104\n  condition: selection and not event",
        ),
        encoding="utf-8",
    )
    assert check_rule(rule_path, probe=NoProbe()).result.status == "UNKNOWN"


@pytest.mark.parametrize(
    "content",
    [
        "",
        "[]",
        "title: [",
        "!!python/object/apply:os.system ['echo bad']",
        "a: &loop [*loop]",
        "title: One\ntitle: Two",
        "a: 1\n---\na: 2",
        "a: " + "[" * 80 + "0" + "]" * 80,
        "x" * (256 * 1024 + 1),
    ],
    ids=[
        "empty",
        "sequence",
        "broken-yaml",
        "object-tag",
        "alias",
        "duplicate",
        "multi-document",
        "deep",
        "oversized",
    ],
)
def test_unsafe_or_malformed_yaml_has_clean_error(rule_path, content):
    rule_path.write_text(content, encoding="utf-8")
    with pytest.raises(ToolError) as exc:
        load_rule(rule_path)
    assert exc.value.code == "RULE_PARSE_ERROR"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("logsource:", "not_logsource:"),
        ("condition: selection", "condition: missing"),
        ("condition: selection", "condition: selection and"),
        ("title: Example Script Block Marker", "title: [bad]"),
        ("ScriptBlockText|contains", "ScriptBlockText|invalidmodifier"),
    ],
)
def test_invalid_sigma_fails_before_host_access(rule_path, rule_text, old, new):
    rule_path.write_text(rule_text.replace(old, new), encoding="utf-8")
    with pytest.raises(ToolError) as exc:
        check_rule(rule_path, probe=NoProbe())
    assert exc.value.code == "RULE_PARSE_ERROR"


def test_missing_and_directory_paths_are_input_errors(tmp_path: Path):
    for path in (tmp_path, tmp_path / "missing.yml"):
        with pytest.raises(ToolError):
            load_rule(path)


@pytest.mark.parametrize("modifier", ["base64", "cased", "expand"])
def test_multi_value_unsupported_modifier_cannot_be_ready(rule_path, rule_text, modifier):
    text = rule_text.replace(
        "ScriptBlockText|contains: 'SigDoctorExampleMarker'",
        f"ScriptBlockText|{modifier}: [foo, bar]",
    )
    rule_path.write_text(text, encoding="utf-8")
    assert check_rule(rule_path, probe=NoProbe()).result.status == "UNKNOWN"


def test_expanding_modifier_never_reaches_pysigma(rule_path, rule_text, monkeypatch):
    # Applying repeated wide modifiers expands exponentially even for tiny YAML.
    text = rule_text.replace("ScriptBlockText|contains", "ScriptBlockText" + "|wide" * 12)
    rule_path.write_text(text, encoding="utf-8")

    def forbidden(*args, **kwargs):
        pytest.fail("Unsupported expansion reached the third-party parser")

    monkeypatch.setattr("sigdoctor.adapter.SigmaRule.from_dict", forbidden)
    assert check_rule(rule_path, probe=NoProbe()).result.status == "UNKNOWN"


def test_unc_path_rejected_before_resolution(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("UNC resolution can initiate network access")

    monkeypatch.setattr(Path, "resolve", forbidden)
    with pytest.raises(ToolError):
        load_rule(Path(r"\\server\share\rule.yml"))


def test_mapped_network_drive_rejected_before_file_access(rule_path, monkeypatch):
    monkeypatch.setattr("sigdoctor.adapter._drive_type", lambda root: 4)

    def forbidden(*args, **kwargs):
        pytest.fail("Mapped drive accessed before checking local-only boundary")

    monkeypatch.setattr(Path, "lstat", forbidden)
    with pytest.raises(ToolError):
        load_rule(rule_path)


def test_reparse_point_is_rejected_without_following_it(rule_path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        Path, "lstat", lambda path: SimpleNamespace(st_file_attributes=0x400, st_mode=0)
    )
    with pytest.raises(ToolError):
        load_rule(rule_path)
