from pathlib import Path

import pytest


@pytest.fixture
def rule_text() -> str:
    return (Path(__file__).parents[1] / "examples" / "powershell_script.yml").read_text(
        encoding="utf-8"
    )


@pytest.fixture
def rule_path(tmp_path: Path, rule_text: str) -> Path:
    path = tmp_path / "rule.yml"
    path.write_text(rule_text, encoding="utf-8")
    return path
