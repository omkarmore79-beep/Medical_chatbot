import argparse
import os
import re

import pandas as pd
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from brand_mapping import brand_to_generic


KB_DIR = "knowledge_base"

SYMPTOM_FILE = os.path.join(KB_DIR, "symptom_kb_prepared.csv")
SYMPTOM_FILE_FALLBACK = os.path.join(KB_DIR, "symptom_kb.csv")
SYMPTOM_NL_FILE = os.path.join(KB_DIR, "symptom_to_diagnosis_prepared.csv")

DRUG_FILE = os.path.join(KB_DIR, "Comprehensive_Medicine_Database.xlsx")
MEDQA_FILE = os.path.join(KB_DIR, "medquad_prepared.csv")
MEDQA_FILE_FALLBACK = os.path.join(KB_DIR, "medquad.csv")

INDIAN_MEDICINE_FILE = os.path.join(KB_DIR, "updated_indian_medicine_data_prepared.csv")
INDIAN_MEDICINE_FILE_FALLBACK = os.path.join(KB_DIR, "updated_indian_medicine_data.csv")
BRAND_INDEX_XLSX = os.path.join(KB_DIR, "Comprehensive_Medicine_Brand_Index.xlsx")
BRAND_INDEX_CSV = os.path.join(KB_DIR, "Comprehensive_Medicine_Brand_Index_expanded.csv")
BRAND_INDEX_CSV_FALLBACK = os.path.join(KB_DIR, "Comprehensive_Medicine_Brand_Index.csv")

RXNORM_FILE = os.path.join(KB_DIR, "rxnorm_concepts.csv")
OPENFDA_FILE = os.path.join(KB_DIR, "openfda_drug_label_prepared.csv")
DAILYMED_FILE = os.path.join(KB_DIR, "dailymed_prepared.csv")
INTERACTIONS_FILE = os.path.join(KB_DIR, "drug_interactions_prepared.csv")
LAB_REFS_FILE = os.path.join(KB_DIR, "lab_reference_aliases.csv")


VS_SYMPTOMS = "vectorstore_symptoms"
VS_SYMPTOM_NL = "vectorstore_symptom_nl"
VS_DRUGS = "vectorstore_drugs"
VS_MEDQA = "vectorstore_medqa"
VS_INDIAN_MEDICINE = "vectorstore_indian_medicine"
VS_RXNORM = "vectorstore_rxnorm"
VS_DRUG_LABELS = "vectorstore_drug_labels"
VS_INTERACTIONS = "vectorstore_interactions"
VS_LAB_REFS = "vectorstore_lab_refs"


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={"normalize_embeddings": True},
)


def row_to_structured_text(row: pd.Series) -> str:
    if "structured_text" in row.index:
        structured = str(row["structured_text"]).strip()
        if structured and structured.lower() != "nan":
            return structured

    parts = []
    for col in row.index:
        value = str(row[col]).strip()
        if value and value.lower() != "nan":
            parts.append(f"{col}: {value}")
    return "\n".join(parts)


def _read_csv_with_fallback(path: str, **kwargs) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8", **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **kwargs)


def build_vectorstore_from_dataframe(df: pd.DataFrame, out_dir: str, domain: str):
    df = df.fillna("")
    docs = []

    for i, row in df.iterrows():
        docs.append(
            Document(
                page_content=row_to_structured_text(row),
                metadata={
                    "domain": domain,
                    "row_id": int(i),
                },
            )
        )

    if not docs:
        print(f"WARN: No rows for {out_dir}. Skipping save.")
        return

    db = FAISS.from_documents(docs, embeddings)
    db.save_local(out_dir)
    print(f"OK: Saved {out_dir} | Docs: {len(docs)}")


def load_brand_index_df() -> pd.DataFrame:
    if os.path.exists(BRAND_INDEX_XLSX):
        return pd.read_excel(BRAND_INDEX_XLSX)

    if os.path.exists(BRAND_INDEX_CSV):
        return _read_csv_with_fallback(BRAND_INDEX_CSV)

    if os.path.exists(BRAND_INDEX_CSV_FALLBACK):
        return _read_csv_with_fallback(BRAND_INDEX_CSV_FALLBACK)

    print(f"WARN: Brand index not found: {BRAND_INDEX_XLSX} or {BRAND_INDEX_CSV}")
    return pd.DataFrame()


