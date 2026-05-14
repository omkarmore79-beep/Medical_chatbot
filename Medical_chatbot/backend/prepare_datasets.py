import json
import re
from pathlib import Path

import pandas as pd

from brand_mapping import brand_aliases, brand_to_generic


KB_DIR = Path("knowledge_base")

MEDQUAD_RAW = KB_DIR / "medquad.csv"
MEDQUAD_PREPARED = KB_DIR / "medquad_prepared.csv"

MEDICINE_RAW = KB_DIR / "updated_indian_medicine_data.csv"
MEDICINE_PREPARED = KB_DIR / "updated_indian_medicine_data_prepared.csv"

SYMPTOM_RAW = KB_DIR / "symptom_kb.csv"
SYMPTOM_PREPARED = KB_DIR / "symptom_kb_prepared.csv"

BRAND_INDEX_RAW = KB_DIR / "Comprehensive_Medicine_Brand_Index.csv"
BRAND_INDEX_PREPARED = KB_DIR / "Comprehensive_Medicine_Brand_Index_expanded.csv"
BRAND_JSON_PREPARED = KB_DIR / "brand_generic_index_expanded.json"


def _normalize_space(value: str) -> str:
    value = str(value or "")
    value = value.replace("\r", " ").replace("\n", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _normalize_key(value: str) -> str:
    value = _normalize_space(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _split_sentences(text: str) -> list[str]:
    text = _normalize_space(text)
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _chunk_text(text: str, max_chars: int = 700, overlap_sentences: int = 1) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence) + 1
        if current and current_len + sentence_len > max_chars:
            chunks.append(" ".join(current).strip())
            current = current[-overlap_sentences:] if overlap_sentences else []
            current_len = sum(len(item) + 1 for item in current)

        current.append(sentence)
        current_len += sentence_len

    if current:
        chunks.append(" ".join(current).strip())

    return chunks


def _safe_json_loads(value: str) -> dict:
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def prepare_medquad() -> None:
    df = pd.read_csv(MEDQUAD_RAW).fillna("")
    df["question"] = df["question"].map(_normalize_space)
    df["answer"] = df["answer"].map(_normalize_space)
    df["source"] = df["source"].map(_normalize_space)
    df["focus_area"] = df["focus_area"].map(_normalize_space)

    df = df[(df["question"] != "") & (df["answer"] != "")]
    df["question_key"] = df["question"].map(_normalize_key)
    df["answer_len"] = df["answer"].str.len()
    df = df.sort_values(["question_key", "answer_len"], ascending=[True, False])
    df = df.drop_duplicates(subset=["question_key"], keep="first")

    rows = []
    for _, row in df.iterrows():
        chunks = _chunk_text(row["answer"], max_chars=700, overlap_sentences=1) or [row["answer"]]
        for idx, chunk in enumerate(chunks, start=1):
            rows.append(
                {
                    "question": row["question"],
                    "question_key": row["question_key"],
                    "focus_area": row["focus_area"],
                    "source": row["source"],
                    "chunk_id": idx,
                    "chunk_count": len(chunks),
                    "answer_chunk": chunk,
                    "structured_text": (
                        f"TYPE: MEDICAL_QA\n"
                        f"QUESTION: {row['question']}\n"
                        f"FOCUS_AREA: {row['focus_area']}\n"
                        f"SOURCE: {row['source']}\n"
                        f"ANSWER_PART_{idx}_OF_{len(chunks)}: {chunk}"
                    ),
                }
            )

    pd.DataFrame(rows).to_csv(MEDQUAD_PREPARED, index=False, encoding="utf-8")
    print(f"OK: Prepared MedQuAD -> {MEDQUAD_PREPARED} | rows={len(rows)}")


def _extract_strength(name: str, composition: str) -> str:
    for value in [name, composition]:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)", str(value), flags=re.IGNORECASE)
        if match:
            return f"{match.group(1)} {match.group(2).lower()}"
    return ""


def _split_side_effects(value: str) -> list[str]:
    text = _normalize_space(value)
    if not text:
        return []
    return [item.strip() for item in re.split(r",|\||;", text) if item.strip()]


def _infer_uses_from_desc(text: str) -> str:
    if not text:
        return ""
    lower = text.lower()
    for marker in [" is used to ", " helps treat ", " is a medicine used to ", " is used for "]:
        idx = lower.find(marker)
        if idx != -1:
            snippet = text[idx + len(marker):]
            sentences = _split_sentences(snippet)
            return sentences[0] if sentences else snippet[:240].strip()
    sentences = _split_sentences(text)
    return sentences[0] if sentences else ""


