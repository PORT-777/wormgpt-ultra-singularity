"""Regression tests for the agent's tool-parsing and skill-selection paths."""
from __future__ import annotations

import json

import configs as config
import skills
from agent_engine import AgentEngine
from tools.base import get_schema


# ---------------------------- Action parsing ---------------------------- #

def test_parse_action_nested_json_with_braces_in_string():
    text = ('Thought: ok\nAction: UniversalFileManager\n'
            'Action Input: {"action": "write", "path": "a.json", '
            '"content": "{\\"nested\\": 1}"}')
    tool, args = AgentEngine._parse_action(text)
    assert tool == "UniversalFileManager"
    assert args["content"] == '{"nested": 1}'
    assert args["action"] == "write"


def test_parse_action_ignores_trailing_prose():
    text = ('Action: MemoryLogicCalculator\n'
            'Action Input: {"op": "hex2dec", "value": "0x10"}\n'
            'Thought: done\nFinal Answer: 16')
    tool, args = AgentEngine._parse_action(text)
    assert tool == "MemoryLogicCalculator"
    assert args == {"op": "hex2dec", "value": "0x10"}


def test_parse_action_single_quotes():
    tool, args = AgentEngine._parse_action(
        "Action: MemoryLogicCalculator\nAction Input: {'op': 'hex2dec'}")
    assert tool == "MemoryLogicCalculator"
    assert args == {"op": "hex2dec"}


def test_parse_action_non_dict_json_is_wrapped():
    tool, args = AgentEngine._parse_action(
        'Action: WebSearch\nAction Input: ["query"]')
    assert args == {"model_input": ["query"]}


def test_parse_action_unclosed_json_falls_back():
    tool, args = AgentEngine._parse_action(
        "Action: PythonInterpreter\nAction Input: {'code': bad")
    assert tool == "PythonInterpreter"
    assert "model_input" in args


def test_get_schema_is_callable():
    class Dummy:
        name = "Dummy"
        description = "test"
        example = {"x": 1}

    assert "Dummy" in get_schema(Dummy())  # type: ignore[arg-type]


# -------------------------- Skill relevance ----------------------------- #

def test_word_boundary_stops_substring_match():
    assert skills._trigger_score("rewrite the file", ["write"]) == 0.0
    assert skills._trigger_score("write the file", ["write"]) > 0.0


def test_generic_trigger_is_weaker_than_specific():
    task = "build a tool for pe header parsing"
    generic = skills._trigger_score(task, ["tool"])
    specific = skills._trigger_score(task, ["pe header parsing"])
    assert generic < specific


def test_phrase_trigger_matches_contiguously():
    assert skills._trigger_score("derive struct layout and offsets",
                                 ["struct layout"]) > 0.0
    assert skills._trigger_score("derive offsets then struct",
                                 ["struct layout"]) == 0.0


def test_greeting_pulls_no_auto_pack(monkeypatch):
    monkeypatch.setattr(config, "MAX_SKILL_PACKS", 4)
    names = [p["name"] for p in skills.relevant_packs("hello there")]
    assert "offset_forensics_playbook" not in names


def test_specific_playbook_still_wins(monkeypatch):
    monkeypatch.setattr(config, "MAX_SKILL_PACKS", 4)
    names = [p["name"] for p in skills.relevant_packs(
        "derive struct layout and offsets for a binary")]
    assert "offset_forensics_playbook" in names
