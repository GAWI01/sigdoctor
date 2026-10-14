from pathlib import Path
from typing import Protocol

from sigdoctor.adapter import load_rule
from sigdoctor.evaluator import evaluate
from sigdoctor.models import Assessment, Evidence
from sigdoctor.profile import load_profile, support_issues


class Probe(Protocol):
    def collect(self) -> tuple[Evidence, ...]: ...


def check_rule(path: Path, probe: Probe | None = None) -> Assessment:
    rule = load_rule(path)
    profile = load_profile()
    if support_issues(rule, profile):
        return evaluate(rule, profile, ())
    if probe is None:
        from sigdoctor.windows import WindowsProbe

        probe = WindowsProbe()
    return evaluate(rule, profile, probe.collect())
