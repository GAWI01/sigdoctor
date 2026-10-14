"""Bounded YAML and pySigma boundary; no third-party objects escape this module."""

import hashlib
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

import yaml
from sigma.conditions import (
    ConditionAND,
    ConditionFieldEqualsValueExpression,
    ConditionNOT,
    ConditionOR,
)
from sigma.exceptions import SigmaError
from sigma.modifiers import modifier_mapping
from sigma.rule import SigmaRule
from sigma.types import SigmaNumber, SigmaString

from sigdoctor.models import Issue, RuleRequirements, ToolError

MAX_INPUT = 256 * 1024


class StrictLoader(yaml.SafeLoader):
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        keys: set[str] = set()
        for key, _ in node.value:
            if not isinstance(key, yaml.ScalarNode) or key.tag != "tag:yaml.org,2002:str":
                raise ValueError("Mapping keys must be strings")
            if key.value in keys:
                raise ValueError("Duplicate mapping key")
            keys.add(key.value)
        return super().construct_mapping(node, deep=deep)


def _yaml_document(text: str) -> dict[str, Any]:
    depth = 0
    for count, event in enumerate(yaml.parse(text)):
        if count > 4096:
            raise ValueError("Too many YAML nodes")
        if (
            isinstance(event, yaml.AliasEvent)
            or getattr(event, "anchor", None)
            or getattr(event, "tag", None)
        ):
            raise ValueError("YAML aliases, anchors and explicit tags are not supported")
        if isinstance(event, (yaml.SequenceStartEvent, yaml.MappingStartEvent)):
            depth += 1
            if depth > 24:
                raise ValueError("YAML nesting limit")
        if isinstance(event, (yaml.SequenceEndEvent, yaml.MappingEndEvent)):
            depth -= 1
    data = yaml.load(text, Loader=StrictLoader)  # noqa: S506 -- SafeLoader subclass
    if not isinstance(data, dict):
        raise ValueError("Expected one rule mapping")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ValueError("Rule title must be a non-empty string")
    logsource = data.get("logsource")
    if not isinstance(logsource, dict) or not logsource:
        raise ValueError("Missing logsource")
    for key in ("product", "category", "service", "definition"):
        if key in logsource and not isinstance(logsource[key], str):
            raise ValueError("Invalid logsource attribute")
    for key in ("fields", "tags"):
        if key in data and (
            not isinstance(data[key], list) or any(not isinstance(x, str) for x in data[key])
        ):
            raise ValueError("Invalid list attribute")
    detection = data.get("detection")
    if not isinstance(detection, dict) or len(detection) > 64:
        raise ValueError("Missing or oversized detection")
    conditions = detection.get("condition")
    if isinstance(conditions, str):
        conditions = [conditions]
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= 8:
        raise ValueError("Invalid condition")
    for condition in conditions:
        if not isinstance(condition, str) or len(condition) > 512 or len(condition.split()) > 64:
            raise ValueError("Condition complexity limit")
        if condition.count("(") > 16:
            raise ValueError("Condition nesting limit")
    return data


def _active_requirements(
    rule: SigmaRule,
) -> tuple[tuple[str, ...], tuple[int, ...], tuple[Issue, ...]]:
    fields: set[str] = set()
    event_ids: set[int] = set()
    issues: set[str] = set()
    nodes = 0

    def visit(node: Any, event_conjunction: bool = True, depth: int = 0) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > 4096 or depth > 64:
            raise ValueError("Resolved condition complexity limit")
        if isinstance(node, (ConditionAND, ConditionOR, ConditionNOT)):
            for arg in node.args:
                visit(arg, event_conjunction and isinstance(node, ConditionAND), depth + 1)
        elif isinstance(node, ConditionFieldEqualsValueExpression):
            fields.add(node.field)
            if node.field == "EventID":
                if isinstance(node.value, SigmaNumber):
                    value = node.value.number
                    if isinstance(value, int):
                        event_ids.add(value)
                elif isinstance(node.value, SigmaString) and str(node.value).isdigit():
                    event_ids.add(int(str(node.value)))
                if not event_conjunction or str(node.value) != "4104":
                    issues.add("Only positive conjunctive EventID 4104 is supported")
            elif not isinstance(node.value, SigmaString):
                issues.add("Only native string field predicates are supported")
        else:
            issues.add("Unbound keywords or unsupported condition semantics")

    if len(rule.detection.parsed_condition) != 1:
        issues.add("Multiple condition alternatives are not supported")
    for condition in rule.detection.parsed_condition:
        visit(condition.parsed)
    return (
        tuple(sorted(fields)),
        tuple(sorted(event_ids)),
        tuple(Issue("UNSUPPORTED_SEMANTICS", message) for message in sorted(issues)),
    )


