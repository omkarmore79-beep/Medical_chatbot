import os
import re
import logging
from typing import Dict, List, Tuple

from dotenv import load_dotenv

from brand_mapping import brand_to_generic as MASTER_BRAND_TO_GENERIC


load_dotenv()

logger = logging.getLogger(__name__)

_emb = None
_gemini_client = None


VS_SYMPTOMS = "vectorstore_symptoms"
VS_SYMPTOM_NL = "vectorstore_symptom_nl"
VS_MEDQA = "vectorstore_medqa"
VS_INDIAN_MEDICINE = "vectorstore_indian_medicine"
VS_RXNORM = "vectorstore_rxnorm"
VS_DRUG_LABELS = "vectorstore_drug_labels"
VS_INTERACTIONS = "vectorstore_interactions"
VS_LAB_REFS = "vectorstore_lab_refs"
INTERACTIONS_FILE = os.path.join("knowledge_base", "drug_interactions_prepared.csv")
INDIAN_MEDICINE_PREPARED_FILE = os.path.join("knowledge_base", "updated_indian_medicine_data_prepared.csv")


_db_sym = None
_db_sym_nl = None
_db_qa = None
_db_indian = None
_db_rxnorm = None
_db_drug_labels = None
_db_interactions = None
_db_lab_refs = None
_interaction_pair_cache = {}
_local_medicine_cache = None


def get_pandas():
    # Render stability change: pandas is only imported when CSV fallback data
    # is needed for an actual request.
    import pandas as pd

    return pd


def get_embeddings():
    global _emb
    if _emb is None:
        # Render stability change: do not load the SentenceTransformer during
        # module import. The embedding model is created on the first RAG request.
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info("Model loading started: HuggingFaceEmbeddings all-MiniLM-L6-v2")
        _emb = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        logger.info("Model loading completed: HuggingFaceEmbeddings all-MiniLM-L6-v2")
    return _emb


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        # Render stability change: keep API client creation lazy as well.
        from google import genai

        logger.info("Model loading started: Gemini client")
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        logger.info("Model loading completed: Gemini client")
    return _gemini_client


def _load_faiss_store(path: str):
    from langchain_community.vectorstores import FAISS

    store = FAISS.load_local(
        path,
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )
    logger.info("FAISS loading completed: %s", path)
    return store


brand_to_generic = {
    "dolo 650": "paracetamol",
    "dolo 500": "paracetamol",
    "crocin": "paracetamol",
    "calpol": "paracetamol",
    "combiflam": "ibuprofen paracetamol",
    "glycomet": "metformin",
    "janumet": "sitagliptin metformin",
    "amlong": "amlodipine",
    "telma": "telmisartan",
    "losar": "losartan",
    "atorva": "atorvastatin",
    "thyronorm": "levothyroxine",
    "pantocid": "pantoprazole",
    "omez": "omeprazole",
    "augmentin": "amoxicillin clavulanic acid",
    "azithral": "azithromycin",
    "montek lc": "montelukast levocetirizine",
    "asthalin": "salbutamol",
    "lasix": "furosemide",
    "lantus": "insulin glargine",
    "alprax": "alprazolam",
    "shelcal": "calcium vitamin d3",
    "neurobion forte": "vitamin b1 b6 b12",
}
brand_to_generic.update(MASTER_BRAND_TO_GENERIC)


EMERGENCY_KEYWORDS = [
    "chest pain", "tightness in chest", "shortness of breath", "difficulty breathing",
    "can't breathe", "cannot breathe", "unconscious", "severe bleeding", "heart attack",
    "stroke", "seizure", "fainting", "overdose", "poisoning", "suicidal",
    "vomited blood", "vomiting blood", "blood in vomit", "throat swelling",
    "swelling of throat", "swelling of my throat", "swelling of lips", "lip swelling",
    "severe allergic swelling", "anaphylaxis", "severe dehydration",
    "unable to keep fluids", "pain going to my left arm",
]

DRUG_QUERY_KEYWORDS = [
    "tablet", "capsule", "syrup", "medicine", "medication", "drug", "dose", "dosage",
    "side effect", "side effects", "interaction", "interact", "precaution", "uses",
    "used for", "take", "taken", "brand", "generic", "prescription",
    "dose form", "strength", "ingredient", "composition", "active ingredient",
]

SYMPTOM_QUERY_KEYWORDS = [
    "symptom", "symptoms", "fever", "pain", "vomiting", "cough", "headache", "fatigue",
    "nausea", "rash", "cold", "flu", "body pain", "sore throat", "breathlessness",
    "runny nose", "loose motion", "diarrhea",
]

LAB_QUERY_KEYWORDS = [
    "lab", "report", "test result", "hemoglobin", "platelet", "sugar", "hba1c",
    "creatinine", "cholesterol", "tsh", "vitamin d",
]

INTERACTION_QUERY_KEYWORDS = [
    "interact", "interaction", "take together", "combine", "drug interaction", "can i take",
]

