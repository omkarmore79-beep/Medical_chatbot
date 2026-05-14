import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path


KB_DIR = Path("knowledge_base")
RAW_JSONL = KB_DIR / "symptom_to_diagnosis_raw.jsonl"


def fetch_rows(offset: int, length: int) -> dict:
    url = (
        "https://datasets-server.huggingface.co/rows?dataset="
        + urllib.parse.quote("gretelai/symptom_to_diagnosis", safe="")
        + f"&config=default&split=train&offset={offset}&length={length}"
    )
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download gretelai/symptom_to_diagnosis via the datasets server.")
    parser.add_argument("--page-size", type=int, default=100, help="Rows per request.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing raw file.")
    args = parser.parse_args()

    if args.overwrite and RAW_JSONL.exists():
        RAW_JSONL.unlink()

    first_page = fetch_rows(0, args.page_size)
    total = first_page.get("num_rows_total", 0)

    with RAW_JSONL.open("a", encoding="utf-8") as handle:
        for offset in range(0, total, args.page_size):
            page = first_page if offset == 0 else fetch_rows(offset, args.page_size)
            for row in page.get("rows", []):
                record = row.get("row", {})
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")
            print(f"Downloaded {min(offset + args.page_size, total)}/{total}")

    print(f"OK: Symptom phrasing raw data saved to {RAW_JSONL}")


if __name__ == "__main__":
    main()
