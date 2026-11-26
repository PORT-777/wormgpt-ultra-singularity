"""Regression tests for the refusal classifier (refusal + non-refusal cases)."""
from __future__ import annotations

import json

import pytest

import agent_engine
from refusal_corpus import (CORPUS, EXPECTED_COUNTS, NON_REFUSAL_CASES,
                            REFUSAL_CASES, counts)
from refusal_baseline import evaluate, main as baseline_main


@pytest.mark.parametrize("case", CORPUS, ids=[c.id for c in CORPUS])
def test_corpus_case(case):
    assert agent_engine.classify_refusal(case.text) is case.expected_refusal, (
        f"{case.id}: {case.note}"
    )


@pytest.mark.parametrize("case", REFUSAL_CASES, ids=[c.id for c in REFUSAL_CASES])
def test_refusal_rule_names_a_real_rule(case):
    rule = agent_engine.refusal_rule(case.text)
    assert rule in agent_engine._REFUSAL_PATTERNS


@pytest.mark.parametrize("case", NON_REFUSAL_CASES,
                         ids=[c.id for c in NON_REFUSAL_CASES])
def test_non_refusal_has_no_rule(case):
    assert agent_engine.refusal_rule(case.text) is None


def test_corpus_shape():
    assert counts() == EXPECTED_COUNTS
    assert len({c.id for c in CORPUS}) == len(CORPUS)


def test_evaluate_is_clean():
    report = evaluate()
    assert report["counts"]["false_positive"] == 0
    assert report["counts"]["false_negative"] == 0
    assert report["rates"]["accuracy"] == 1.0
    assert report["mismatches"] == []


def test_empty_text_is_not_a_refusal():
    assert agent_engine.classify_refusal("") is False
    assert agent_engine.refusal_rule(None) is None


def test_baseline_writes_json_report(tmp_path):
    out = tmp_path / "report.json"
    rc = baseline_main(["--json", str(out)])
    assert rc == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["meta"]["exit_code"] == 0
    assert report["counts"]["total"] == len(CORPUS)
