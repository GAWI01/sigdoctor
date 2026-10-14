import json
import unicodedata
from dataclasses import asdict

from sigdoctor.models import Assessment


def _safe(text: str) -> str:
    return "".join(c if not unicodedata.category(c).startswith("C") else "?" for c in text)


def render_json(assessment: Assessment) -> str:
    return json.dumps(asdict(assessment), indent=2, ensure_ascii=True)


def render_terminal(assessment: Assessment) -> str:
    lines = ["SigDoctor", f"Rule: {_safe(assessment.rule.title)}", f"Scope: {assessment.scope}"]
    if assessment.rule.mitre_techniques:
        lines.append("MITRE: " + ", ".join(assessment.rule.mitre_techniques))
    lines += ["", "Telemetry evidence:"]
    for item in assessment.evidence:
        details = json.dumps(item.details, ensure_ascii=True, sort_keys=True)
        lines.append(f"  {item.capability}: {item.state} [{item.source}; {item.observed_at}]")
        lines.append(f"    {details}")
        if item.error_code:
            lines.append(f"    Error: {item.error_code}")
    if not assessment.evidence:
        lines.append("  No host probes performed for this unsupported rule.")
    lines += ["", f"Result: {assessment.result.status}"]
    lines += [f"  {issue.code}: {issue.message}" for issue in assessment.result.reasons]
    lines += ["", "Limits:"] + [f"  {limit}" for limit in assessment.limitations]
    return "\n".join(lines)
