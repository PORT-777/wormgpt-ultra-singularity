"""Tests for structured_output and response_cache."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import structured_output, response_cache


def test_structured_valid():
    schema = {"type": "object", "required": ["name", "age"],
              "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}
    r = structured_output.validate({"name": "a", "age": 5}, schema)
    assert r["valid"] is True


def test_structured_invalid():
    schema = {"type": "object", "required": ["name"],
              "properties": {"name": {"type": "string"}}}
    r = structured_output.validate({"name": 5}, schema)
    assert r["valid"] is False
    r2 = structured_output.validate({}, schema)
    assert r2["valid"] is False


def test_structured_parse():
    schema = {"type": "array", "items": {"type": "number"}}
    r = structured_output.parse_and_validate("[1,2,3]", schema)
    assert r["valid"] is True and r["data"] == [1, 2, 3]
    r2 = structured_output.parse_and_validate("not json", schema)
    assert r2["valid"] is False


def test_response_cache():
    k = response_cache.key_for([{"role": "user", "content": "hi"}], "m")
    response_cache.set(k, "val", ttl=10)
    assert response_cache.get(k) == "val"
    assert response_cache.invalidate(k) is True
    assert response_cache.get(k) is None
    response_cache.set(k, "v2", ttl=10)
    assert response_cache.clear() >= 1
    assert response_cache.stats()["entries"] == 0
