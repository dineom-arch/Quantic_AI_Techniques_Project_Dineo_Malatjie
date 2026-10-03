from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from app.config import get_settings
from app.operational.repository import (
    OperationalDataError,
    OperationalRepository,
    get_operational_repository,
)


def test_all_controlled_operational_fixtures_load() -> None:
    repository = OperationalRepository(Path("mock_data/hr_operations"))
    assert len(repository.employees) == 8
    assert repository.pto("EMP-1007").available_days == 15
    assert repository.employee("EMP-1104").display_name == "Liam Chen"


def test_missing_operational_dependency_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(OperationalDataError, match="employees.json"):
        OperationalRepository(tmp_path)


def test_malformed_operational_dependency_is_explicit(tmp_path: Path) -> None:
    (tmp_path / "employees.json").write_text(json.dumps([{"employee_id": "broken"}]))
    with pytest.raises(OperationalDataError, match="employees.json"):
        OperationalRepository(tmp_path)


def _copy_operational_fixtures(destination_root: Path) -> Path:
    destination = destination_root / "hr_operations"
    shutil.copytree(Path("mock_data/hr_operations"), destination)
    return destination


def _set_available_days(directory: Path, available_days: int) -> None:
    path = directory / "pto_balances.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    records[0]["available_days"] = available_days
    path.write_text(json.dumps(records), encoding="utf-8")


def test_configured_repository_cache_is_isolated_by_canonical_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root_a = tmp_path / "fixture-a"
    root_b = tmp_path / "fixture-b"
    directory_a = _copy_operational_fixtures(root_a)
    directory_b = _copy_operational_fixtures(root_b)
    _set_available_days(directory_a, 101)
    _set_available_days(directory_b, 202)

    try:
        monkeypatch.setenv("MOCK_DATA_PATH", str(root_a))
        get_settings.cache_clear()
        repository_a = get_operational_repository()
        repository_a_again = get_operational_repository()
        assert repository_a_again is repository_a
        assert repository_a.pto("EMP-1007").available_days == 101

        monkeypatch.setenv("MOCK_DATA_PATH", str(root_b))
        get_settings.cache_clear()
        repository_b = get_operational_repository()
        assert repository_b is not repository_a
        assert repository_b.pto("EMP-1007").available_days == 202

        monkeypatch.setenv("MOCK_DATA_PATH", str(root_b / "."))
        get_settings.cache_clear()
        assert get_operational_repository() is repository_b
    finally:
        get_settings.cache_clear()
