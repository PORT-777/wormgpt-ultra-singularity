"""Tests for the gap-feature batch: context windows + vision helpers."""
from __future__ import annotations

from model_context import context_window_for, estimate_tokens, trim_messages
from vision_service import is_image


def test_context_window_detection():
    assert context_window_for("nvidia/nemotron-3.5-super-vl:free") == 1000000
    assert context_window_for("sonnet4.6-500k") == 500000
    assert context_window_for("google/gemma-4-31b-it:free") == 262144
    assert context_window_for("openai/gpt-oss-120b") == 131072
    assert context_window_for("mystery-model-xyz") == 32768
    assert context_window_for("") == 32768


def test_trim_messages_keeps_system_and_drops_oldest():
    msgs = [{"role": "system", "content": "s"}]
    msgs += [{"role": "user", "content": "x" * 20000} for _ in range(20)]
    kept, info = trim_messages(msgs, 8192)
    assert info["trimmed"] is True
    assert info["dropped"] > 0
    assert kept[0]["role"] == "system"
    # min_keep=2 is intentional: never drop the current goal, even if it
    # alone exceeds the budget.
    assert len(kept) == 3
    assert estimate_tokens(kept) < 20 * 5000


def test_trim_messages_noop_when_small():
    msgs = [{"role": "system", "content": "s"},
            {"role": "user", "content": "hello"}]
    kept, info = trim_messages(msgs, 200000)
    assert info["trimmed"] is False
    assert kept == msgs


def test_vision_is_image(tmp_path):
    png = tmp_path / "a.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    txt = tmp_path / "a.txt"
    txt.write_text("hi", encoding="utf-8")
    assert is_image(png) is True
    assert is_image(txt) is False