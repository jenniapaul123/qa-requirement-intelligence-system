"""Simple smoke test for req-quality-analyzer.

This test validates that `last_report.json` exists and contains the
required top-level keys and types expected by consumers.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
REPORT = ROOT / "last_report.json"

REQUIRED_KEYS = {
    "summary": str,
    "clarity_score": int,
    "clarity_score_reason": str,
    "ambiguities": list,
    "missing_information": list,
    "assumptions": list,
    "risks_and_dependencies": list,
    "edge_cases": list,
    "acceptance_criteria": list,
    "test_scenarios": list,
}


def main():
    if not REPORT.exists():
        print(f"FAIL: {REPORT} not found")
        sys.exit(2)

    data = json.loads(REPORT.read_text(encoding="utf-8"))

    for k, t in REQUIRED_KEYS.items():
        if k not in data:
            print(f"FAIL: missing key: {k}")
            sys.exit(2)
        if not isinstance(data[k], t):
            print(f"FAIL: key {k} expected {t.__name__}, got {type(data[k]).__name__}")
            sys.exit(2)

    # additional check: clarity_score range
    cs = data.get("clarity_score")
    if not (0 <= cs <= 100):
        print(f"FAIL: clarity_score out of range: {cs}")
        sys.exit(2)

    print("OK: last_report.json looks valid")


if __name__ == "__main__":
    main()