def prepare_medicine_dataset() -> None:
    df = pd.read_csv(MEDICINE_RAW).fillna("")
    text_cols = [
        "name",
        "manufacturer_name",
        "pack_size_label",
        "short_composition1",
        "short_composition2",
        "salt_composition",
        "medicine_desc",
        "side_effects",
        "drug_interactions",
    ]
    for col in text_cols:
        df[col] = df[col].map(_normalize_space)

    df["name_key"] = df["name"].map(_normalize_key)
    df["has_clinical_content"] = (
        (df["medicine_desc"] != "")
        | (df["side_effects"] != "")
        | (df["drug_interactions"] != "")
        | (df["salt_composition"] != "")
    )
    df = df[df["has_clinical_content"]].copy()
    df = df[df["Is_discontinued"].astype(str).str.lower() != "true"].copy()
    df["content_score"] = (
        df["medicine_desc"].str.len()
        + df["side_effects"].str.len()
        + df["drug_interactions"].str.len()
        + df["salt_composition"].str.len()
    )
    df = df.sort_values(["name_key", "content_score"], ascending=[True, False])
    df = df.drop_duplicates(subset=["name_key"], keep="first")

    structured_rows = []
    for _, row in df.iterrows():
        name = row["name"]
        generic = row["salt_composition"] or " ".join(
            part for part in [row["short_composition1"], row["short_composition2"]] if part
        ).strip()
        desc = row["medicine_desc"]
        uses = _infer_uses_from_desc(desc)
        side_effects = _split_side_effects(row["side_effects"])

        interaction_data = _safe_json_loads(row["drug_interactions"])
        interaction_drugs = [item.strip() for item in interaction_data.get("drug", []) if str(item).strip()]
        interaction_brands = [item.strip() for item in interaction_data.get("brand", []) if str(item).strip()]
        interaction_effects = [item.strip() for item in interaction_data.get("effect", []) if str(item).strip()]
        interaction_pairs = []
        for i, drug in enumerate(interaction_drugs):
            brand = interaction_brands[i] if i < len(interaction_brands) else ""
            effect = interaction_effects[i] if i < len(interaction_effects) else ""
            interaction_pairs.append(f"{drug} | {brand} | {effect}".strip(" |"))

        structured_text = (
            f"TYPE: MEDICINE\n"
            f"NAME: {name}\n"
            f"GENERIC_OR_SALT: {generic}\n"
            f"MANUFACTURER: {row['manufacturer_name']}\n"
            f"PACK_SIZE: {row['pack_size_label']}\n"
            f"USES: {uses}\n"
            f"DESCRIPTION: {desc}\n"
            f"SIDE_EFFECTS: {', '.join(side_effects)}\n"
            f"INTERACTIONS: {'; '.join(interaction_pairs)}"
        )

        structured_rows.append(
            {
                "id": row["id"],
                "name": name,
                "name_key": row["name_key"],
                "price": row["price"],
                "manufacturer_name": row["manufacturer_name"],
                "pack_size_label": row["pack_size_label"],
                "generic_or_salt": generic,
                "uses": uses,
                "description": desc,
                "side_effects_list": json.dumps(side_effects, ensure_ascii=True),
                "interaction_pairs": json.dumps(interaction_pairs, ensure_ascii=True),
                "strength": _extract_strength(name, generic),
                "structured_text": structured_text,
            }
        )

    pd.DataFrame(structured_rows).to_csv(MEDICINE_PREPARED, index=False, encoding="utf-8")
    print(f"OK: Prepared medicine dataset -> {MEDICINE_PREPARED} | rows={len(structured_rows)}")


def _parse_symptom_blob(text: str) -> dict:
    parsed = {}
    for line in str(text).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[_normalize_key(key).replace(" ", "_")] = value.strip()
    return parsed


def _clean_symptom_terms(value: str) -> list[str]:
    text = str(value or "").replace("_", " ")
    parts = [item.strip() for item in re.split(r",|\|", text) if item.strip()]
    cleaned = []
    seen = set()
    for part in parts:
        key = _normalize_key(part)
        if key and key not in seen:
            cleaned.append(part.strip())
            seen.add(key)
    return cleaned


