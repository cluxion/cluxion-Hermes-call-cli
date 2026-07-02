from __future__ import annotations

from pathlib import Path

import pytest

from cluxion_hermes_call import jobs


def test_env_override_wins(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(jobs.HOME_ENV, str(tmp_path / "custom"))
    root = jobs.resolve_jobs_root()
    assert root == tmp_path / "custom" / "jobs"
    assert root.is_dir()


def test_falls_back_to_workspace_when_home_unwritable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(jobs.HOME_ENV, raising=False)
    monkeypatch.setattr(jobs, "DEFAULT_JOBS_ROOT", Path("/dev/null/impossible/jobs"))
    monkeypatch.chdir(tmp_path)
    root = jobs.resolve_jobs_root()
    assert root == tmp_path / ".hermes-call" / "jobs"


def test_raises_typed_error_with_hint_when_nothing_writable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(jobs.HOME_ENV, "/dev/null/impossible")
    with pytest.raises(jobs.JobRootUnwritableError) as exc:
        jobs.resolve_jobs_root()
    assert jobs.HOME_ENV in exc.value.hint
