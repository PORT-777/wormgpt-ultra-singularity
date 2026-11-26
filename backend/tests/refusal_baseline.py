"""Run the refusal corpus against the engine currently on disk.

Standalone harness (no pytest, no network, no API keys):

    cd backend
    python tests/refusal_baseline.py                 # strict: exit 1 on any mismatch
    python tests/refusal_baseline.py --no-strict     # record-only: always exit 0

It writes a JSON report (default ``tests/refusal_baseline_report.json``) with
the observed per-case results, the raw refusal-positive rate and the exit code
actually returned by this process. "Rate" here means the fraction of the
labeled corpus that the current classifier flags as a refusal - not a claim
about any live model's refusal behaviour.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

import agent_engine  # noqa: E402
from refusal_corpus import CORPUS, counts  # noqa: E402


def classify(text: str):
    """Return (is_refusal, rule_name). Tolerates older builds without rule names."""
    rule = getattr(agent_engine, "refusal_rule", None)
    if callable(rule):
        name = rule(text)
        return bool(name), name or None
    match = agent_engine._REFUSAL_RE.search(text)
    return bool(match), match.lastgroup if match else None


def evaluate() -> dict:
    tp = fp = tn = fn = 0
    results = []
    for case in CORPUS:
        predicted, rule = classify(case.text)
        correct = predicted == case.expected_refusal
        if case.expected_refusal:
            tp += int(predicted)
            fn += int(not predicted)
        else:
            fp += int(predicted)
            tn += int(not predicted)
        results.append({
            "id": case.id,
            "expected": "refusal" if case.expected_refusal else "non_refusal",
            "predicted": "refusal" if predicted else "non_refusal",
            "rule": rule,
            "correct": correct,
            "note": case.note,
        })

    total = len(CORPUS)
    n_ref = counts()["refusal"]
    n_non = counts()["non_refusal"]
    accuracy = (tp + tn) / total if total else 0.0
    return {
        "counts": {
            "total": total,
            "labeled_refusal": n_ref,
            "labeled_non_refusal": n_non,
            "true_positive": tp,
            "false_positive": fp,
            "true_negative": tn,
            "false_negative": fn,
        },
        "rates": {
            "refusal_positive_rate": round(
                (tp + fp) / total, 4) if total else 0.0,
            "accuracy": round(accuracy, 4),
            "false_positive_rate": round(fp / n_non, 4) if n_non else 0.0,
            "false_negative_rate": round(fn / n_ref, 4) if n_ref else 0.0,
        },
        "mismatches": [r for r in results if not r["correct"]],
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(_HERE / "refusal_baseline_report.json"),
                        help="path for the JSON report")
    parser.add_argument("--no-strict", action="store_true",
                        help="always exit 0 (record-only baseline)")
    args = parser.parse_args(argv)

    report = evaluate()
    strict_rc = 0 if not report["mismatches"] else 1
    rc = 0 if args.no_strict else strict_rc

    report["meta"] = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "strict": not args.no_strict,
        "exit_code": rc,
        "strict_exit_code": strict_rc,
        "regex_pattern": getattr(agent_engine, "_REFUSAL_RE").pattern[:500],
    }

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    c = report["counts"]
    r = report["rates"]
    print(f"corpus={c['total']} refusal={c['labeled_refusal']} "
          f"non_refusal={c['labeled_non_refusal']}")
    print(f"TP={c['true_positive']} FP={c['false_positive']} "
          f"TN={c['true_negative']} FN={c['false_negative']}")
    print(f"refusal_positive_rate={r['refusal_positive_rate']:.4f} "
          f"accuracy={r['accuracy']:.4f} "
          f"FPR={r['false_positive_rate']:.4f} FNR={r['false_negative_rate']:.4f}")
    for m in report["mismatches"]:
        print(f"  MISMATCH {m['id']}: expected={m['expected']} "
              f"predicted={m['predicted']} rule={m['rule']}")
    print(f"report={out}")
    print(f"exit_code={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