DRUG_SAFETY_KEYWORDS = [
    "side effect", "side effects", "warning", "warnings", "contraindication",
    "contraindications", "pregnancy", "breastfeeding", "lactation", "adverse reaction",
    "precaution", "precautions",
]

DRUG_PROPERTY_KEYWORDS = [
    "generic name", "brand name", "dose form", "strength", "ingredient", "composition", "active ingredient",
]

LAB_REPORT_ACTION_KEYWORDS = [
    "upload", "uploaded", "my report", "my lab report", "analyze report", "analyze my report",
]

NAME_EQUIVALENTS = {
    "paracetamol": "acetaminophen",
    "acetaminophen": "paracetamol",
    "amoxycillin": "amoxicillin",
    "amoxicillin clavulanic acid": "amoxicillin clavulanate",
    "levocetirizine": "levocetirizine dihydrochloride",
    "aspirin": "acetylsalicylic acid",
    "acetylsalicylic acid": "aspirin",
}

SAFE_GENERIC_OVERRIDES = {
    "azithromycin": "azithromycin",
    "warfarin": "warfarin",
    "aspirin": "aspirin",
    "montelukast": "montelukast",
    "levocetirizine": "levocetirizine",
    "terfenadine": "terfenadine",
}


def load_dbs():
    global _db_sym, _db_sym_nl, _db_qa, _db_indian, _db_rxnorm, _db_drug_labels, _db_interactions, _db_lab_refs

    if all(
        db is not None
        for db in (
            _db_sym,
            _db_sym_nl,
            _db_qa,
            _db_indian,
            _db_rxnorm,
            _db_drug_labels,
            _db_interactions,
            _db_lab_refs,
        )
    ):
        return

    # Render stability change: vector indexes are loaded only when an endpoint
    # first needs RAG, so uvicorn can bind port 10000 immediately.
    logger.info("Model loading started: FAISS vector stores")

    if _db_sym is None:
        _db_sym = _load_faiss_store(VS_SYMPTOMS)

    if _db_sym_nl is None:
        _db_sym_nl = _load_faiss_store(VS_SYMPTOM_NL)

    if _db_qa is None:
        _db_qa = _load_faiss_store(VS_MEDQA)

    if _db_indian is None:
        _db_indian = _load_faiss_store(VS_INDIAN_MEDICINE)

    if _db_rxnorm is None:
        _db_rxnorm = _load_faiss_store(VS_RXNORM)

    if _db_drug_labels is None:
        _db_drug_labels = _load_faiss_store(VS_DRUG_LABELS)

    if _db_interactions is None:
        _db_interactions = _load_faiss_store(VS_INTERACTIONS)

    if _db_lab_refs is None:
        _db_lab_refs = _load_faiss_store(VS_LAB_REFS)

    logger.info("Model loading completed: FAISS vector stores")


