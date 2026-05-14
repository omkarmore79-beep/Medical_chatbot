import argparse
from pathlib import Path

import pandas as pd


DATA_DIR = Path("knowledge_base") / "mimic_iv_demo"
D_LABITEMS = DATA_DIR / "d_labitems.csv.gz"
LABEVENTS = DATA_DIR / "labevents.csv.gz"
OUT_ITEMS = Path("knowledge_base") / "mimic_lab_items.csv"
OUT_PREPARED = Path("knowledge_base") / "lab_reference_aliases.csv"


def normalize_text(value: str) -> str:
    value = str(value or "").strip()
    value = " ".join(value.split())
    return value


def build_aliases(label: str, fluid: str, category: str) -> str:
    aliases = []
    if label:
        aliases.append(label)
        aliases.append(label.lower())
        aliases.append(label.replace(",", " "))
    if fluid:
        aliases.append(f"{label} {fluid}")
    if category:
        aliases.append(f"{category} {label}")
    seen = []
    seen_keys = set()
    for item in aliases:
        cleaned = normalize_text(item)
        key = cleaned.lower()
        if cleaned and key not in seen_keys:
            seen.append(cleaned)
            seen_keys.add(key)
    return " | ".join(seen)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare MIMIC-IV demo lab reference aliases.")
    parser.add_argument("--max-units", type=int, default=5, help="Max distinct units to keep per lab item.")
    args = parser.parse_args()

    d_lab = pd.read_csv(D_LABITEMS, compression="gzip").fillna("")
    labevents = pd.read_csv(LABEVENTS, compression="gzip", usecols=["itemid", "valueuom"]).fillna("")

    units = (
        labevents[labevents["valueuom"].astype(str).str.strip() != ""]
        .groupby("itemid")["valueuom"]
        .agg(lambda values: " | ".join(sorted(dict.fromkeys(v.strip() for v in values if str(v).strip()))[: args.max_units]))
        .reset_index()
    )

    merged = d_lab.merge(units, on="itemid", how="left")
    merged["label"] = merged["label"].map(normalize_text)
    merged["fluid"] = merged["fluid"].map(normalize_text)
    merged["category"] = merged["category"].map(normalize_text)
    merged["valueuom"] = merged["valueuom"].fillna("").map(normalize_text)
    merged["aliases"] = merged.apply(
        lambda row: build_aliases(row["label"], row["fluid"], row["category"]),
        axis=1,
    )

    merged["structured_text"] = merged.apply(
        lambda row: (
            f"TYPE: LAB_TEST\n"
            f"DISPLAY_NAME: {row['label']}\n"
            f"ALIASES: {row['aliases']}\n"
            f"UNIT: {row['valueuom']}\n"
            f"CATEGORY: {row['category']}\n"
            f"FLUID: {row['fluid']}\n"
            f"LOINC: {row.get('loinc_code', '')}\n"
            f"ITEMID: {row['itemid']}"
        ),
        axis=1,
    )

    merged.to_csv(OUT_ITEMS, index=False, encoding="utf-8")
    merged[
        ["itemid", "label", "aliases", "valueuom", "category", "fluid", "structured_text"]
    ].to_csv(OUT_PREPARED, index=False, encoding="utf-8")

    print(f"OK: Saved {OUT_ITEMS} | rows={len(merged)}")
    print(f"OK: Saved {OUT_PREPARED} | rows={len(merged)}")


if __name__ == "__main__":
    main()