def build_brand_index_documents(df: pd.DataFrame):
    if df.empty:
        return []

    df.columns = [str(c).strip().lower() for c in df.columns]
    required = ["brand", "generic", "aliases", "form", "strength"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"WARN: Brand index missing columns: {missing}")
        return []

    docs = []
    for i, row in df.fillna("").iterrows():
        brand = str(row["brand"]).strip()
        generic = str(row["generic"]).strip()
        aliases = str(row["aliases"]).strip()
        form = str(row["form"]).strip()
        strength = str(row["strength"]).strip()

        if not brand or not generic:
            continue

        docs.append(
            Document(
                page_content=(
                    f"TYPE: BRAND_INDEX\n"
                    f"Brand: {brand}\n"
                    f"Generic: {generic}\n"
                    f"Aliases: {aliases}\n"
                    f"Form: {form}\n"
                    f"Strength: {strength}"
                ),
                metadata={
                    "domain": "indian_medicine",
                    "source": "brand_index",
                    "row_id": int(i),
                    "brand": brand,
                    "generic": generic,
                    "form": form,
                },
            )
        )

    return docs


def build_indian_medicine_vectorstore_with_brand_index():
    docs = []

    if os.path.exists(INDIAN_MEDICINE_FILE):
        try:
            df_ind = _read_csv_with_fallback(INDIAN_MEDICINE_FILE).fillna("")
            for i, row in df_ind.iterrows():
                docs.append(
                    Document(
                        page_content=row_to_structured_text(row),
                        metadata={
                            "domain": "indian_medicine",
                            "source": "updated_indian_medicine_data",
                            "row_id": int(i),
                        },
                    )
                )
        except Exception as e:
            print(f"WARN: Failed to load Indian medicine file: {e}")
    elif os.path.exists(INDIAN_MEDICINE_FILE_FALLBACK):
        try:
            df_ind = _read_csv_with_fallback(INDIAN_MEDICINE_FILE_FALLBACK).fillna("")
            for i, row in df_ind.iterrows():
                docs.append(
                    Document(
                        page_content=row_to_structured_text(row),
                        metadata={
                            "domain": "indian_medicine",
                            "source": "updated_indian_medicine_data",
                            "row_id": int(i),
                        },
                    )
                )
        except Exception as e:
            print(f"WARN: Failed to load fallback Indian medicine file: {e}")
    else:
        print(f"WARN: Indian medicine file not found: {INDIAN_MEDICINE_FILE}")

    try:
        df_brand = load_brand_index_df()
        brand_docs = build_brand_index_documents(df_brand)
        docs.extend(brand_docs)
        if brand_docs:
            print(f"OK: Brand index docs added: {len(brand_docs)}")
    except Exception as e:
        print(f"WARN: Failed to process brand index: {e}")

    if not docs:
        print("WARN: No documents available for VS_INDIAN_MEDICINE. Skipping save.")
        return

    db = FAISS.from_documents(docs, embeddings)
    db.save_local(VS_INDIAN_MEDICINE)
    print(f"OK: Saved {VS_INDIAN_MEDICINE} | Docs: {len(docs)}")


def _normalize_key(value: str) -> str:
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _local_medicine_terms() -> set[str]:
    terms = set()

    for brand, generic in brand_to_generic.items():
        for value in [brand, generic]:
            key = _normalize_key(value)
            if key:
                terms.add(key)

    if os.path.exists(INDIAN_MEDICINE_FILE):
        df = _read_csv_with_fallback(INDIAN_MEDICINE_FILE, usecols=["name", "generic_or_salt"]).fillna("")
        for col in ["name", "generic_or_salt"]:
            if col in df.columns:
                for value in df[col].tolist():
                    key = _normalize_key(value)
                    if key:
                        terms.add(key)

    if os.path.exists(RXNORM_FILE):
        df = _read_csv_with_fallback(RXNORM_FILE, usecols=["canonical_name", "generic_names", "brand_names"]).fillna("")
        for col in df.columns:
            for value in df[col].tolist():
                for item in str(value).split("|"):
                    key = _normalize_key(item)
                    if key:
                        terms.add(key)

    return terms


def build_symptoms_vectorstore():
    if os.path.exists(SYMPTOM_FILE):
        df_sym = _read_csv_with_fallback(SYMPTOM_FILE)
        build_vectorstore_from_dataframe(df_sym, VS_SYMPTOMS, "symptoms")
    elif os.path.exists(SYMPTOM_FILE_FALLBACK):
        df_sym = _read_csv_with_fallback(SYMPTOM_FILE_FALLBACK)
        build_vectorstore_from_dataframe(df_sym, VS_SYMPTOMS, "symptoms")
    else:
        print(f"WARN: Missing {SYMPTOM_FILE} and {SYMPTOM_FILE_FALLBACK}")


def build_symptom_nl_vectorstore():
    if os.path.exists(SYMPTOM_NL_FILE):
        df = _read_csv_with_fallback(SYMPTOM_NL_FILE)
        build_vectorstore_from_dataframe(df, VS_SYMPTOM_NL, "symptom_nl")
    else:
        print(f"WARN: Missing {SYMPTOM_NL_FILE}")


def build_drugs_vectorstore():
    if os.path.exists(DRUG_FILE):
        df_drug = pd.read_excel(DRUG_FILE)
        build_vectorstore_from_dataframe(df_drug, VS_DRUGS, "drugs")
    else:
        print(f"WARN: Missing {DRUG_FILE}")