def _normalize_key(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _build_drug_terms():
    terms = set()
    for brand, generic in brand_to_generic.items():
        for item in [brand, generic]:
            text = _normalize_key(item)
            if len(text) >= 4:
                terms.add(text)
            for token in text.split():
                if len(token) >= 5:
                    terms.add(token)
    return sorted(terms, key=len, reverse=True)


DRUG_TERMS = _build_drug_terms()


def normalize_brand_names(query: str) -> str:
    q = query.lower()
    for brand, generic in brand_to_generic.items():
        if brand.lower() in SAFE_GENERIC_OVERRIDES:
            continue
        pattern = r"\b" + re.escape(brand.lower()) + r"\b"
        q = re.sub(pattern, generic.lower(), q)
    for source, target in SAFE_GENERIC_OVERRIDES.items():
        pattern = r"\b" + re.escape(source.lower()) + r"\b"
        q = re.sub(pattern, target.lower(), q)
    for source, target in NAME_EQUIVALENTS.items():
        pattern = r"\b" + re.escape(source.lower()) + r"\b"
        q = re.sub(pattern, target.lower(), q)
    return re.sub(r"\s+", " ", q).strip()


def detect_emergency(query: str) -> bool:
    q = query.lower()
    return any(word in q for word in EMERGENCY_KEYWORDS)


def emergency_response() -> str:
    return (
        "MEDICAL EMERGENCY DETECTED\n\n"
        "Your symptoms may indicate a serious or life-threatening condition.\n\n"
        "Please seek immediate medical attention:\n"
        "- Call 108 (Ambulance - India)\n"
        "- Call 112 (National Emergency Helpline - India)\n\n"
        "This AI system cannot provide emergency medical assistance."
    )


def _keyword_hits(query: str, keywords: List[str]) -> int:
    q = query.lower()
    return sum(1 for keyword in keywords if keyword in q)


def _find_drug_terms(query: str) -> List[str]:
    q = _normalize_key(query)
    hits = []
    for term in DRUG_TERMS:
        if term in q:
            hits.append(term)
        if len(hits) >= 8:
            break
    return hits


def _contains_any(query: str, keywords: List[str]) -> bool:
    q = query.lower()
    return any(keyword in q for keyword in keywords)


def _extract_interaction_pair(query: str) -> Tuple[str, str]:
    q = normalize_brand_names(query.lower())
    patterns = [
        r"does\s+(.+?)\s+interact\s+with\s+(.+?)(?:\?|$)",
        r"can i take\s+(.+?)\s+with\s+(.+?)(?:\?|$)",
        r"can i take\s+(.+?)\s+and\s+(.+?)\s+together(?:\?|$)",
        r"can i take\s+(.+?)\s+and\s+(.+?)(?:\?|$)",
        r"interaction between\s+(.+?)\s+and\s+(.+?)(?:\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            left = _normalize_key(_clean_medicine_phrase(match.group(1)))
            right = _normalize_key(_clean_medicine_phrase(match.group(2)))
            return left, right
    return "", ""


def _name_candidates(name: str) -> set:
    candidates = {name}
    if name in NAME_EQUIVALENTS:
        candidates.add(_normalize_key(NAME_EQUIVALENTS[name]))
    reverse = {v: k for k, v in NAME_EQUIVALENTS.items()}
    if name in reverse:
        candidates.add(_normalize_key(reverse[name]))
    return {item for item in candidates if item}


def _load_local_medicine_cache():
    global _local_medicine_cache
    if _local_medicine_cache is not None:
        return _local_medicine_cache

    _local_medicine_cache = {}
    if not os.path.exists(INDIAN_MEDICINE_PREPARED_FILE):
        return _local_medicine_cache

    usecols = [
        "name",
        "generic_or_salt",
        "uses",
        "description",
        "side_effects_list",
    ]
    pd = get_pandas()
    df = pd.read_csv(INDIAN_MEDICINE_PREPARED_FILE, usecols=usecols).fillna("")
    for _, row in df.iterrows():
        entry = {col: str(row[col]).strip() for col in usecols}
        keys = {
            _normalize_key(entry["name"]),
            _normalize_key(entry["generic_or_salt"]),
        }
        for key in list(keys):
            if not key:
                continue
            if key not in _local_medicine_cache:
                _local_medicine_cache[key] = entry
    return _local_medicine_cache


def _extract_local_medicine_name(query: str) -> str:
    q_variants = [
        _normalize_key(query.lower()),
        _normalize_key(normalize_brand_names(query.lower())),
    ]
    cache = _load_local_medicine_cache()
    matches = []
    for key in cache.keys():
        if key and any(key in q for q in q_variants):
            matches.append(key)
    if not matches:
        return ""
    return max(matches, key=len)


def _clean_medicine_phrase(value: str) -> str:
    value = str(value).lower()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml)\b", " ", value)
    value = re.sub(r"\b\d+\b", " ", value)
    value = re.sub(
        r"\b(tablet|tab|capsule|cap|injection|inj|syrup|suspension|oral|dry|drop|drops|cream|gel|ointment|duo|ds|forte)\b",
        " ",
        value,
    )
    value = re.sub(r"[^a-z0-9\s+]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _split_generic_components(value: str) -> List[str]:
    cleaned = _clean_medicine_phrase(value)
    if not cleaned:
        return []
    parts = re.split(r"\s+\+\s+|\+", cleaned)
    components = []
    for part in parts:
        part = _normalize_key(part)
        if part:
            components.append(part)
            if part in NAME_EQUIVALENTS:
                components.append(_normalize_key(NAME_EQUIVALENTS[part]))
    return list(dict.fromkeys(components))


def _get_local_medicine_entry(query: str) -> Dict[str, str]:
    key = _extract_local_medicine_name(query)
    if not key:
        return {}
    return _load_local_medicine_cache().get(key, {})


def _format_side_effects_list(value: str) -> str:
    value = str(value).strip()
    if not value:
        return ""
    value = re.sub(r'^\[|\]$', "", value)
    value = value.replace('"', "").replace("'", "")
    value = re.sub(r"\s*,\s*", ", ", value)
    return value.strip(", ")


def _local_medicine_answer(query: str) -> str:
    q = query.lower()
    entry = _get_local_medicine_entry(query)
    if not entry:
        return ""

    medicine_name = entry.get("name", "This medicine")
    generic_name = entry.get("generic_or_salt", "")
    uses = entry.get("uses", "")
    description = entry.get("description", "")
    side_effects = _format_side_effects_list(entry.get("side_effects_list", ""))

    if _contains_any(q, ["side effect", "side effects", "adverse reaction"]):
        if side_effects:
            answer = f"Common side effects of {medicine_name} are: {side_effects}."
            if generic_name:
                answer += f" It contains {generic_name}."
            return answer

    if "generic name" in q or _contains_any(q, ["ingredient", "composition", "active ingredient"]):
        if generic_name:
            return f"{medicine_name} contains {generic_name}."

    if _contains_any(q, ["used for", "uses"]):
        if uses:
            return f"{medicine_name} is used for {uses}"
        if description:
            return _extract_first_sentences(description, 2)

    return ""


def _chunk_exact_interaction_lookup(left: str, right: str):
    if not left or not right or not os.path.exists(INTERACTIONS_FILE):
        return None

    cache_key = tuple(sorted((left, right)))
    if cache_key in _interaction_pair_cache:
        return _interaction_pair_cache[cache_key]

    left_candidates = _name_candidates(left)
    right_candidates = _name_candidates(right)

    usecols = [
        "drug_name",
        "generic_name",
        "interacting_drug",
        "interaction_severity",
        "interaction_text",
    ]

    pd = get_pandas()
    for chunk in pd.read_csv(INTERACTIONS_FILE, usecols=usecols, chunksize=100000):
        normalized = pd.DataFrame(
            {
                "drug_name": chunk["drug_name"].fillna("").map(_normalize_key),
                "generic_name": chunk["generic_name"].fillna("").map(_normalize_key),
                "interacting_drug": chunk["interacting_drug"].fillna("").map(_normalize_key),
            }
        )
        mask = (
            (
                normalized["drug_name"].isin(left_candidates | right_candidates)
                | normalized["generic_name"].isin(left_candidates | right_candidates)
            )
            & (
                (normalized["drug_name"].isin(left_candidates) | normalized["generic_name"].isin(left_candidates))
                & normalized["interacting_drug"].isin(right_candidates)
                |
                (normalized["drug_name"].isin(right_candidates) | normalized["generic_name"].isin(right_candidates))
                & normalized["interacting_drug"].isin(left_candidates)
            )
        )

        if mask.any():
            row = chunk[mask].iloc[0].fillna("")
            result = {
                "drug_name": str(row["drug_name"]).strip(),
                "generic_name": str(row["generic_name"]).strip(),
                "interacting_drug": str(row["interacting_drug"]).strip(),
                "interaction_severity": str(row["interaction_severity"]).strip(),
                "interaction_text": str(row["interaction_text"]).strip(),
            }
            _interaction_pair_cache[cache_key] = result
            return result

    _interaction_pair_cache[cache_key] = None
    return None


def _interaction_pair_answer(query: str) -> str:
    left, right = _extract_interaction_pair(query)
    if not left or not right:
        return ""

    exact_interaction = _chunk_exact_interaction_lookup(left, right)
    if exact_interaction:
        return (
            f"Yes, {exact_interaction['drug_name']} interacts with {exact_interaction['interacting_drug']}. "
            f"Severity: {exact_interaction['interaction_severity']}. "
            f"Details: {exact_interaction['interaction_text']}"
        )

    left_entry = _get_local_medicine_entry(left)
    right_entry = _get_local_medicine_entry(right)
    left_name = left_entry.get("name") or left.title()
    right_name = right_entry.get("name") or right.title()

    left_generic = left_entry.get("generic_or_salt", "")
    right_generic = right_entry.get("generic_or_salt", "")

    if left_generic:
        left_name = f"{left_name} ({left_generic})"
    if right_generic:
        right_name = f"{right_name} ({right_generic})"

    return (
        f"I cannot confidently confirm a direct interaction between {left_name} and {right_name} from the available information. "
        "That does not mean the combination is safe. Please confirm with your doctor or pharmacist, "
        "especially if this was not prescribed together."
    )


def classify_query(query: str) -> Tuple[str, Dict[str, int]]:
    q = query.lower()
    scores = {
        "drugs": 0,
        "symptoms": 0,
        "medqa": 0,
        "lab": 0,
    }

    drug_terms = _find_drug_terms(q)
    scores["drugs"] += min(len(drug_terms) * 2, 8)
    scores["drugs"] += _keyword_hits(q, DRUG_QUERY_KEYWORDS)
    if _keyword_hits(q, DRUG_PROPERTY_KEYWORDS):
        scores["drugs"] += 2

    scores["symptoms"] += _keyword_hits(q, SYMPTOM_QUERY_KEYWORDS)
    if re.search(r"\bi have\b|\bim having\b|\bmy\b|\bfeeling\b", q):
        scores["symptoms"] += 1

    scores["lab"] += _keyword_hits(q, LAB_QUERY_KEYWORDS)
    if _contains_any(q, LAB_QUERY_KEYWORDS):
        scores["lab"] += 2
    scores["medqa"] += 1
    if any(phrase in q for phrase in ["what is", "what causes", "how is", "treatment of", "risk factors"]):
        scores["medqa"] += 2

    if detect_emergency(q):
        return "emergency", scores

    if scores["lab"] >= max(scores["drugs"], scores["symptoms"], scores["medqa"]) and scores["lab"] >= 2:
        return "lab", scores

    best_domain = max(("drugs", "symptoms", "medqa"), key=lambda item: scores[item])
    return best_domain, scores


def _query_variants(query: str, normalized_query: str, domain: str) -> List[str]:
    variants = [query]
    if normalized_query != query.lower():
        variants.append(normalized_query)

    if domain == "drugs":
        drug_terms = _find_drug_terms(query)
        if drug_terms:
            variants.append(" ".join(drug_terms))
        for source, target in NAME_EQUIVALENTS.items():
            if source in normalized_query:
                variants.append(normalized_query.replace(source, target))
            if target in normalized_query:
                variants.append(normalized_query.replace(target, source))

    return list(dict.fromkeys(v.strip() for v in variants if v.strip()))


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _lexical_score(query: str, text: str) -> float:
    q_tokens = _tokenize(query)
    t_tokens = _tokenize(text)
    if not q_tokens or not t_tokens:
        return 0.0

    overlap = len(q_tokens & t_tokens)
    score = overlap / len(q_tokens)
    if "TYPE: MEDICINE" in text and any(word in query.lower() for word in ["side effect", "interaction", "used for", "uses"]):
        score += 0.15
    if "TYPE: DRUG_LABEL" in text and _contains_any(query, DRUG_SAFETY_KEYWORDS):
        score += 0.25
    if "TYPE: DRUG_INTERACTION" in text and _contains_any(query, INTERACTION_QUERY_KEYWORDS):
        score += 0.35
    if "TYPE: RXNORM_MEDICATION" in text and _contains_any(query, DRUG_PROPERTY_KEYWORDS):
        score += 0.30
    if "TYPE: LAB_TEST" in text and _contains_any(query, LAB_QUERY_KEYWORDS):
        score += 0.25
    if "TYPE: MEDICAL_QA" in text and any(phrase in query.lower() for phrase in ["what is", "what causes", "how is"]):
        score += 0.10
    if "TYPE: SYMPTOM" in text:
        score += 0.05
    return score


def _candidate_dbs(domain: str, query: str):
    if domain == "drugs":
        if _contains_any(query, INTERACTION_QUERY_KEYWORDS):
            return [
                ("interactions", _db_interactions),
                ("drug_labels", _db_drug_labels),
                ("rxnorm", _db_rxnorm),
                ("indian_medicine", _db_indian),
            ]
        if _contains_any(query, DRUG_PROPERTY_KEYWORDS):
            return [
                ("rxnorm", _db_rxnorm),
                ("drug_labels", _db_drug_labels),
                ("indian_medicine", _db_indian),
            ]
        if _contains_any(query, DRUG_SAFETY_KEYWORDS):
            return [
                ("drug_labels", _db_drug_labels),
                ("indian_medicine", _db_indian),
                ("rxnorm", _db_rxnorm),
            ]
        return [
            ("rxnorm", _db_rxnorm),
            ("indian_medicine", _db_indian),
            ("drug_labels", _db_drug_labels),
        ]
    if domain == "symptoms":
        return [("symptom_nl", _db_sym_nl), ("symptoms", _db_sym), ("medqa", _db_qa)]
    if domain == "lab":
        return [("lab_refs", _db_lab_refs), ("medqa", _db_qa)]
    return [("medqa", _db_qa), ("symptoms", _db_sym)]


def _domain_db_bonus(domain: str, db_name: str, text: str) -> float:
    bonus = 0.0

    if domain == "symptoms":
        if db_name == "symptom_nl":
            bonus += 0.35
        if db_name == "symptoms":
            bonus += 0.30
        if "TYPE: SYMPTOM" in text:
            bonus += 0.20
        if "TYPE: SYMPTOM_NL" in text:
            bonus += 0.25

    if domain == "drugs":
        if db_name == "interactions":
            bonus += 0.40
        if db_name == "drug_labels":
            bonus += 0.30
        if db_name == "rxnorm":
            bonus += 0.30
        if db_name == "indian_medicine":
            bonus += 0.25
        if "TYPE: DRUG_INTERACTION" in text:
            bonus += 0.35
        if "TYPE: DRUG_LABEL" in text:
            bonus += 0.25
        if "TYPE: RXNORM_MEDICATION" in text:
            bonus += 0.25
        if "TYPE: MEDICINE" in text:
            bonus += 0.20

    if domain == "lab":
        if db_name == "lab_refs":
            bonus += 0.35
        if "TYPE: LAB_TEST" in text:
            bonus += 0.25

    if domain == "medqa" and db_name == "medqa":
        bonus += 0.15

    return bonus


def _query_store_bonus(query: str, db_name: str) -> float:
    bonus = 0.0
    if _contains_any(query, INTERACTION_QUERY_KEYWORDS):
        if db_name == "interactions":
            bonus += 0.45
        elif db_name == "drug_labels":
            bonus += 0.15
        elif db_name == "indian_medicine":
            bonus -= 0.10
    if _contains_any(query, DRUG_SAFETY_KEYWORDS):
        if db_name == "drug_labels":
            bonus += 0.35
        elif db_name == "indian_medicine":
            bonus -= 0.10
    if _contains_any(query, DRUG_PROPERTY_KEYWORDS):
        if db_name == "rxnorm":
            bonus += 0.55
        elif db_name == "drug_labels":
            bonus += 0.15
        elif db_name == "indian_medicine":
            bonus -= 0.15
    if _contains_any(query, LAB_QUERY_KEYWORDS):
        if db_name == "lab_refs":
            bonus += 0.30
    return bonus


def retrieve_context(query: str, normalized_query: str, domain: str, k: int = 8):
    if domain == "emergency":
        return emergency_response(), 0.99, "emergency", []

    variants = _query_variants(query, normalized_query, domain)
    seen_texts = set()
    candidates = []

    for db_name, db in _candidate_dbs(domain, normalized_query):
        for variant in variants:
            results = db.similarity_search_with_score(variant, k=k)
            for doc, score in results:
                text = doc.page_content.strip()
                text_key = text[:500]
                if not text or text_key in seen_texts:
                    continue
                seen_texts.add(text_key)

                lexical = _lexical_score(normalized_query, text)
                combined = lexical - min(float(score), 1000.0) / 1000.0
                combined += _domain_db_bonus(domain, db_name, text)
                combined += _query_store_bonus(normalized_query, db_name)
                candidates.append(
                    {
                        "db": db_name,
                        "text": text,
                        "score": float(score),
                        "lexical": lexical,
                        "combined": combined,
                    }
                )

    candidates = sorted(
        candidates,
        key=lambda item: (item["combined"], item["lexical"], -item["score"]),
        reverse=True,
    )
    top_results = candidates[:5]

    if not top_results:
        return "", 0.0, domain, []

    context = "\n\n---\n\n".join(item["text"] for item in top_results)
    lexical_avg = sum(item["lexical"] for item in top_results) / len(top_results)
    vector_component = sum(1 / (1 + max(item["score"], 0.0)) for item in top_results) / len(top_results)
    confidence = round(max(0.0, min(1.0, lexical_avg * 0.65 + vector_component * 0.35)), 3)

    return context, confidence, domain, top_results


def _extract_rxnorm_mappings(top_results: List[dict]) -> List[dict]:
    mappings = []
    for item in top_results:
        if item["db"] != "rxnorm":
            continue
        text = item["text"]

        def pick(label: str) -> str:
            match = re.search(rf"^{label}:\s*(.*)$", text, flags=re.MULTILINE)
            return match.group(1).strip() if match else ""

        mappings.append(
            {
                "canonical_name": pick("CANONICAL_NAME"),
                "generic_names": pick("GENERIC_NAMES"),
                "brand_names": pick("BRAND_NAMES"),
                "dose_forms": pick("DOSE_FORMS"),
                "strengths": pick("STRENGTHS"),
                "rxcui": pick("RXCUI"),
            }
        )
    return mappings[:3]


def _parse_field(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.*)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _first_nonempty(items: List[str]) -> str:
    for item in items:
        if item and item.strip():
            return item.strip()
    return ""


def _extract_first_sentences(text: str, count: int = 2) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:count]).strip()


