"""Experiment aggregation utilities."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List


METRIC_ROWS = [
    ("execution", "Execution Success Rate"),
    ("exists", "Object Completeness"),
    ("relation", "Spatial Relation Accuracy"),
    ("visible", "Visibility Pass Rate"),
    ("material", "Material Pass Rate"),
    ("color", "Color Pass Rate"),
    ("lighting", "Lighting Pass Rate"),
    ("overall", "Overall Contract Pass Rate"),
]


def aggregate(rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    rows = list(rows)
    methods = sorted({str(row["method"]) for row in rows})
    summary: List[Dict[str, object]] = []
    for method in methods:
        method_rows = [row for row in rows if row["method"] == method]
        for metric_key, metric_name in METRIC_ROWS:
            passed = 0
            total = 0
            for row in method_rows:
                by_type = row["summary"]["by_type"]  # type: ignore[index]
                if metric_key == "overall":
                    passed += int(row["summary"]["passed"])  # type: ignore[index]
                    total += int(row["summary"]["total"])  # type: ignore[index]
                elif metric_key in by_type:
                    passed += int(by_type[metric_key]["passed"])
                    total += int(by_type[metric_key]["total"])
            summary.append(
                {
                    "method": method,
                    "metric": metric_name,
                    "passed": passed,
                    "total": total,
                    "rate": passed / total if total else 0.0,
                }
            )
    return summary


def write_summary_csv(summary: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "metric", "passed", "total", "rate"])
        writer.writeheader()
        for row in summary:
            writer.writerow(
                {
                    "method": row["method"],
                    "metric": row["metric"],
                    "passed": row["passed"],
                    "total": row["total"],
                    "rate": f"{float(row['rate']):.4f}",
                }
            )
