import json
import re
from pathlib import Path

import pandas as pd


KB_DIR = Path("knowledge_base")
RAW_JSONL = KB_DIR / "dailymed_raw.jsonl"
PREPARED_CSV = KB_DIR / "dailymed_prepared.csv"


def normalize_space(value: str) -> str:
    value = str(value or "").strip()
    return re.sub(r"\s+", " ", value)


def main() -> None:
    rows = []
    with RAW_JSONL.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            source_term = normalize_space(item.get("_source_term", ""))
            search_result = item.get("search_result", {}) or {}
            packaging = item.get("packaging", {}) or {}

            setid = normalize_space(packaging.get("setid") or search_result.get("setid"))
            title = normalize_space(packaging.get("title") or search_result.get("title"))
            published_date = normalize_space(packaging.get("published_date") or search_result.get("published_date"))

            for product in packaging.get("products", []) or []:
                product_name = normalize_space(product.get("product_name"))
                generic_name = normalize_space(product.get("product_name_generic"))
                ingredients = []
                strengths = []
                ndcs = []
                package_desc = []

                for ingredient in product.get("active_ingredients", []) or []:
                    name = normalize_space(ingredient.get("name"))
                    strength = normalize_space(ingredient.get("strength"))
                    if name:
                        ingredients.append(name)
                    if strength:
                        strengths.append(strength)

                for package in product.get("packaging", []) or []:
                    ndc = normalize_space(package.get("ndc"))
                    if ndc:
                        ndcs.append(ndc)
                    for desc in package.get("package_descriptions", []) or []:
                        desc = normalize_space(desc)
                        if desc:
                            package_desc.append(desc)

                rows.append(
                    {
                        "source": "DailyMed",
                        "source_term": source_term,
                        "setid": setid,
                        "title": title,
                        "published_date": published_date,
                        "product_name": product_name,
                        "generic_name": generic_name,
                        "active_ingredients": " | ".join(ingredients),
                        "strengths": " | ".join(strengths),
                        "ndcs": " | ".join(ndcs),
                        "package_descriptions": " | ".join(package_desc),
                        "structured_text": (
                            f"TYPE: DAILMED_PRODUCT\n"
                            f"PRODUCT_NAME: {product_name}\n"
                            f"GENERIC_NAME: {generic_name}\n"
                            f"ACTIVE_INGREDIENTS: {' | '.join(ingredients)}\n"
                            f"STRENGTHS: {' | '.join(strengths)}\n"
                            f"NDCS: {' | '.join(ndcs)}\n"
                            f"PACKAGE_DESCRIPTIONS: {' | '.join(package_desc)}\n"
                            f"PUBLISHED_DATE: {published_date}\n"
                            f"TITLE: {title}\n"
                            f"SETID: {setid}\n"
                            f"SOURCE: DailyMed"
                        ),
                    }
                )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["setid", "product_name", "generic_name", "ndcs"], keep="first")
    df.to_csv(PREPARED_CSV, index=False, encoding="utf-8")
    print(f"OK: Prepared DailyMed data -> {PREPARED_CSV} | rows={len(df)}")


if __name__ == "__main__":
    main()