def _strip_structured_prefix(text: str) -> str:
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    plain_lines = [line for line in lines if ":" not in line[:40]]
    if plain_lines:
        return " ".join(plain_lines).strip()
    return " ".join(lines).strip()


def _brand_generic_shortcut(query: str) -> str:
    q = query.lower()
    for brand, generic in brand_to_generic.items():
        if re.search(r"\b" + re.escape(brand.lower()) + r"\b", q):
            return f"The generic name of {brand.title()} is {generic}."
    return ""


def fallback_answer(query: str, domain: str, top_results: List[dict]) -> str:
    q = query.lower()
    texts = [item["text"] for item in top_results]

    if domain == "symptoms":
        for text in texts:
            possible = _first_nonempty([
                _parse_field(text, "POSSIBLE_CONDITION"),
                _parse_field(text, "DISEASE"),
            ])
            follow_up = _parse_field(text, "FOLLOW_UP_QUESTIONS")
            if possible:
                answer = f"A possible condition related to these symptoms is {possible}."
                if follow_up:
                    answer += f" Helpful follow-up questions: {follow_up}."
                answer += " This is educational guidance only and not a diagnosis."
                return answer

    if domain == "drugs":
        if "provide uses, common side effects, and key precautions" in q:
            uses_value = ""
            side_effects_value = ""
            precaution_value = ""
            for text in texts:
                if not uses_value:
                    uses_value = _first_nonempty([
                        _parse_field(text, "USES"),
                        _parse_field(text, "GENERIC_OR_SALT"),
                    ])
                    if not uses_value and _parse_field(text, "SECTION") == "indications_and_usage":
                        uses_value = _extract_first_sentences(_parse_field(text, "CONTENT"), 2)

                if not side_effects_value:
                    side_effects_value = _parse_field(text, "SIDE_EFFECTS")
                    if not side_effects_value and _parse_field(text, "SECTION") == "adverse_reactions":
                        side_effects_value = _extract_first_sentences(_parse_field(text, "CONTENT"), 2)

                if not precaution_value:
                    if _parse_field(text, "SECTION") in {"warnings", "contraindications", "precautions"}:
                        precaution_value = _extract_first_sentences(_parse_field(text, "CONTENT"), 2)

            parts = []
            if uses_value:
                parts.append(f"Uses: {uses_value}")
            if side_effects_value:
                parts.append(f"Common side effects: {side_effects_value}")
            if precaution_value:
                parts.append(f"Key precautions: {precaution_value}")
            if parts:
                return " ".join(parts)

        if "generic name" in q:
            shortcut = _brand_generic_shortcut(query)
            if shortcut:
                return shortcut
            for text in texts:
                generic = _parse_field(text, "GENERIC_NAMES") or _parse_field(text, "GENERIC_OR_SALT")
                canonical = _parse_field(text, "CANONICAL_NAME") or _parse_field(text, "NAME")
                if generic:
                    return f"The generic name information I found is: {generic}."
                if canonical:
                    return f"The medicine name information I found is: {canonical}."

        if _contains_any(q, INTERACTION_QUERY_KEYWORDS):
            for text in texts:
                interacting = _parse_field(text, "INTERACTING_DRUG")
                severity = _parse_field(text, "SEVERITY")
                details = _parse_field(text, "DETAILS")
                if interacting and details:
                    answer = f"Yes, there is a recorded interaction with {interacting}."
                    if severity:
                        answer += f" Severity: {severity}."
                    answer += f" Details: {details}"
                    return answer

        if _contains_any(q, ["side effect", "side effects", "adverse reaction"]):
            for text in texts:
                side_effects = _parse_field(text, "SIDE_EFFECTS")
                section = _parse_field(text, "SECTION")
                content = _parse_field(text, "CONTENT")
                if side_effects:
                    return f"Common side effects listed for this medicine include: {side_effects}."
                if section in {"adverse_reactions", "warnings"} and content:
                    return f"Relevant safety information from the current label data: {_extract_first_sentences(content, 3)}"

        if _contains_any(q, DRUG_SAFETY_KEYWORDS):
            for text in texts:
                section = _parse_field(text, "SECTION")
                content = _parse_field(text, "CONTENT")
                if section and content:
                    return f"{section.replace('_', ' ').title()}: {_extract_first_sentences(content, 3)}"

        if _contains_any(q, ["used for", "uses"]):
            for text in texts:
                uses = _parse_field(text, "USES")
                section = _parse_field(text, "SECTION")
                content = _parse_field(text, "CONTENT")
                if uses:
                    return f"This medicine is used for: {uses}"
                if section == "indications_and_usage" and content:
                    return f"According to the current label data, this medicine is used for: {_extract_first_sentences(content, 3)}"

        if _contains_any(q, DRUG_PROPERTY_KEYWORDS):
            for text in texts:
                if "dose form" in q:
                    value = _first_nonempty([
                        _parse_field(text, "DOSE_FORMS"),
                        _parse_field(text, "PACKAGE_DESCRIPTIONS"),
                    ])
                    if value:
                        return f"The dose form information I found is: {value}."
                if "strength" in q:
                    value = _first_nonempty([
                        _parse_field(text, "STRENGTHS"),
                        _parse_field(text, "AVAILABLE_STRENGTHS"),
                    ])
                    if value:
                        return f"The strength information I found is: {value}."
                if _contains_any(q, ["ingredient", "composition", "active ingredient"]):
                    value = _first_nonempty([
                        _parse_field(text, "ACTIVE_INGREDIENTS"),
                        _parse_field(text, "GENERIC_NAMES"),
                        _parse_field(text, "GENERIC_OR_SALT"),
                    ])
                    if value:
                        return f"The ingredient information I found is: {value}."

    if domain == "lab":
        for text in texts:
            display = _parse_field(text, "DISPLAY_NAME")
            unit = _parse_field(text, "UNIT")
            category = _parse_field(text, "CATEGORY")
            if display:
                answer = f"{display} is a laboratory test listed in the current reference data."
                if category:
                    answer += f" Category: {category}."
                if unit and "CATEGORY:" not in unit and "DISPLAY_NAME:" not in unit:
                    answer += f" Common unit(s): {unit}."
                return answer

    if domain == "medqa":
        for text in texts:
            answer_part = _first_nonempty([
                _parse_field(text, "ANSWER_PART_1_OF_1"),
                _parse_field(text, "ANSWER_PART_1_OF_2"),
                _parse_field(text, "ANSWER_PART_1_OF_3"),
                _parse_field(text, "ANSWER_PART_1_OF_4"),
                _parse_field(text, "ANSWER_PART_1_OF_5"),
            ])
            if answer_part:
                return _extract_first_sentences(answer_part, 3)
            return _extract_first_sentences(_strip_structured_prefix(text), 3)

    return "I cannot answer this confidently from the details available. Please ask with a little more detail or consult a qualified healthcare professional."