def prepare_symptom_dataset() -> None:
    df = pd.read_csv(SYMPTOM_RAW).fillna("")
    parsed_rows = []

    for _, row in df.iterrows():
        parsed = _parse_symptom_blob(row["text"])
        disease = _normalize_space(parsed.get("disease", ""))
        symptoms = _clean_symptom_terms(parsed.get("symptoms", ""))
        synonyms = _clean_symptom_terms(parsed.get("symptom_synonyms", ""))
        followups = _clean_symptom_terms(parsed.get("follow_up_questions", ""))
        severity = _normalize_space(parsed.get("severity_level", ""))
        action = _normalize_space(parsed.get("recommended_action", ""))

        if not disease or not symptoms:
            continue

        disease_key = _normalize_key(disease)
        symptom_key = "|".join(sorted(_normalize_key(item) for item in symptoms))
        parsed_rows.append(
            {
                "id": row["id"],
                "disease": disease,
                "disease_key": disease_key,
                "symptoms": symptoms,
                "symptom_key": symptom_key,
                "synonyms": synonyms,
                "follow_up_questions": followups,
                "severity_level": severity,
                "recommended_action": action,
            }
        )

    clean_df = pd.DataFrame(parsed_rows)
    clean_df = clean_df.drop_duplicates(subset=["disease_key", "symptom_key"], keep="first")

    rows = []
    for _, row in clean_df.iterrows():
        common_text = (
            f"DISEASE: {row['disease']}\n"
            f"SYMPTOMS: {', '.join(row['symptoms'])}\n"
            f"SYMPTOM_SYNONYMS: {', '.join(row['synonyms'])}\n"
            f"FOLLOW_UP_QUESTIONS: {' | '.join(row['follow_up_questions'])}\n"
            f"SEVERITY_LEVEL: {row['severity_level']}\n"
            f"RECOMMENDED_ACTION: {row['recommended_action']}"
        )
        rows.append(
            {
                "id": row["id"],
                "record_type": "symptom_disease",
                "lookup_text": ", ".join(row["symptoms"] + row["synonyms"]),
                "structured_text": f"TYPE: SYMPTOM_DISEASE\n{common_text}",
            }
        )
        rows.append(
            {
                "id": f"{row['id']}_triage",
                "record_type": "symptom_triage",
                "lookup_text": ", ".join(row["symptoms"] + row["synonyms"]),
                "structured_text": (
                    f"TYPE: SYMPTOM_TRIAGE\n"
                    f"PATIENT_PHRASES: {', '.join(row['symptoms'] + row['synonyms'])}\n"
                    f"POSSIBLE_CONDITION: {row['disease']}\n"
                    f"SEVERITY_LEVEL: {row['severity_level']}\n"
                    f"FOLLOW_UP_QUESTIONS: {' | '.join(row['follow_up_questions'])}\n"
                    f"RECOMMENDED_ACTION: {row['recommended_action']}"
                ),
            }
        )

    pd.DataFrame(rows).to_csv(SYMPTOM_PREPARED, index=False, encoding="utf-8")
    print(f"OK: Prepared symptom dataset -> {SYMPTOM_PREPARED} | rows={len(rows)}")


def _infer_form(brand: str, generic: str) -> str:
    text = f"{brand} {generic}".lower()
    if "inj" in text or "injection" in text:
        return "injection"
    if "syrup" in text or "syp" in text:
        return "syrup"
    if "capsule" in text or "cap" in text:
        return "capsule"
    if "insulin" in text:
        return "injection"
    if "drop" in text:
        return "drops"
    return "tablet"


def prepare_brand_index() -> None:
    rows_by_brand = {}

    if BRAND_INDEX_RAW.exists():
        raw_df = pd.read_csv(BRAND_INDEX_RAW).fillna("")
        for _, row in raw_df.iterrows():
            brand = _normalize_space(row["brand"]).lower()
            if not brand:
                continue
            rows_by_brand[brand] = {
                "brand": brand,
                "generic": _normalize_space(row["generic"]).lower(),
                "aliases": _normalize_space(row.get("aliases", "")),
                "form": _normalize_space(row.get("form", "")) or _infer_form(brand, row["generic"]),
                "strength": _normalize_space(row.get("strength", "")),
            }

    for brand, generic in brand_to_generic.items():
        key = _normalize_space(brand).lower()
        row = rows_by_brand.get(
            key,
            {
                "brand": key,
                "generic": _normalize_space(generic).lower(),
                "aliases": "",
                "form": _infer_form(brand, generic),
                "strength": _extract_strength(brand, generic),
            },
        )
        if not row["generic"]:
            row["generic"] = _normalize_space(generic).lower()
        if not row["form"]:
            row["form"] = _infer_form(brand, generic)
        if not row["strength"]:
            row["strength"] = _extract_strength(brand, generic)
        rows_by_brand[key] = row

    for alias, canonical in brand_aliases.items():
        canonical_key = _normalize_space(canonical).lower()
        alias_text = _normalize_space(alias).lower()
        if canonical_key not in rows_by_brand or not alias_text:
            continue
        existing_aliases = [item.strip() for item in rows_by_brand[canonical_key]["aliases"].split(",") if item.strip()]
        if alias_text not in existing_aliases:
            existing_aliases.append(alias_text)
        rows_by_brand[canonical_key]["aliases"] = ", ".join(sorted(existing_aliases))

    expanded_rows = sorted(rows_by_brand.values(), key=lambda item: item["brand"])
    pd.DataFrame(expanded_rows).to_csv(BRAND_INDEX_PREPARED, index=False, encoding="utf-8")
    BRAND_JSON_PREPARED.write_text(json.dumps(expanded_rows, indent=2), encoding="utf-8")
    print(f"OK: Expanded brand index -> {BRAND_INDEX_PREPARED} | rows={len(expanded_rows)}")


def main() -> None:
    prepare_medquad()
    prepare_medicine_dataset()
    prepare_symptom_dataset()
    prepare_brand_index()
    print("DONE: Dataset preparation complete.")


if __name__ == "__main__":
    main()
