"""Read-only observations of the actual host; never change its logging state."""

import os
import sys

import pytest

from sigdoctor.output import render_json
from sigdoctor.windows import WindowsProbe
from sigdoctor.workflow import check_rule


@pytest.mark.windows_integration
@pytest.mark.skipif(
    sys.platform != "win32" or os.environ.get("SIGDOCTOR_WINDOWS_TESTS") != "1",
    reason="Opt in with SIGDOCTOR_WINDOWS_TESTS=1 on Windows",
)
def test_actual_host_observation_contract(rule_path):
    evidence = WindowsProbe().collect()
    assert len(evidence) == 4
    assert all(e.observed_at and e.source for e in evidence)
    assert evidence[1].state in {"ENABLED", "DISABLED"}, evidence[1]

    class Snapshot:
        def collect(self):
            return evidence

    assessment = check_rule(rule_path, Snapshot())
    by_name = {e.capability: e.state for e in evidence}
    if assessment.result.status == "READY":
        assert by_name == {
            "script_block_logging": "ENABLED",
            "powershell_channel": "ENABLED",
            "event_4104": "OBSERVED",
            "field_ScriptBlockText": "OBSERVED",
        }
    assert "PRIVATE" not in render_json(assessment)