def generate_answer(query: str, context: str, domain: str) -> str:
    domain_instruction = {
        "drugs": (
            "Focus on medicine-specific facts such as uses, side effects, precautions, and interactions. "
            "If the context gives interaction severity, state it clearly."
        ),
        "symptoms": (
            "Provide a cautious educational answer, possible conditions only if clearly supported, "
            "and include appropriate follow-up questions or next steps. "
            "Use this exact plain-text structure with no Markdown, no asterisks, and no bold markers:\n"
            "SUMMARY: one short paragraph.\n"
            "POSSIBLE_CONDITIONS:\n"
            "- Condition name | short reason based on the user's symptoms.\n"
            "- Condition name | short reason based on the user's symptoms.\n"
            "FOLLOW_UP_QUESTIONS:\n"
            "1. Question.\n"
            "2. Question.\n"
            "3. Question.\n"
            "SAFETY_NOTE: educational disclaimer and emergency red flags."
        ),
        "medqa": (
            "Answer directly and concisely using the supplied evidence. Prefer short factual explanations."
        ),
        "lab": (
            "Answer general educational questions about lab tests, names, aliases, and units if the context supports it. "
            "Do not interpret unseen patient lab reports as clinical advice."
        ),
    }.get(domain, "Answer directly using the supplied evidence only.")

    prompt = f"""
You are a professional medical assistant AI.

Use ONLY the provided medical context.
Do not invent information.
If the context is insufficient, say: "I cannot answer this confidently from the information available here."
Do not diagnose emergencies.

Task instruction:
{domain_instruction}

User Question:
{query}

Medical Context:
{context}

Return:
1. A direct answer in plain language.
2. If relevant, 2-4 short bullet points.
3. If the evidence is weak, say so explicitly.
4. Do not use Markdown formatting symbols such as ** or *.
"""

    try:
        response = get_gemini_client().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        if hasattr(response, "text") and response.text:
            return response.text.strip()

        if response.candidates:
            return response.candidates[0].content.parts[0].text.strip()

        return "Unable to generate response."
    except Exception:
        return "AI system temporarily unavailable."


