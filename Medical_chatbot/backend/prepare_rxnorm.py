import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


KB_DIR = Path("knowledge_base")
RAW_JSONL = KB_DIR / "rxnorm_raw.jsonl"
CONCEPTS_CSV = KB_DIR / "rxnorm_concepts.csv"
BRAND_MAP_CSV = KB_DIR / "rxnorm_brand_generic_map.csv"


GENERIC_TTYS = {"IN", "MIN", "PIN"}
BRAND_TTYS = {"BN"}
CLINICAL_DRUG_TTYS = {"SCD", "SBD", "GPCK", "BPCK", "SCDC", "SBDC", "SCDF", "SBDF"}


def normalize_key(value: str) -> str:
    value = str(value or "").strip().lower()
    return " ".join(value.replace("/", " ").replace("-", " ").split())


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def parse_related_names(bundle: dict) -> dict[str, set[str]]:
    names = defaultdict(set)
    concept_groups = bundle.get("all_related", {}).get("allRelatedGroup", {}).get("conceptGroup", []) or []
    for group in concept_groups:
        tty = group.get("tty", "")
        for item in group.get("conceptProperties", []) or []:
            name = item.get("name", "").strip()
            if name:
                names[tty].add(name)
    return names


def parse_all_properties(bundle: dict) -> dict[str, list[str]]:
    values = defaultdict(list)
    prop_concepts = bundle.get("all_properties", {}).get("propConceptGroup", {}).get("propConcept", []) or []
    for item in prop_concepts:
        key = item.get("propName", "").strip()
        value = item.get("propValue", "").strip()
        if key and value and value not in values[key]:
            values[key].append(value)
    return values


def main() -> None:
    bundles = load_jsonl(RAW_JSONL)
    concept_rows = []
    brand_rows = []

    for bundle in bundles:
        properties = bundle.get("properties", {}).get("properties", {}) or {}
        rxcui = properties.get("rxcui", bundle.get("rxcui", "")).strip()
        name = properties.get("name", "").strip()
        tty = properties.get("tty", "").strip()
        if not rxcui or not name:
            continue

        related_names = parse_related_names(bundle)
        prop_values = parse_all_properties(bundle)

        generic_names = sorted(
            {
                item
                for related_tty, values in related_names.items()
                if related_tty in GENERIC_TTYS
                for item in values
            }
        )
        brand_names = sorted(
            {
                item
                for related_tty, values in related_names.items()
                if related_tty in BRAND_TTYS
                for item in values
            }
        )
        clinical_names = sorted(
            {
                item
                for related_tty, values in related_names.items()
                if related_tty in CLINICAL_DRUG_TTYS
                for item in values
            }
        )
        aliases = sorted(set(generic_names + brand_names + clinical_names))

        strength_values = prop_values.get("AVAILABLE_STRENGTH", [])
        dose_form_values = prop_values.get("RXNORM_DOSE_FORM", []) or prop_values.get("DOSE_FORM_GROUP", [])
        atc_codes = prop_values.get("ATC", [])

        concept_rows.append(
            {
                "rxcui": rxcui,
                "canonical_name": name,
                "canonical_name_key": normalize_key(name),
                "term_type": tty,
                "source_term": bundle.get("source_term", ""),
                "generic_names": " | ".join(generic_names),
                "brand_names": " | ".join(brand_names),
                "clinical_drug_names": " | ".join(clinical_names),
                "dose_forms": " | ".join(dose_form_values),
                "strengths": " | ".join(strength_values),
                "atc_codes": " | ".join(atc_codes),
                "aliases": " | ".join(aliases),
                "structured_text": (
                    f"TYPE: RXNORM_MEDICATION\n"
                    f"CANONICAL_NAME: {name}\n"
                    f"TERM_TYPE: {tty}\n"
                    f"GENERIC_NAMES: {' | '.join(generic_names)}\n"
                    f"BRAND_NAMES: {' | '.join(brand_names)}\n"
                    f"CLINICAL_DRUG_NAMES: {' | '.join(clinical_names)}\n"
                    f"DOSE_FORMS: {' | '.join(dose_form_values)}\n"
                    f"STRENGTHS: {' | '.join(strength_values)}\n"
                    f"ATC_CODES: {' | '.join(atc_codes)}\n"
                    f"ALIASES: {' | '.join(aliases)}\n"
                    f"RXCUI: {rxcui}"
                ),
            }
        )

        for brand_name in brand_names:
            linked_generics = generic_names or [name]
            for generic_name in linked_generics:
                brand_rows.append(
                    {
                        "brand_name": brand_name,
                        "brand_name_key": normalize_key(brand_name),
                        "generic_name": generic_name,
                        "generic_name_key": normalize_key(generic_name),
                        "rxcui": rxcui,
                        "term_type": tty,
                    }
                )

    concept_df = pd.DataFrame(concept_rows).drop_duplicates(subset=["rxcui"], keep="first")
    brand_df = pd.DataFrame(brand_rows).drop_duplicates(
        subset=["brand_name_key", "generic_name_key", "rxcui"],
        keep="first",
    )

    concept_df.to_csv(CONCEPTS_CSV, index=False, encoding="utf-8")
    brand_df.to_csv(BRAND_MAP_CSV, index=False, encoding="utf-8")

    print(f"OK: RxNorm concepts saved to {CONCEPTS_CSV} | rows={len(concept_df)}")
    print(f"OK: RxNorm brand-generic map saved to {BRAND_MAP_CSV} | rows={len(brand_df)}")


if __name__ == "__main__":
    main()
