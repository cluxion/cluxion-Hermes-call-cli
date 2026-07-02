from __future__ import annotations

from cluxion_hermes_call.core import (
    TASK_COMPLETE_MARKER,
    _parse_completion_marker,
    _same_remaining_work,
    _strip_completion_marker,
)


def test_marker_tolerates_case_and_whitespace() -> None:
    assert _parse_completion_marker("done\n  task_complete  ") == TASK_COMPLETE_MARKER
    assert _parse_completion_marker("done\nTask_Complete") == TASK_COMPLETE_MARKER
    marker = _parse_completion_marker("step\n work_remains:   fix tests ")
    assert marker == "WORK_REMAINS: fix tests"


def test_strip_removes_marker_variants() -> None:
    text = "answer body\n task_complete \nWORK_remains: leftover"
    assert _strip_completion_marker(text) == "answer body"


def test_same_remaining_work_detects_rephrased_blocker() -> None:
    assert _same_remaining_work("fix the parser bug", "fix the parser bug")
    assert _same_remaining_work("Fix the parser bug.", "fix the parser bug")
    assert not _same_remaining_work("write docs", "fix the parser bug")
    assert not _same_remaining_work("anything", None)