def build_medqa_vectorstore():
    if os.path.exists(MEDQA_FILE):
        df_medqa = _read_csv_with_fallback(MEDQA_FILE)
        build_vectorstore_from_dataframe(df_medqa, VS_MEDQA, "medqa")
    elif os.path.exists(MEDQA_FILE_FALLBACK):
        df_medqa = _read_csv_with_fallback(MEDQA_FILE_FALLBACK)
        build_vectorstore_from_dataframe(df_medqa, VS_MEDQA, "medqa")
    else:
        print(f"WARN: Missing {MEDQA_FILE} and {MEDQA_FILE_FALLBACK}")


def build_rxnorm_vectorstore():
    if os.path.exists(RXNORM_FILE):
        df_rxnorm = _read_csv_with_fallback(RXNORM_FILE)
        build_vectorstore_from_dataframe(df_rxnorm, VS_RXNORM, "rxnorm")
    else:
        print(f"WARN: Missing {RXNORM_FILE}")


def build_drug_labels_vectorstore():
    frames = []

    if os.path.exists(OPENFDA_FILE):
        frames.append(_read_csv_with_fallback(OPENFDA_FILE))
    else:
        print(f"WARN: Missing {OPENFDA_FILE}")

    if os.path.exists(DAILYMED_FILE):
        frames.append(_read_csv_with_fallback(DAILYMED_FILE))
    else:
        print(f"WARN: Missing {DAILYMED_FILE}")

    if not frames:
        print("WARN: No drug label datasets available.")
        return

    df = pd.concat(frames, ignore_index=True).fillna("")
    if "structured_text" in df.columns:
        df = df.drop_duplicates(subset=["structured_text"], keep="first")
    build_vectorstore_from_dataframe(df, VS_DRUG_LABELS, "drug_labels")


def build_interactions_vectorstore():
    if not os.path.exists(INTERACTIONS_FILE):
        print(f"WARN: Missing {INTERACTIONS_FILE}")
        return

    usecols = [
        "drug_name",
        "generic_name",
        "interacting_drug",
        "interaction_severity",
        "interaction_text",
        "source",
        "structured_text",
    ]
    df = _read_csv_with_fallback(INTERACTIONS_FILE, usecols=usecols).fillna("")
    terms = _local_medicine_terms()

    def matches_local(row: pd.Series) -> bool:
        left = _normalize_key(row["drug_name"])
        generic = _normalize_key(row["generic_name"])
        right = _normalize_key(row["interacting_drug"])
        return left in terms or generic in terms or right in terms

    mask = df.apply(matches_local, axis=1)
    df = df[mask].copy()
    df = df.drop_duplicates(subset=["drug_name", "interacting_drug", "interaction_text"], keep="first")

    if len(df) > 250000:
        df = df.iloc[:250000].copy()
        print("WARN: Interaction dataset capped at 250000 docs for practical vectorstore size.")

    build_vectorstore_from_dataframe(df, VS_INTERACTIONS, "interactions")


def build_lab_refs_vectorstore():
    if os.path.exists(LAB_REFS_FILE):
        df = _read_csv_with_fallback(LAB_REFS_FILE)
        build_vectorstore_from_dataframe(df, VS_LAB_REFS, "lab_refs")
    else:
        print(f"WARN: Missing {LAB_REFS_FILE}")


def parse_args():
    parser = argparse.ArgumentParser(description="Build medical chatbot vectorstores.")
    parser.add_argument(
        "--domains",
        nargs="+",
        choices=[
            "symptoms",
            "symptom_nl",
            "drugs",
            "medqa",
            "indian",
            "rxnorm",
            "drug_labels",
            "interactions",
            "lab_refs",
            "all",
        ],
        default=["all"],
        help="Specific vectorstore domains to rebuild.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    domains = args.domains
    if "all" in domains:
        domains = [
            "symptoms",
            "symptom_nl",
            "drugs",
            "medqa",
            "indian",
            "rxnorm",
            "drug_labels",
            "interactions",
            "lab_refs",
        ]

    if "symptoms" in domains:
        build_symptoms_vectorstore()

    if "symptom_nl" in domains:
        build_symptom_nl_vectorstore()

    if "drugs" in domains:
        build_drugs_vectorstore()

    if "medqa" in domains:
        build_medqa_vectorstore()

    if "indian" in domains:
        build_indian_medicine_vectorstore_with_brand_index()

    if "rxnorm" in domains:
        build_rxnorm_vectorstore()

    if "drug_labels" in domains:
        build_drug_labels_vectorstore()

    if "interactions" in domains:
        build_interactions_vectorstore()

    if "lab_refs" in domains:
        build_lab_refs_vectorstore()

    print(f"DONE: Vectorstore build finished for {', '.join(domains)}")


if __name__ == "__main__":
    main()