def get_answer(query: str, include_debug: bool = False) -> Dict:
    load_dbs()

    user_query = query.strip()
    normalized_query = normalize_brand_names(user_query)
    domain, scores = classify_query(normalized_query)

    if domain == "drugs":
        direct_local_answer = _local_medicine_answer(user_query)
        if direct_local_answer:
            response = {
                "intents": ["exact_medicine_match"],
                "answer": direct_local_answer,
                "confidence": 0.94,
                "detected_domain": "drugs",
            }
            if include_debug:
                response["debug_scores"] = scores
                response["retrieved_contexts"] = [{"source_db": "indian_medicine_exact_lookup", "score": 0.0, "lexical_score": 1.0}]
            return response

    if domain == "drugs" and _contains_any(user_query, INTERACTION_QUERY_KEYWORDS):
        interaction_answer = _interaction_pair_answer(user_query)
        if interaction_answer:
            response = {
                "intents": ["exact_interaction_match"],
                "answer": interaction_answer,
                "confidence": 0.95 if interaction_answer.lower().startswith("yes,") else 0.72,
                "detected_domain": "drugs",
            }
            if include_debug:
                response["debug_scores"] = scores
                response["retrieved_contexts"] = [{"source_db": "interactions_exact_lookup", "score": 0.0, "lexical_score": 1.0}]
            return response

    if domain == "lab" and _contains_any(user_query, LAB_REPORT_ACTION_KEYWORDS):
        response = {
            "intents": ["lab_query_redirect"],
            "answer": (
                "This looks like a lab-related query. For uploaded lab reports, use the lab analysis route. "
                "For general medical questions about a test, ask the specific test name and what you want to know."
            ),
            "confidence": 0.65,
            "detected_domain": "lab",
        }
        if include_debug:
            response["debug_scores"] = scores
        return response

    context, confidence, detected_domain, top_results = retrieve_context(
        user_query,
        normalized_query,
        domain,
    )

    if detected_domain == "emergency":
        response = {
            "intents": ["emergency"],
            "answer": context,
            "confidence": confidence,
            "detected_domain": detected_domain,
        }
        if include_debug:
            response["debug_scores"] = scores
        return response

    if not context.strip():
        response = {
            "intents": ["unknown"],
            "answer": "I cannot answer this confidently from the details available. Please ask with a little more detail or consult a qualified healthcare professional.",
            "confidence": confidence,
            "detected_domain": detected_domain,
        }
        if include_debug:
            response["debug_scores"] = scores
        return response

    if confidence < 0.22:
        response = {
            "intents": ["low_confidence"],
            "answer": (
                "I cannot answer this confidently from the details available. Please ask with a little more detail. "
                "For personal medical concerns, please consult a qualified healthcare professional."
            ),
            "confidence": confidence,
            "detected_domain": detected_domain,
        }
        if include_debug:
            response["debug_scores"] = scores
        return response

    final_answer = generate_answer(user_query, context, detected_domain)

    if not final_answer or "temporarily unavailable" in final_answer.lower():
        final_answer = fallback_answer(user_query, detected_domain, top_results)

    if len(final_answer.split()) > 350:
        final_answer = (
            "I found broad information, but not enough to give a clear concise answer. "
            "Please ask a more specific question so I can respond more helpfully."
        )

    response = {
        "intents": ["grounded_rag"],
        "answer": final_answer,
        "confidence": confidence,
        "detected_domain": detected_domain,
    }
    if include_debug:
        response["rxnorm_matches"] = _extract_rxnorm_mappings(top_results)
        response["retrieved_contexts"] = [
            {
                "source_db": item["db"],
                "score": round(item["score"], 3),
                "lexical_score": round(item["lexical"], 3),
            }
            for item in top_results
        ]
        response["debug_scores"] = scores
    return response
