import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from brand_mapping import brand_to_generic


KB_DIR = Path("knowledge_base")
RAW_JSONL = KB_DIR / "dailymed_raw.jsonl"
LOG_CSV = KB_DIR / "dailymed_log.csv"


def normalize_space(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("/", " ").replace("-", " ").replace("+", " ")
    return " ".join(value.split())


def clean_term(value: str) -> str:
    value = normalize_space(value)
    value = pd.Series([value]).str.replace(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu)\b", "", regex=True).iloc[0]
    value = pd.Series([value]).str.replace(
        r"\b(tablet|tablets|capsule|capsules|syrup|injection|cream|ointment|drop|drops|kit)\b",
        "",
        regex=True,
    ).iloc[0]
    return " ".join(value.split())


def gather_seed_terms(limit: int | None) -> list[str]:
    generic_terms = []

    def add(value: str):
        key = clean_term(value)
        if key and len(key) >= 4:
            generic_terms.append(key)

    for generic in brand_to_generic.values():
        add(generic)

    prepared_meds = KB_DIR / "updated_indian_medicine_data_prepared.csv"
    if prepared_meds.exists():
        df = pd.read_csv(prepared_meds).fillna("")
        for value in df.get("generic_or_salt", []).tolist():
            add(value)

    seen = set()
    ordered = []
    for item in generic_terms:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered[:limit] if limit else ordered


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def search_spls(term: str, pagesize: int) -> list[dict]:
    params = urllib.parse.urlencode({"drug_name": term, "page": 1, "pagesize": pagesize})
    payload = fetch_json(f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?{params}")
    return payload.get("data", []) or []


def fetch_packaging(setid: str) -> dict:
    return fetch_json(f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}/packaging.json")


def append_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def write_log(path: Path, rows: list[dict]) -> None:
    fieldnames = ["source_term", "result_count", "status", "error"]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download DailyMed SPL packaging data for seeded medicine terms.")
    parser.add_argument("--max-terms", type=int, default=100, help="Maximum number of generic terms to query.")
    parser.add_argument("--results-per-term", type=int, default=2, help="Max SPLs per term.")
    parser.add_argument("--sleep-seconds", type=float, default=0.1, help="Delay between requests.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing raw and log files.")
    args = parser.parse_args()

    if args.overwrite:
        if RAW_JSONL.exists():
            RAW_JSONL.unlink()
        if LOG_CSV.exists():
            LOG_CSV.unlink()

    terms = gather_seed_terms(args.max_terms)
    seen_setids = set()
    log_rows = []

    for idx, term in enumerate(terms, start=1):
        try:
            results = search_spls(term, args.results_per_term)
            new_rows = []
            for item in results:
                setid = item.get("setid")
                if not setid or setid in seen_setids:
                    continue
                packaging = fetch_packaging(setid)
                payload = {
                    "_source_term": term,
                    "search_result": item,
                    "packaging": packaging.get("data", {}),
                }
                new_rows.append(payload)
                seen_setids.add(setid)
                time.sleep(args.sleep_seconds)
            if new_rows:
                append_jsonl(RAW_JSONL, new_rows)
            log_rows.append({"source_term": term, "result_count": len(results), "status": "ok", "error": ""})
        except Exception as exc:
            log_rows.append({"source_term": term, "result_count": 0, "status": "error", "error": str(exc)})

        if idx % 20 == 0:
            write_log(LOG_CSV, log_rows)
            log_rows = []
            print(f"Processed {idx}/{len(terms)} terms")

    if log_rows:
        write_log(LOG_CSV, log_rows)

    print(f"OK: DailyMed raw data saved to {RAW_JSONL}")
    print(f"OK: DailyMed log saved to {LOG_CSV}")


if __name__ == "__main__":
    main()
