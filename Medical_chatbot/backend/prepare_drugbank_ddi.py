import argparse
import csv
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


KB_DIR = Path("knowledge_base")
ZIP_PATH = KB_DIR / "drugbank_all_full_database.xml.zip"
OUTPUT_CSV = KB_DIR / "drug_interactions_prepared.csv"


NS = {"db": "http://www.drugbank.ca"}


def normalize_space(value: str) -> str:
    value = str(value or "").strip()
    return re.sub(r"\s+", " ", value)


def infer_severity(description: str) -> str:
    text = description.lower()
    if any(term in text for term in ["contraindicated", "life-threatening", "fatal"]):
        return "high"
    if any(term in text for term in ["serious", "significant", "major", "severe"]):
        return "moderate"
    if any(term in text for term in ["monitor", "adjust", "caution", "increase", "decrease"]):
        return "moderate"
    return "unknown"


def extract_drugbank_id(drug_elem: ET.Element) -> str:
    for dbid in drug_elem.findall("db:drugbank-id", NS):
        if dbid.attrib.get("primary") == "true":
            return normalize_space(dbid.text)
    first = drug_elem.find("db:drugbank-id", NS)
    return normalize_space(first.text if first is not None else "")


def extract_external_ids(drug_elem: ET.Element) -> str:
    values = []
    for ext in drug_elem.findall("db:external-identifiers/db:external-identifier", NS):
        resource = normalize_space(ext.findtext("db:resource", default="", namespaces=NS))
        identifier = normalize_space(ext.findtext("db:identifier", default="", namespaces=NS))
        if resource and identifier:
            values.append(f"{resource}:{identifier}")
    return " | ".join(values[:20])


def iter_interaction_rows(xml_file) -> list[dict]:
    rows = []
    context = ET.iterparse(xml_file, events=("end",))
    for _, elem in context:
        if not elem.tag.endswith("drug"):
            continue

        name = normalize_space(elem.findtext("db:name", default="", namespaces=NS))
        drugbank_id = extract_drugbank_id(elem)
        generic_name = normalize_space(elem.findtext("db:international-brands/db:international-brand/db:name", default="", namespaces=NS))
        if not generic_name:
            generic_name = name

        for interaction in elem.findall("db:drug-interactions/db:drug-interaction", NS):
            interacting_drug = normalize_space(interaction.findtext("db:name", default="", namespaces=NS))
            interaction_description = normalize_space(interaction.findtext("db:description", default="", namespaces=NS))
            interacting_drugbank_id = normalize_space(
                interaction.findtext("db:drugbank-id", default="", namespaces=NS)
            )
            if not interacting_drug or not interaction_description:
                continue

            rows.append(
                {
                    "drug_name": name,
                    "generic_name": generic_name,
                    "drugbank_id": drugbank_id,
                    "interacting_drug": interacting_drug,
                    "interacting_drugbank_id": interacting_drugbank_id,
                    "interaction_severity": infer_severity(interaction_description),
                    "interaction_text": interaction_description,
                    "external_ids": extract_external_ids(elem),
                    "source": "DrugBank",
                    "structured_text": (
                        f"TYPE: DRUG_INTERACTION\n"
                        f"DRUG_NAME: {name}\n"
                        f"GENERIC_NAME: {generic_name}\n"
                        f"DRUGBANK_ID: {drugbank_id}\n"
                        f"INTERACTING_DRUG: {interacting_drug}\n"
                        f"INTERACTING_DRUGBANK_ID: {interacting_drugbank_id}\n"
                        f"SEVERITY: {infer_severity(interaction_description)}\n"
                        f"DETAILS: {interaction_description}\n"
                        f"SOURCE: DrugBank"
                    ),
                }
            )

        elem.clear()

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare DrugBank DDI data from the full XML zip.")
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of rows to write for testing.")
    args = parser.parse_args()

    with zipfile.ZipFile(ZIP_PATH) as zf:
        xml_name = zf.namelist()[0]
        with zf.open(xml_name) as xml_file:
            rows = iter_interaction_rows(xml_file)

    if args.limit:
        rows = rows[: args.limit]

    fieldnames = [
        "drug_name",
        "generic_name",
        "drugbank_id",
        "interacting_drug",
        "interacting_drugbank_id",
        "interaction_severity",
        "interaction_text",
        "external_ids",
        "source",
        "structured_text",
    ]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"OK: Prepared DrugBank DDI data -> {OUTPUT_CSV} | rows={len(rows)}")


if __name__ == "__main__":
    main()
