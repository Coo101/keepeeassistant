"""pyproject.toml is the one place for dependencies; the requirements files are
generated from it for Docker and CI (see README)."""

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _pins(lines: list[str]) -> set[str]:
    return {line.split(";")[0].strip().lower() for line in lines}


@pytest.mark.parametrize(
    ("declared", "generated"),
    [
        (PYPROJECT["project"]["dependencies"], "requirements.txt"),
        (PYPROJECT["dependency-groups"]["dev"], "requirements-dev.txt"),
    ],
)
def test_requirements_match_pyproject(declared: list[str], generated: str) -> None:
    assert all("==" in dependency for dependency in declared)
    lines = (ROOT / generated).read_text(encoding="utf-8").splitlines()
    assert _pins(declared) <= _pins(lines)
