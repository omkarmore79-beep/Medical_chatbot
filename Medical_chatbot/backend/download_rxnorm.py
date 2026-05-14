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
RAW_JSONL = KB_DIR / "rxnorm_raw.jsonl"
LOG_CSV = KB_DIR / "rxnorm_download_log.csv"


def normalize_key(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("/", " ").replace("-", " ")
    value = value.replace("+", " ")
    value = " ".join(value.split())
    value = value.replace("(", " ").replace(")", " ")
    return " ".join(value.split())


def clean_rxnorm_term(value: str) -> str:
    value = normalize_key(value)
    value = pd.Series([value]).str.replace(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu)\b", "", regex=True).iloc[0]
    value = pd.Series([value]).str.replace(
        r"\b(tablet|tablets|capsule|capsules|syrup|injection|cream|ointment|drop|drops|kit)\b",
        "",
        regex=True,
    ).iloc[0]
    value = " ".join(value.split())
    return value


def gather_seed_terms(limit: int | None) -> list[str]:
    generic_terms = []
    brand_terms = []

    def add_term(bucket: list[str], value: str):
        key = clean_rxnorm_term(value)
        if key and len(key) >= 4:
            bucket.append(key)

    for brand, generic in brand_to_generic.items():
        add_term(generic_terms, generic)
        add_term(brand_terms, brand)

    prepared_meds = KB_DIR / "updated_indian_medicine_data_prepared.csv"
    if prepared_meds.exists():
        df = pd.read_csv(prepared_meds).fillna("")
        for value in df.get("generic_or_salt", []).tolist():
            add_term(generic_terms, value)
        for column in ["name"]:
            if column not in df.columns:
                continue
            for value in df[column].tolist():
                add_term(brand_terms, value)

    ordered = []
    seen = set()
    for value in generic_terms + brand_terms:
        if value not in seen:
            ordered.append(value)
            seen.add(value)

    if limit:
        ordered = ordered[:limit]
    return ordered


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=45) as response:
        return json.load(response)


def fetch_rxcuis(term: str) -> list[str]:
    searches = [2, 1]
    found = []
    for search_mode in searches:
        url = (
            "https://rxnav.nlm.nih.gov/REST/rxcui.json?"
            + urllib.parse.urlencode({"name": term, "search": search_mode})
        )
        payload = fetch_json(url)
        ids = payload.get("idGroup", {}).get("rxnormId", []) or []
        if ids:
            found.extend(ids)
            break
    return sorted(set(found))


def fetch_concept_bundle(term: str, rxcui: str) -> dict:
    base = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}"
    return {
        "source_term": term,
        "rxcui": rxcui,
        "properties": fetch_json(f"{base}/properties.json"),
        "all_properties": fetch_json(f"{base}/allProperties.json?prop=all"),
        "all_related": fetch_json(f"{base}/allrelated.json"),
    }


def append_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def write_log(path: Path, rows: list[dict]) -> None:
    fieldnames = ["source_term", "matched_rxcuis", "status", "error"]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download RxNorm concept bundles from the RxNav API.")
    parser.add_argument("--max-terms", type=int, default=150, help="Maximum number of seed terms to query.")
    parser.add_argument("--sleep-seconds", type=float, default=0.1, help="Delay between API requests.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing raw and log files.")
    args = parser.parse_args()

    KB_DIR.mkdir(exist_ok=True)

    if args.overwrite:
        if RAW_JSONL.exists():
            RAW_JSONL.unlink()
        if LOG_CSV.exists():
            LOG_CSV.unlink()

    terms = gather_seed_terms(args.max_terms)
    log_rows = []

    seen_rxcui = set()
    for idx, term in enumerate(terms, start=1):
        try:
            rxcuis = fetch_rxcuis(term)
            bundles = []
            for rxcui in rxcuis:
                if rxcui in seen_rxcui:
                    continue
                bundles.append(fetch_concept_bundle(term, rxcui))
                seen_rxcui.add(rxcui)
                time.sleep(args.sleep_seconds)

            if bundles:
                append_jsonl(RAW_JSONL, bundles)

            log_rows.append(
                {
                    "source_term": term,
                    "matched_rxcuis": "|".join(rxcuis),
                    "status": "ok" if rxcuis else "not_found",
                    "error": "",
                }
            )
        except Exception as exc:
            log_rows.append(
                {
                    "source_term": term,
                    "matched_rxcuis": "",
                    "status": "error",
                    "error": str(exc),
                }
            )

        if idx % 20 == 0:
            write_log(LOG_CSV, log_rows)
            log_rows = []
            print(f"Processed {idx}/{len(terms)} terms")

    if log_rows:
        write_log(LOG_CSV, log_rows)

    print(f"OK: RxNorm raw data saved to {RAW_JSONL}")
    print(f"OK: Download log saved to {LOG_CSV}")


if __name__ == "__main__":
    main()
