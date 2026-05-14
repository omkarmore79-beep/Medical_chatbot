import json
import sys
from pathlib import Path

from rag_engine import get_answer


CASES_PATH = Path("regression_queries.json")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    passed = 0
    for case in cases:
        result = get_answer(case["query"], include_debug=True)
        detected_domain = result.get("detected_domain")
        contexts = result.get("retrieved_contexts") or []
        top_source = contexts[0]["source_db"] if contexts else None
        answer = result.get("answer", "")
        failures = []

        if detected_domain != case["expected_domain"]:
            failures.append(f"domain expected={case['expected_domain']} actual={detected_domain}")

        expected_source = case.get("expected_top_source")
        if expected_source and top_source != expected_source:
            failures.append(f"top_source expected={expected_source} actual={top_source}")

        if "temporarily unavailable" in answer.lower():
            failures.append("generator_unavailable")

        status = "PASS" if not failures else "FAIL"
        if not failures:
            passed += 1

        print(f"[{status}] {case['name']}")
        print(f"  query: {case['query']}")
        print(f"  domain: {detected_domain}")
        print(f"  top_source: {top_source}")
        if failures:
            print(f"  failures: {', '.join(failures)}")
        print()

    print(f"Summary: {passed}/{len(cases)} passed")


if __name__ == "__main__":
    main()
