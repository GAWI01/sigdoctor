"""The sole owner of readiness classification."""

from sigdoctor.models import (
    Assessment,
    Decision,
    Evidence,
    Issue,
    Requirement,
    RuleRequirements,
    TelemetryProfile,
)
from sigdoctor.profile import support_issues


def evaluate(
    rule: RuleRequirements, profile: TelemetryProfile, evidence: tuple[Evidence, ...]
) -> Assessment:
    requirements = tuple(
        Requirement(field, "DIRECT", "Referenced by the active detection condition.")
        for field in rule.required_fields
    )
    unsupported = support_issues(rule, profile)
    if unsupported:
        decision = Decision("UNKNOWN", unsupported)
    else:
        requirements += tuple(
            Requirement(cap, "DERIVED", f"Required by telemetry profile {profile.id}.")
            for cap in profile.capabilities
        )
        observations = {item.capability: item for item in evidence}
        if len(observations) != len(evidence):
            decision = Decision(
                "UNKNOWN",
                (
                    Issue(
                        "CONFLICTING_EVIDENCE",
                        "Duplicate capability observations cannot establish readiness.",
                    ),
                ),
            )
        else:
            core = ("script_block_logging", "powershell_channel")
            disabled = [
                name
                for name in core
                if name in observations and observations[name].state == "DISABLED"
            ]
            if disabled:
                decision = Decision(
                    "BLIND",
                    tuple(
                        Issue(
                            "CAPABILITY_DISABLED",
                            f"Required capability {name} is explicitly disabled for this provider.",
                        )
                        for name in disabled
                    ),
                )
            elif any(
                name not in observations or observations[name].state != "ENABLED" for name in core
            ):
                decision = Decision(
                    "UNKNOWN",
                    (
                        Issue(
                            "INSUFFICIENT_EVIDENCE",
                            "Machine Script Block Logging policy and channel state must both be verified; events cannot substitute for missing configuration evidence.",
                        ),
                    ),
                )
            elif all(
                name in observations and observations[name].state == "OBSERVED"
                for name in ("event_4104", "field_ScriptBlockText")
            ):
                decision = Decision(
                    "READY",
                    (
                        Issue(
                            "CAPABILITIES_VERIFIED",
                            "Machine logging and channel enabled; recent native 4104 plaintext ScriptBlockText observed.",
                        ),
                    ),
                )
            else:
                decision = Decision(
                    "PARTIAL",
                    (
                        Issue(
                            "OBSERVATION_INCOMPLETE",
                            "Logging and channel enabled, but recent usable ScriptBlockText telemetry is unverified. No recent event does not mean disabled logging.",
                        ),
                    ),
                )
    return Assessment(rule, requirements, evidence, profile.scope, profile.limitations, decision)
