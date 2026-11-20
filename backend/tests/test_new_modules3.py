"""Tests for latest modules."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import structured_output, response_cache, auto_backup, safety_filter
import summarize, event_bus, tool_exec_log, users, presence, diffs
import data_analysis, webhooks, backup, chat_export


def test_safety_filter():
    safety_filter.add_pattern(r"secret")
    r = safety_filter.check("this is a secret msg")
    assert r["flagged"] is True
    assert "secret" in safety_filter.redact("this is a secret msg").lower() or "REDACTED" in safety_filter.redact("this is a secret msg")


def test_summarize():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    s = summarize.extractive(text, 2)
    assert isinstance(s, str) and len(s) > 0
    b = summarize.bullet_points(text, 3)
    assert len(b) == 3


def test_event_bus2():
    captured = []
    event_bus.subscribe("e2", lambda p: captured.append(p))
    n = event_bus.publish("e2", {"a": 1})
    assert n >= 1 and captured[0]["a"] == 1


def test_auto_backup():
    import tempfile, os
    d = tempfile.mkdtemp()
    path = auto_backup.maybe_backup(backup_dir=d, force=True)
    assert path is not None and os.path.exists(path)
