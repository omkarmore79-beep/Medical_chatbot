import json
import re
from pathlib import Path

import pandas as pd


KB_DIR = Path("knowledge_base")
RAW_JSONL = KB_DIR / "symptom_to_diagnosis_raw.jsonl"
PREPARED_CSV = KB_DIR / "symptom_to_diagnosis_prepared.csv"


def normalize_space(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_key(value: str) -> str:
    value = normalize_space(value).lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def main() -> None:
    rows = []
    with RAW_JSONL.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            input_text = normalize_space(record.get("input_text", ""))
            output_text = normalize_space(record.get("output_text", ""))
            if not input_text or not output_text:
                continue
            rows.append(
                {
                    "source": "gretelai/symptom_to_diagnosis",
                    "input_text": input_text,
                    "output_text": output_text,
                    "normalized_input": normalize_key(input_text),
                    "structured_text": (
                        f"TYPE: SYMPTOM_NL\n"
                        f"PATIENT_DESCRIPTION: {input_text}\n"
                        f"POSSIBLE_CONDITION: {output_text}\n"
                        f"SOURCE: gretelai/symptom_to_diagnosis"
                    ),
                }
            )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["normalized_input", "output_text"], keep="first")
    df.to_csv(PREPARED_CSV, index=False, encoding="utf-8")
    print(f"OK: Prepared symptom phrasing dataset -> {PREPARED_CSV} | rows={len(df)}")


if __name__ == "__main__":
    main()
