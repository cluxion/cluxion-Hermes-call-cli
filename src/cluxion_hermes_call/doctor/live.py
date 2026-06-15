"""Live round-trip checks for doctor --live. Preserves the original live logic from old doctor.py."""

from __future__ import annotations

from cluxion_hermes_call.core import CallOptions, run_call
from cluxion_hermes_call.doctor.framework import CheckResult

LIVE_NO_TOOLS_PROMPT = (
    "List files in the current directory using your tools. If you have no tools, reply exactly NO_TOOLS."
)


def live_checks(ctx_or_timeout: object = 120.0) -> list[CheckResult]:
    """Perform the one tiny live --ask round-trip and return framework CheckResult list.

    Accepts float/int timeout_seconds or a DoctorContext-like object (uses .hermes_bin if present).
    """
    if isinstance(ctx_or_timeout, (int, float)):
        timeout_seconds = float(ctx_or_timeout)
        hermes_bin = "hermes"
    else:
        # support ctx_or_timeout with hermes_bin attr
        hermes_bin = getattr(ctx_or_timeout, "hermes_bin", "hermes")
        timeout_seconds = getattr(ctx_or_timeout, "timeout", 120.0)

    try:
        result = run_call(
            CallOptions(
                prompt=LIVE_NO_TOOLS_PROMPT,
                ask=True,
                sandbox=True,
                timeout_seconds=timeout_seconds,
                hermes_bin=hermes_bin,
            )
        )
    except Exception as exc:  # pragma: no cover - defensive
        detail = f"live call failed before returning: {type(exc).__name__}: {exc}"
        return [
            CheckResult(
                check_id="live_answer",
                category="live",
                severity="high",
                status="fail",
                detail=detail,
            ),
            CheckResult(
                check_id="live_no_tools",
                category="live",
                severity="high",
                status="fail",
                detail=detail,
            ),
            CheckResult(
                check_id="live_session_cleanup",
                category="live",
                severity="high",
                status="fail",
                detail=detail,
            ),
        ]

    answer = result.answer.strip()
    checks: list[CheckResult] = [
        CheckResult(
            check_id="live_answer",
            category="live",
            severity="high",
            status="pass" if result.ok and bool(answer) else "fail",
            detail=(
                "answer returned"
                if result.ok and answer
                else f"exit_code={result.exit_code} empty_answer={not bool(answer)}"
            ),
        ),
        CheckResult(
            check_id="live_no_tools",
            category="live",
            severity="high",
            status="pass" if "NO_TOOLS" in answer.upper() else "fail",
            detail=(
                "NO_TOOLS observed"
                if "NO_TOOLS" in answer.upper()
                else f"answer={answer[:100]!r}"
            ),
        ),
    ]
    cleanup_detail = result.session_id or result.session_cleanup_reason or "unknown"
    checks.append(
        CheckResult(
            check_id="live_session_cleanup",
            category="live",
            severity="high",
            status="pass" if result.session_cleaned else "fail",
            detail=f"deleted {cleanup_detail}" if result.session_cleaned else cleanup_detail,
        )
    )
    return checks
