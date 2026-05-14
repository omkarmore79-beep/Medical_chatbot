import argparse
import csv
import os
from pathlib import Path


KB_DIR = Path("knowledge_base")
README = KB_DIR / "drugbank_ddi_README.txt"
TEMPLATE = KB_DIR / "drugbank_ddi_template.csv"


README_TEXT = """DrugBank dedicated DDI data was not downloaded automatically.

Reason:
- DrugBank interaction data requires a DrugBank license and authenticated access.
- No DrugBank credentials were configured in this environment.

Expected next step:
1. Obtain DrugBank access or export a DrugBank interaction file.
2. Place the export in the knowledge_base folder.
3. Transform it into the schema shown in drugbank_ddi_template.csv.

Suggested columns:
- drug_name
- generic_name
- interacting_drug
- interaction_severity
- interaction_text
- source

If you later configure credentials, this script can be extended to fetch directly from the DrugBank API.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create local DrugBank DDI placeholders and credential note.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing placeholder files.")
    args = parser.parse_args()

    creds_present = any(
        os.getenv(key) for key in ["DRUGBANK_API_KEY", "DRUGBANK_USERNAME", "DRUGBANK_PASSWORD"]
    )
    if creds_present:
        print("INFO: DrugBank credentials detected, but direct API download is not implemented yet.")

    if args.overwrite or not README.exists():
        README.write_text(README_TEXT, encoding="utf-8")

    if args.overwrite or not TEMPLATE.exists():
        with TEMPLATE.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "drug_name",
                    "generic_name",
                    "interacting_drug",
                    "interaction_severity",
                    "interaction_text",
                    "source",
                ]
            )
            writer.writerow(
                [
                    "azithromycin",
                    "azithromycin",
                    "terfenadine",
                    "life-threatening",
                    "Example template row. Replace with licensed DrugBank data.",
                    "DrugBank",
                ]
            )

    print(f"OK: Wrote {README}")
    print(f"OK: Wrote {TEMPLATE}")


if __name__ == "__main__":
    main()
