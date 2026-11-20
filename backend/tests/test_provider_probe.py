"""Tests for provider_probe."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import provider_probe


def test_probe_bad_url():
    r = provider_probe.probe("http://127.0.0.1:1/", timeout=1.0)
    assert r["ok"] is False
    assert "latency_ms" in r


def test_probe_many():
    r = provider_probe.probe_many({"a": "http://127.0.0.1:1/"})
    assert "a" in r
    assert r["a"]["ok"] is False
