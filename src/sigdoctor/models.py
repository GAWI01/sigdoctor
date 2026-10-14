from dataclasses import dataclass
from typing import Literal

Status = Literal["READY", "PARTIAL", "BLIND", "UNKNOWN"]
State = Literal[
    "ENABLED", "DISABLED", "OBSERVED", "NOT_OBSERVED", "UNKNOWN", "ERROR", "UNSUPPORTED"
]


class ToolError(Exception):
    def __init__(self, code: str, message: str, exit_code: int = 2):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


@dataclass(frozen=True)
class Issue:
    code: str
    message: str


@dataclass(frozen=True)
class RuleRequirements:
    id: str | None
    title: str
    product: str | None
    category: str | None
    service: str | None
    definition: str | None
    required_fields: tuple[str, ...]
    display_fields: tuple[str, ...]
    tags: tuple[str, ...]
    mitre_techniques: tuple[str, ...]
    event_ids: tuple[int, ...]
    sha256: str
    issues: tuple[Issue, ...]


@dataclass(frozen=True)
class Evidence:
    capability: str
    state: State
    source: str
    observed_at: str
    details: dict[str, str | int | bool | None]
    error_code: str | None = None


@dataclass(frozen=True)
class Requirement:
    capability: str
    provenance: Literal["DIRECT", "DERIVED"]
    reason: str


@dataclass(frozen=True)
class TelemetryProfile:
    id: str
    scope: str
    product: str
    category: str
    service: str
    channel: str
    provider: str
    event_id: int
    fields: tuple[str, ...]
    capabilities: tuple[str, ...]
    references: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    status: Status
    reasons: tuple[Issue, ...]


@dataclass(frozen=True)
class Assessment:
    rule: RuleRequirements
    requirements: tuple[Requirement, ...]
    evidence: tuple[Evidence, ...]
    scope: str
    limitations: tuple[str, ...]
    result: Decision
    schema_version: str = "1"
