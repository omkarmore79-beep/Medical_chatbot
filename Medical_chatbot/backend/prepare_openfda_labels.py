import json
import re
from pathlib import Path

import pandas as pd


KB_DIR = Path("knowledge_base")
RAW_JSONL = KB_DIR / "openfda_drug_label_raw.jsonl"
PREPARED_CSV = KB_DIR / "openfda_drug_label_prepared.csv"

SECTIONS = [
    "indications_and_usage",
    "dosage_and_administration",
    "warnings",
    "boxed_warning",
    "contraindications",
    "adverse_reactions",
    "drug_interactions",
    "pregnancy",
    "lactation",
    "pediatric_use",
    "geriatric_use",
]


def normalize_space(value: str) -> str:
    value = str(value or "").strip()
    return re.sub(r"\s+", " ", value)


def chunk_text(text: str, max_chars: int = 900) -> list[str]:
    text = normalize_space(text)
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = []
    current_len = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if current and current_len + len(sentence) + 1 > max_chars:
            chunks.append(" ".join(current).strip())
            current = current[-1:]
            current_len = sum(len(item) + 1 for item in current)
        current.append(sentence)
        current_len += len(sentence) + 1
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def first_value(value):
    if isinstance(value, list):
        return normalize_space(value[0]) if value else ""
    return normalize_space(value)


def main() -> None:
    rows = []
    with RAW_JSONL.open("r", encoding="utf-8") as handle:
        for line in handle:
            result = json.loads(line)
            openfda = result.get("openfda", {}) or {}
            drug_name = first_value(openfda.get("brand_name")) or first_value(result.get("openfda", {}).get("generic_name"))
            generic_name = first_value(openfda.get("generic_name"))
            manufacturer = first_value(openfda.get("manufacturer_name"))
            rxcui = first_value(openfda.get("rxcui"))
            set_id = first_value(openfda.get("spl_set_id")) or first_value(result.get("id"))
            source_term = normalize_space(result.get("_source_term", ""))

            for section in SECTIONS:
                content = result.get(section, [])
                if not content:
                    continue
                section_text = normalize_space(" ".join(content if isinstance(content, list) else [str(content)]))
                for idx, chunk in enumerate(chunk_text(section_text), start=1):
                    rows.append(
                        {
                            "source": "openFDA",
                            "source_term": source_term,
                            "set_id": set_id,
                            "drug_name": drug_name,
                            "generic_name": generic_name,
                            "manufacturer": manufacturer,
                            "rxcui": rxcui,
                            "section_name": section,
                            "chunk_id": idx,
                            "section_text": chunk,
                            "structured_text": (
                                f"TYPE: DRUG_LABEL\n"
                                f"DRUG_NAME: {drug_name}\n"
                                f"GENERIC_NAME: {generic_name}\n"
                                f"SECTION: {section}\n"
                                f"CONTENT: {chunk}\n"
                                f"SOURCE: openFDA\n"
                                f"RXCUI: {rxcui}\n"
                                f"SET_ID: {set_id}"
                            ),
                        }
                    )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["set_id", "section_name", "section_text"], keep="first")
    df.to_csv(PREPARED_CSV, index=False, encoding="utf-8")
    print(f"OK: Prepared openFDA labels -> {PREPARED_CSV} | rows={len(df)}")


if __name__ == "__main__":
    main()