def _unsupported_modifiers(value: Any) -> bool:
    """Inspect keys BEFORE pySigma eagerly applies potentially expanding modifiers.

    All selectors are checked, including unused ones. This intentionally declines
    the whole rule rather than applying transformations to find the active tree.
    """
    unsupported = False
    if isinstance(value, dict):
        for key, child in value.items():
            modifiers = key.split("|")[1:]
            if any(modifier not in modifier_mapping for modifier in modifiers):
                raise ValueError("Unknown Sigma modifier")
            if len(modifiers) > 4 or any(
                modifier not in {"contains", "startswith", "endswith", "all"}
                for modifier in modifiers
            ):
                unsupported = True
            unsupported = _unsupported_modifiers(child) or unsupported
    elif isinstance(value, list):
        for child in value:
            unsupported = _unsupported_modifiers(child) or unsupported
    return unsupported


def _mitre(tags: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        tag.removeprefix("attack.").upper()
        for tag in tags
        if re.fullmatch(r"attack\.t\d{4}(?:\.\d{3})?", tag)
    )


def _drive_type(root: str) -> int:
    if sys.platform != "win32":
        return 3
    import ctypes
    from ctypes import wintypes

    get_drive_type = ctypes.WinDLL("kernel32", use_last_error=True).GetDriveTypeW
    get_drive_type.argtypes = [wintypes.LPCWSTR]
    get_drive_type.restype = wintypes.UINT
    return int(get_drive_type(root))


def _local_file(path: Path) -> Path:
    # abspath is lexical. resolve() could follow remote reparse targets.
    if str(path).startswith(("\\\\", "//")):
        raise ValueError("Remote and device paths are not supported")
    absolute = Path(os.path.abspath(path))
    if str(absolute).startswith(("\\\\", "//")) or _drive_type(absolute.anchor) not in (2, 3, 5, 6):
        raise ValueError("Input must be on a local drive")
    # Inspect from the root down, so no child lookup follows an unchecked link.
    for component in (*reversed(absolute.parents), absolute):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Symlinks, junctions and other reparse points are unsupported")
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Input must be a regular file")
    return absolute


def load_rule(path: Path) -> RuleRequirements:
    try:
        local_path = _local_file(path)
        with local_path.open("rb") as handle:
            raw = handle.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("Rule exceeds 256 KiB")
        data = _yaml_document(raw.decode("utf-8-sig"))
        digest = hashlib.sha256(raw).hexdigest()
        if _unsupported_modifiers(data["detection"]):
            # Preserve metadata without claiming that Sigma validation completed.
            logsource = data["logsource"]
            tags = tuple(data.get("tags", []))
            return RuleRequirements(
                str(data["id"]) if data.get("id") is not None else None,
                data["title"],
                logsource.get("product"),
                logsource.get("category"),
                logsource.get("service"),
                logsource.get("definition"),
                (),
                tuple(data.get("fields", [])),
                tags,
                _mitre(tags),
                (),
                digest,
                (
                    Issue(
                        "UNSUPPORTED_SEMANTICS",
                        "Unsupported modifier or modifier-chain limit. Sigma validation was not completed; transformations were rejected before expansion, including in unused selectors.",
                    ),
                ),
            )
        rule = SigmaRule.from_dict(data)
        fields, events, issues = _active_requirements(rule)
        tags = tuple(str(tag) for tag in rule.tags)
        return RuleRequirements(
            str(rule.id) if rule.id else None,
            rule.title,
            rule.logsource.product,
            rule.logsource.category,
            rule.logsource.service,
            rule.logsource.definition,
            fields,
            tuple(rule.fields),
            tags,
            _mitre(tags),
            events,
            digest,
            issues,
        )
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RecursionError,
        yaml.YAMLError,
        SigmaError,
    ) as exc:
        # Exception strings can include rule contents or local paths. Do not echo them.
        raise ToolError(
            "RULE_PARSE_ERROR",
            "Cannot read or parse one bounded UTF-8 Sigma rule. Check its path, YAML, logsource and detection condition.",
        ) from exc
