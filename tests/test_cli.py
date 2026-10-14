import json

import pytest
from test_workflow import FakeHost

from sigdoctor.cli import main
from sigdoctor.models import ToolError
from sigdoctor.workflow import check_rule


@pytest.mark.parametrize(
    "states, expected",
    [
        (("DISABLED", "ENABLED", "OBSERVED", "OBSERVED"), "BLIND"),
        (("UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN"), "UNKNOWN"),
        (("ENABLED", "ENABLED", "OBSERVED", "OBSERVED"), "READY"),
    ],
)
def test_cli_renders_same_assessment_and_success_exit(
    rule_path, capsys, monkeypatch, states, expected
):
    monkeypatch.setattr(
        "sigdoctor.cli.check_rule", lambda path: check_rule(path, FakeHost(*states))
    )
    assert main(["check", str(rule_path), "--json"]) == 0
    output = capsys.readouterr()
    assert not output.err
    assert json.loads(output.out)["result"]["status"] == expected
    assert main(["check", str(rule_path)]) == 0
    assert "Result: " + expected in capsys.readouterr().out


def test_malformed_input_is_clean_machine_readable_error(rule_path, capsys):
    rule_path.write_text("SECRET: [malformed", encoding="utf-8")
    assert main(["check", str(rule_path), "--json"]) == 2
    output = capsys.readouterr()
    assert json.loads(output.out)["error"]["code"] == "RULE_PARSE_ERROR"
    assert "SECRET" not in output.out and "Traceback" not in output.out
    assert output.err == ""


def test_linux_rule_completes_without_crash(rule_path, rule_text, capsys):
    rule_path.write_text(rule_text.replace("windows", "linux"), encoding="utf-8")
    assert main(["check", str(rule_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["status"] == "UNKNOWN"
    assert payload["evidence"] == []


@pytest.mark.parametrize(
    "args", [["check", "--json"], ["check", "example.yml", "--bad", "--json"], ["--json"]]
)
def test_bad_usage_with_json_has_json_error(args, capsys):
    assert main(args) == 2
    output = capsys.readouterr()
    assert json.loads(output.out)["error"]["code"] == "INVALID_ARGUMENT"
    assert output.err == ""


@pytest.mark.parametrize(
    "failure, code",
    [
        (ToolError("INVALID_PROFILE", "Reinstall", 1), "INVALID_PROFILE"),
        (RuntimeError("PRIVATE details"), "INTERNAL_ERROR"),
    ],
)
def test_tool_failure_is_sanitized(rule_path, capsys, monkeypatch, failure, code):
    def fail(path):
        raise failure

    monkeypatch.setattr("sigdoctor.cli.check_rule", fail)
    assert main(["check", str(rule_path), "--json"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out)["error"]["code"] == code
    assert "PRIVATE" not in output.out


@pytest.mark.parametrize("flag, text", [("--help", "check"), ("--version", "0.1.0")])
def test_help_version(flag, text, capsys):
    assert main([flag]) == 0
    assert text in capsys.readouterr().out
