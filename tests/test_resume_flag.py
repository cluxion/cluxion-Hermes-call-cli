from __future__ import annotations

from cluxion_hermes_call.core import CallOptions, _build_hermes_command


def test_resume_command_uses_chat_resume_with_model() -> None:
    options = CallOptions(prompt="continue", model="grok-4.3", resume_session=None)
    command = _build_hermes_command(options, resume_session_id="20260702_abc")
    assert command[:5] == ["hermes", "chat", "-Q", "--resume", "20260702_abc"]
    assert "-m" in command and "grok-4.3" in command
    assert command[-1] == "continue"


def test_resume_session_skips_gc(monkeypatch) -> None:
    from cluxion_hermes_call import core

    calls = {"snapshot": 0}

    def _snap(**kwargs: object) -> object:
        calls["snapshot"] += 1
        return core.SessionSnapshot(ids=frozenset(), ok=True)

    monkeypatch.setattr(core, "capture_session_ids", _snap)
    monkeypatch.setattr(
        core,
        "_run_hermes_process",
        lambda options, *, cwd, resume_session_id=None: core.HermesProcessResult(
            stdout="done", stderr="", returncode=0, timed_out=False
        ),
    )
    result = core.run_call(CallOptions(prompt="hi", resume_session="20260702_abc"))
    assert calls["snapshot"] == 0
    assert result.session_cleanup_reason == "resumed_session"
