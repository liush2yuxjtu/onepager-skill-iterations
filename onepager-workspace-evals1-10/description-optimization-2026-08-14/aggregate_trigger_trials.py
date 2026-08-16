#!/usr/bin/env python3
"""Aggregate three independent description-trigger routing trials."""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path


def split_queries(items: list[dict], holdout: float = 0.4, seed: int = 42):
    random.seed(seed)
    positive = [item for item in items if item["should_trigger"]]
    negative = [item for item in items if not item["should_trigger"]]
    random.shuffle(positive)
    random.shuffle(negative)
    pos_n = max(1, int(len(positive) * holdout))
    neg_n = max(1, int(len(negative) * holdout))
    test = positive[:pos_n] + negative[:neg_n]
    train = positive[pos_n:] + negative[neg_n:]
    return train, test


def metrics(results: list[dict]) -> dict:
    tp = sum(r["triggers"] for r in results if r["should_trigger"])
    pos_runs = sum(r["runs"] for r in results if r["should_trigger"])
    fp = sum(r["triggers"] for r in results if not r["should_trigger"])
    neg_runs = sum(r["runs"] for r in results if not r["should_trigger"])
    fn = pos_runs - tp
    tn = neg_runs - fp
    total = tp + tn + fp + fn
    return {
        "query_passed": sum(r["pass"] for r in results),
        "query_total": len(results),
        "trial_accuracy": round((tp + tn) / total, 4) if total else 0,
        "precision": round(tp / (tp + fp), 4) if tp + fp else 1,
        "recall": round(tp / (tp + fn), 4) if tp + fn else 1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-set", type=Path, required=True)
    parser.add_argument("--trials-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--description-label", default="current")
    args = parser.parse_args()

    eval_items = json.loads(args.eval_set.read_text())
    trial_paths = sorted(args.trials_dir.glob("trial-*.json"))
    if len(trial_paths) != 3:
        raise SystemExit(f"expected 3 trials, found {len(trial_paths)}")
    trials = [json.loads(path.read_text()) for path in trial_paths]
    descriptions = [trial["description"] for trial in trials]
    normalized = {re.sub(r"\s+", "", description) for description in descriptions}
    if len(normalized) != 1:
        raise SystemExit("trials used materially different descriptions")

    decisions: dict[str, list[bool]] = {item["query"]: [] for item in eval_items}
    reasons: dict[str, list[str]] = {item["query"]: [] for item in eval_items}
    for trial in trials:
        by_query = {item["query"]: item for item in trial["results"]}
        for item in eval_items:
            row = by_query[item["query"]]
            decisions[item["query"]].append(bool(row["decision"]))
            reasons[item["query"]].append(row.get("reason", ""))

    results = []
    for item in eval_items:
        votes = decisions[item["query"]]
        rate = sum(votes) / len(votes)
        expected = item["should_trigger"]
        passed = rate >= 0.5 if expected else rate < 0.5
        results.append({
            "query": item["query"],
            "should_trigger": expected,
            "trigger_rate": rate,
            "triggers": sum(votes),
            "runs": len(votes),
            "pass": passed,
            "reasons": reasons[item["query"]],
        })

    train_items, test_items = split_queries(eval_items)
    train_queries = {item["query"] for item in train_items}
    train_results = [r for r in results if r["query"] in train_queries]
    test_results = [r for r in results if r["query"] not in train_queries]
    payload = {
        "description_label": args.description_label,
        "description": descriptions[0],
        "runs_per_query": 3,
        "holdout": 0.4,
        "train": {"metrics": metrics(train_results), "results": train_results},
        "test": {"metrics": metrics(test_results), "results": test_results},
        "all": {"metrics": metrics(results), "results": results},
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload["all"]["metrics"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
