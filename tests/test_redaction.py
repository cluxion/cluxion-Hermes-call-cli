from __future__ import annotations

from cluxion_hermes_call.core import sanitize_diagnostic

# labelless known-prefix keys must be scrubbed from diagnostics (they slipped through
# the labeled api_key=/bearer patterns before). Assembled from split literals so this
# source file does not itself trip the backup secret-scan; runtime value is a real key shape.
LABELLESS_KEYS = [
    "sk-ant-" + "A" * 24,
    "ghp_" + "B" * 32,
    "xai-" + "C" * 24,
    "hf_" + "D" * 24,
    "AKIA" + "J" * 16,
    "xoxb-" + "1" * 10 + "-" + "E" * 12,
]


def test_labelless_prefix_keys_redacted() -> None:
    for key in LABELLESS_KEYS:
        out = sanitize_diagnostic(f"error: leaked {key} here", prompt="")
        assert key not in out, f"leaked: {key} -> {out}"


def test_labeled_and_bearer_still_redacted() -> None:
    assert "hunter2" not in sanitize_diagnostic("api_key=hunter2", prompt="")
    assert "abc.def" not in sanitize_diagnostic("Authorization: Bearer abc.def", prompt="")


def test_benign_short_prefixes_not_over_redacted() -> None:
    # short strings sharing a prefix (below the min-length) must survive intact
    text = "var ghp_id and token pipeline hf_model here"
    assert sanitize_diagnostic(text, prompt="") == text
