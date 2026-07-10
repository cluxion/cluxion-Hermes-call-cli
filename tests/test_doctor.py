"""Tests for doctor probes."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cluxion_hermes_call.doctor.framework import DoctorContext, run_doctor
from cluxion_hermes_call.doctor.probes import (
    PROBES,
    hermes_help_flags_missing,
    hermes_oneshot_flag,
    hermes_version,
)

CATALOG_PATH = Path(__file__).parent.parent / "src" / "cluxion_hermes_call" / "doctor" / "catalog.json"
REALISTIC_VERSION = "Hermes Agent v0.16.0 (2026.6.5)\n"
REALISTIC_HELP = "-z PROMPT, --oneshot PROMPT\n-t TOOLSETS, --toolsets TOOLSETS\n"


def _completed(command: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def _realistic_runner(
    overrides: dict[tuple[str, ...], subprocess.CompletedProcess[str]] | None = None,
):
    responses = {
        ("hermes", "--version"): _completed(["hermes", "--version"], stdout=REALISTIC_VERSION),
        ("hermes", "--help"): _completed(["hermes", "--help"], stdout=REALISTIC_HELP),
    }
    responses.update(overrides or {})

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return responses.get(tuple(command), _completed(command, 99, stderr=f"unexpected: {command!r}"))

    return runner


def test_new_probes_registered_and_non_skip():
    # run doctor (our new probes do not need runner)
    result = run_doctor(
        cwd=Path.cwd(),
        hermes_bin="hermes",
        catalog_path=CATALOG_PATH,
        probes=PROBES,
        plugin="hermes-call",
        version="0.3.2",
    )
    check_map = {c.check_id: c for c in result.checks}
    # assert our two new probes return non-skip
    p1 = check_map.get("python_version_incompatibility")
    assert p1 is not None
    assert p1.status in ("pass", "warn")  # non-skip
    p2 = check_map.get("json_mode_output_malformed")
    assert p2 is not None
    assert p2.status in ("pass", "warn", "fail")  # non-skip
    # determinism of json output
    j1 = json.dumps(result.to_json_object(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    j2 = json.dumps(result.to_json_object(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert j1 == j2


def test_contract_probes_are_registered_or_removed():
    result = run_doctor(
        cwd=Path.cwd(),
        hermes_bin="hermes",
        catalog_path=CATALOG_PATH,
        probes=PROBES,
        plugin="hermes-call",
        version="0.3.11",
    )
    check_map = {c.check_id: c for c in result.checks}
    assert [c.check_id for c in result.checks if c.severity == "critical" and c.status == "skip"] == []

    for check_id in (
        "session_cleanup_race_condition",
        "subprocess_timeout_not_enforced",
        "process_group_termination_fails",
        "sessions_list_parse_failure",
        "hermes_command_flag_incompatible",
        "model_argument_invalid",
        "jobs_root_not_writable",
    ):
        assert check_map[check_id].status != "skip"


def test_session_cleanup_race_condition_passes_against_current_sessions():
    result = run_doctor(
        cwd=Path.cwd(),
        hermes_bin="hermes",
        catalog_path=CATALOG_PATH,
        probes=PROBES,
        plugin="hermes-call",
        version="0.3.11",
    )
    check = {c.check_id: c for c in result.checks}["session_cleanup_race_condition"]
    assert check.status == "pass", check.detail
    assert "unambiguous" in check.detail


def test_hermes_version_live_exec_rejects_true_accepts_fixture():
    true_ctx = DoctorContext(
        cwd=Path.cwd(),
        hermes_bin="/usr/bin/true",
        run=lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL),
    )
    status, detail = hermes_version(true_ctx)
    assert status == "fail", detail

    fixture_ctx = DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=_realistic_runner())
    status, detail = hermes_version(fixture_ctx)
    assert status == "pass", detail
    assert "Hermes Agent v0.16.0" in detail


def test_hermes_oneshot_flag_live_help_rejects_stub_accepts_fixture():
    stub = _realistic_runner(
        {
            ("hermes", "--help"): _completed(
                ["hermes", "--help"],
                stdout="usage: hermes [options]\n  --profile PROFILE\n",
            )
        }
    )
    stub_ctx = DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=stub)
    status, detail = hermes_oneshot_flag(stub_ctx)
    assert status == "fail", detail

    fixture_ctx = DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=_realistic_runner())
    status, detail = hermes_oneshot_flag(fixture_ctx)
    assert status == "pass", detail


def test_hermes_help_flags_missing_live_help_requires_toolsets_too():
    no_toolsets = _realistic_runner(
        {
            ("hermes", "--help"): _completed(
                ["hermes", "--help"],
                stdout="-z PROMPT, --oneshot PROMPT\n",
            )
        }
    )
    ctx = DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=no_toolsets)
    status, detail = hermes_help_flags_missing(ctx)
    assert status == "fail", detail

    fixture_ctx = DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=_realistic_runner())
    status, detail = hermes_help_flags_missing(fixture_ctx)
    assert status == "pass", detail


def test_hermes_oneshot_flag_rejects_zero_copy_substring_false_positive():
    """--zero-copy must not satisfy short -z (raw substring false positive)."""
    zero_copy = _realistic_runner(
        {
            ("hermes", "--help"): _completed(
                ["hermes", "--help"],
                stdout="usage: hermes [options]\n  --zero-copy\n  --oneshot PROMPT\n",
            )
        }
    )
    ctx = DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=zero_copy)
    status, detail = hermes_oneshot_flag(ctx)
    assert status == "fail", detail
    assert "-z" in detail


def test_hermes_help_flags_missing_rejects_toolsets_substring_for_short_t():
    """--toolsets must not satisfy short -t (raw substring false positive)."""
    long_only = _realistic_runner(
        {
            ("hermes", "--help"): _completed(
                ["hermes", "--help"],
                stdout="-z PROMPT, --oneshot PROMPT\n--toolsets TOOLSETS\n",
            )
        }
    )
    ctx = DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=long_only)
    status, detail = hermes_help_flags_missing(ctx)
    assert status == "fail", detail
    assert "-t" in detail


def test_missing_flags_accepts_argparse_option_token_forms():
    from cluxion_hermes_call.doctor.probes import _missing_flags

    # whitespace / comma / equals forms are real help tokens
    assert _missing_flags("-z PROMPT, --oneshot PROMPT\n", ("-z", "--oneshot")) == []
    assert _missing_flags("-t=TOOLS, --toolsets=TOOLS\n", ("-t", "--toolsets")) == []
    assert _missing_flags("  -z, --oneshot\n", ("-z", "--oneshot")) == []
    # substrings of longer options are not tokens
    assert _missing_flags("--zero-copy\n--oneshot\n", ("-z", "--oneshot")) == ["-z"]
    assert _missing_flags("-z --oneshot\n--toolsets\n", ("-z", "--oneshot", "-t", "--toolsets")) == ["-t"]


def test_hermes_version_rejects_non_numeric_suffix_and_accepts_dotted():
    banana = _realistic_runner(
        {
            ("hermes", "--version"): _completed(
                ["hermes", "--version"],
                stdout="Hermes Agent vbanana\n",
            )
        }
    )
    status, detail = hermes_version(DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=banana))
    assert status == "fail", detail
    assert "unparseable" in detail

    fixture_ctx = DoctorContext(cwd=Path.cwd(), hermes_bin="hermes", run=_realistic_runner())
    status, detail = hermes_version(fixture_ctx)
    assert status == "pass", detail
    assert detail == "Hermes Agent v0.16.0"
