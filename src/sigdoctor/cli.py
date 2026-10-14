import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn

from sigdoctor import __version__
from sigdoctor.models import ToolError
from sigdoctor.output import render_json, render_terminal
from sigdoctor.workflow import check_rule


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ToolError(
            "INVALID_ARGUMENT",
            "Invalid arguments. Use sigdoctor check <rule.yml> [--json] or sigdoctor --help.",
        )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    machine = "--json" in args
    parser = Parser(
        prog="sigdoctor",
        description="Read-only local telemetry checks for supported Windows PowerShell Sigma rules.",
    )
    parser.add_argument("--version", action="version", version=f"sigdoctor {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser(
        "check", help="Assess one rule against local Windows PowerShell telemetry"
    )
    check.add_argument("rule", type=Path)
    check.add_argument("--json", action="store_true", help="Emit schema-versioned JSON")
    try:
        options = parser.parse_args(args)
        assessment = check_rule(options.rule)
        print(render_json(assessment) if machine else render_terminal(assessment))
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    except ToolError as exc:
        error = exc
    except Exception:
        error = ToolError(
            "INTERNAL_ERROR",
            "SigDoctor could not complete the check. Report the tool version and a sanitized reproduction.",
            1,
        )
    if machine:
        print(
            json.dumps(
                {"schema_version": "1", "error": {"code": error.code, "message": error.message}},
                ensure_ascii=True,
            )
        )
    else:
        print(f"{error.code}: {error.message}", file=sys.stderr)
    return error.exit_code
