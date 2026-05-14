import ast
import os
import re
from itertools import combinations
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

import pandas as pd

from medicine_parser import resolve_medicine_line


MEDICINE_DATA_FILE = os.path.join("knowledge_base", "updated_indian_medicine_data_prepared.csv")
INTERACTIONS_FILE = os.path.join("knowledge_base", "drug_interactions_prepared.csv")


FREQUENCY_MAP = {
    "od": "once daily",
    "qd": "once daily",
    "daily": "once daily",
    "bid": "twice daily",
    "bd": "twice daily",
    "tds": "three times daily",
    "tid": "three times daily",
    "qid": "four times daily",
    "hs": "at bedtime",
    "sos": "as needed",
    "stat": "immediately",
}

FORM_WORDS = [
    "tab",
    "tablet",
    "cap",
    "capsule",
    "syrup",
    "syp",
    "inj",
    "injection",
    "drops",
    "drop",
    "cream",
    "ointment",
]

TEST_ALIASES = {
    "cbc": "Complete blood count",
    "complete blood count": "Complete blood count",
    "urine routine": "Urine routine",
    "urine culture": "Urine culture",
    "urine r/m": "Urine routine",
    "urine microscopy": "Urine microscopy",
    "malaria parasite": "Malaria parasite test",
    "mp": "Malaria parasite test",
    "peripheral smear": "Peripheral smear",
    "dengue ns1": "Dengue NS1",
    "dengue igm": "Dengue IgM",
    "widal": "Widal test",
    "blood culture": "Blood culture",
    "hba1c": "HbA1c",
    "fbs": "Fasting blood sugar",
    "ppbs": "Postprandial blood sugar",
    "rbs": "Random blood sugar",
    "lft": "Liver function test",
    "kft": "Kidney function test",
    "liver function test": "Liver function test",
    "kidney function test": "Kidney function test",
    "x ray": "X-ray",
    "x-ray": "X-ray",
    "ecg": "ECG",
    "troponin": "Troponin",
}

SYMPTOM_PATTERNS = {
    "fever": [r"\bfever\b", r"\bpyrexia\b"],
    "chills": [r"\bchills?\b", r"\brigor(s)?\b"],
    "burning urination": [r"burning (while )?(passing )?urine", r"burning micturition", r"dysuria"],
    "frequent urination": [r"frequency of urine", r"frequent urination", r"increased urination"],
    "cough": [r"\bcough\b"],
    "sore throat": [r"sore throat", r"throat pain"],
    "headache": [r"\bheadache\b"],
    "fatigue": [r"\bfatigue\b", r"\btiredness\b", r"\bexhaustion\b"],
    "body pain": [r"body pain", r"body ache", r"myalgia"],
    "vomiting": [r"\bvomiting\b", r"\bvomit\b"],
    "nausea": [r"\bnausea\b"],
    "loose stools": [r"loose stool", r"diarrhea", r"diarrhoea"],
    "abdominal pain": [r"abdominal pain", r"stomach pain", r"abd pain"],
    "rash": [r"\brash\b"],
    "breathlessness": [r"shortness of breath", r"breathlessness", r"difficulty breathing"],
}

CONDITION_RULES = {
    "malaria": {
        "diagnosis_keywords": ["malaria", "malarial fever"],
        "symptoms_any": ["fever", "chills", "headache", "body pain", "vomiting"],
        "tests_indicative": ["Malaria parasite test", "Peripheral smear"],
        "medicine_keywords": [
            "artemether", "lumefantrine", "chloroquine", "primaquine",
            "artesunate", "quinine"
        ],
        "required_medicine_note": "Diagnosis suggests malaria but no antimalarial was identified.",
    },
    "uti": {
        "diagnosis_keywords": ["uti", "urinary tract infection", "cystitis"],
        "symptoms_any": ["fever", "burning urination", "frequent urination", "abdominal pain"],
        "tests_indicative": ["Urine culture", "Urine routine", "Urine microscopy"],
        "medicine_keywords": [
            "nitrofurantoin", "fosfomycin", "ciprofloxacin", "ofloxacin",
            "norfloxacin", "cefixime", "cefuroxime", "amoxicillin", "clavulanic"
        ],
        "required_medicine_note": "Diagnosis suggests urinary infection but no likely UTI treatment was identified.",
    },
    "dengue": {
        "diagnosis_keywords": ["dengue"],
        "symptoms_any": ["fever", "body pain", "headache", "vomiting", "rash"],
        "tests_indicative": ["Dengue NS1", "Dengue IgM", "Complete blood count"],
        "medicine_keywords": ["paracetamol", "acetaminophen", "oral rehydration"],
        "avoid_keywords": ["ibuprofen", "diclofenac", "aceclofenac", "aspirin", "nimesulide"],
        "infer_from_medicine": False,
        "required_medicine_note": "Dengue care usually centers on fluids and paracetamol; NSAIDs can be risky.",
    },
    "typhoid": {
        "diagnosis_keywords": ["typhoid", "enteric fever"],
        "symptoms_any": ["fever", "abdominal pain", "vomiting", "loose stools"],
        "tests_indicative": ["Widal test", "Blood culture"],
        "medicine_keywords": ["azithromycin", "cefixime", "ceftriaxone", "ofloxacin"],
        "required_medicine_note": "Typhoid diagnosis should usually align with targeted antibiotic therapy.",
    },
    "diabetes": {
        "diagnosis_keywords": ["diabetes", "dm", "type 2 diabetes", "type 1 diabetes"],
        "symptoms_any": ["frequent urination"],
        "tests_indicative": ["HbA1c", "Fasting blood sugar", "Postprandial blood sugar", "Random blood sugar"],
        "medicine_keywords": ["metformin", "insulin", "glimepiride", "sitagliptin", "dapagliflozin"],
        "required_medicine_note": "Diabetes diagnosis was found, but no common antidiabetic medicine was detected.",
    },
    "hypertension": {
        "diagnosis_keywords": ["hypertension", "htn", "high bp", "high blood pressure"],
        "symptoms_any": [],
        "tests_indicative": ["ECG"],
        "medicine_keywords": ["amlodipine", "telmisartan", "losartan", "metoprolol", "atenolol", "ramipril"],
        "required_medicine_note": "Hypertension diagnosis was found, but no common antihypertensive medicine was detected.",
    },
    "gastritis": {
        "diagnosis_keywords": ["gastritis", "acidity", "acid peptic disease", "gerd"],
        "symptoms_any": ["abdominal pain", "nausea", "vomiting"],
        "tests_indicative": [],
        "medicine_keywords": ["pantoprazole", "omeprazole", "rabeprazole", "esomeprazole"],
        "required_medicine_note": "Acid-related diagnosis was found, but acid suppression therapy was not identified.",
    },
}

AGE_GENDER_RULES = [
    {
        "keyword": "doxycycline",
        "max_age": 7,
        "severity": "high",
        "message": "Doxycycline is generally avoided in young children below 8 years.",
    },
    {
        "keyword": "tetracycline",
        "max_age": 7,
        "severity": "high",
        "message": "Tetracyclines are generally avoided in young children below 8 years.",
    },
    {
        "keyword": "ciprofloxacin",
        "max_age": 17,
        "severity": "medium",
        "message": "Ciprofloxacin in children usually needs explicit pediatric justification.",
    },
    {
        "keyword": "ofloxacin",
        "max_age": 17,
        "severity": "medium",
        "message": "Ofloxacin in children usually needs explicit pediatric justification.",
    },
    {
        "keyword": "levofloxacin",
        "max_age": 17,
        "severity": "medium",
        "message": "Levofloxacin in children usually needs explicit pediatric justification.",
    },
    {
        "keyword": "aspirin",
        "max_age": 15,
        "severity": "high",
        "message": "Aspirin is usually avoided in children with febrile illness unless specifically indicated.",
    },
    {
        "keyword": "finasteride",
        "gender": "female",
        "severity": "high",
        "message": "Finasteride is usually not prescribed for female patients in routine practice.",
    },
    {
        "keyword": "tamsulosin",
        "gender": "female",
        "severity": "medium",
        "message": "Tamsulosin is uncommon in female patients and should be verified against the indication.",
    },
]


_MEDICINE_CATALOG: Optional[Dict[str, Dict[str, str]]] = None
_INTERACTION_ROWS: Optional[pd.DataFrame] = None
_GENERIC_TERM_LOOKUP: Optional[Dict[str, str]] = None
_MONTH_LOOKUP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

MEDICATION_PURPOSE_RULES = [
    ("paracetamol", "Fever & pain relief", "acute"),
    ("acetaminophen", "Fever & pain relief", "acute"),
    ("amoxicillin", "Antibiotic for bacterial infection", "acute"),
    ("azithromycin", "Antibiotic for bacterial infection", "acute"),
    ("cefixime", "Antibiotic for bacterial infection", "acute"),
    ("metformin", "For diabetes (chronic condition)", "chronic"),
    ("insulin", "For diabetes (chronic condition)", "chronic"),
    ("atorvastatin", "For cholesterol", "chronic"),
    ("rosuvastatin", "For cholesterol", "chronic"),
    ("pantoprazole", "For acidity or gastric protection", "supportive"),
    ("omeprazole", "For acidity or gastric protection", "supportive"),
]

SAFE_GENERIC_USES = {
    "paracetamol": "Used for fever and pain relief.",
    "acetaminophen": "Used for fever and pain relief.",
    "amoxicillin": "Used for treating bacterial infections.",
    "azithromycin": "Used for treating bacterial infections.",
    "cefixime": "Used for treating bacterial infections.",
    "metformin": "Used to control blood sugar in type 2 diabetes.",
    "atorvastatin": "Used to lower cholesterol.",
    "rosuvastatin": "Used to lower cholesterol.",
    "telmisartan": "Used to control high blood pressure.",
    "losartan": "Used to control high blood pressure.",
    "amlodipine": "Used to control high blood pressure.",
    "pantoprazole": "Used to reduce stomach acid and acidity symptoms.",
    "omeprazole": "Used to reduce stomach acid and acidity symptoms.",
    "rabeprazole": "Used to reduce stomach acid and acidity symptoms.",
    "levocetirizine": "Used to relieve allergy symptoms.",
    "cetirizine": "Used to relieve allergy symptoms.",
    "montelukast": "Used for allergy and asthma symptom control.",
    "salbutamol": "Used to relieve wheezing and breathing difficulty.",
    "nitrofurantoin": "Used for treating urinary tract infections.",
}

LAB_ROUTE_KEYWORDS = [
    "hemoglobin", "haemoglobin", "hb", "wbc", "rbc", "platelet", "creatinine",
    "tsh", "t3", "t4", "hba1c", "fbs", "ppbs", "rbs", "bilirubin", "sgot", "sgpt",
    "cholesterol", "triglycerides", "uric acid", "urea", "sodium", "potassium",
    "test result", "lab report", "investigation result", "reference range",
    "pathology lab", "investigation", "reference value", "sample collected",
    "liver function test", "lft", "ast", "alt", "ggtp", "alkaline phosphatase",
    "total protein", "albumin", "globulin", "a : g ratio", "a:g ratio",
]

GENERIC_NAME_ALIASES = {
    "amoxycillin": "amoxicillin",
    "acetaminophen": "paracetamol",
    "levocetrizine": "levocetirizine",
    "pantaprazole": "pantoprazole",
}

THERAPEUTIC_CATEGORY_RULES = [
    {
        "name": "antibiotic",
        "keywords": [
            "amoxicillin", "azithromycin", "cefixime", "cefuroxime", "ceftriaxone",
            "ciprofloxacin", "ofloxacin", "levofloxacin", "doxycycline", "metronidazole",
            "antibiotic",
        ],
        "purpose": "Antibiotic for bacterial infection",
        "category": "acute",
        "family": "acute_infection",
    },
    {
        "name": "analgesic_antipyretic",
        "keywords": [
            "paracetamol", "acetaminophen", "ibuprofen", "diclofenac", "aceclofenac",
        ],
        "purpose": "Fever & pain relief",
        "category": "acute",
        "family": "symptomatic_relief",
    },
    {
        "name": "antidiabetic",
        "keywords": [
            "metformin", "glimepiride", "sitagliptin", "vildagliptin",
            "insulin", "empagliflozin", "dapagliflozin", "diabetes", "anti diabetic",
        ],
        "purpose": "For diabetes management",
        "category": "chronic",
        "family": "metabolic_chronic",
    },
    {
        "name": "statin",
        "keywords": [
            "atorvastatin", "rosuvastatin", "cholesterol", "lipid",
        ],
        "purpose": "For cholesterol control",
        "category": "chronic",
        "family": "cardiometabolic_chronic",
    },
    {
        "name": "antihypertensive",
        "keywords": [
            "amlodipine", "telmisartan", "losartan", "ramipril",
            "atenolol", "metoprolol", "blood pressure", "hypertension",
        ],
        "purpose": "For blood pressure control",
        "category": "chronic",
        "family": "cardiometabolic_chronic",
    },
    {
        "name": "acid_suppression",
        "keywords": [
            "pantoprazole", "omeprazole", "rabeprazole", "esomeprazole",
            "acidity", "gastric", "gerd",
        ],
        "purpose": "For acidity or gastric protection",
        "category": "supportive",
        "family": "supportive_care",
    },
    {
        "name": "antihistamine",
        "keywords": [
            "cetirizine", "levocetirizine", "fexofenadine", "chlorpheniramine",
            "allergy", "antihistamine",
        ],
        "purpose": "For allergy symptom relief",
        "category": "supportive",
        "family": "allergy_respiratory",
    },
    {
        "name": "respiratory",
        "keywords": [
            "salbutamol", "montelukast", "budesonide", "theophylline",
            "asthma", "wheeze", "bronchodilator",
        ],
        "purpose": "For airway or breathing symptom control",
        "category": "supportive",
        "family": "allergy_respiratory",
    },
    {
        "name": "vitamin_supplement",
        "keywords": [
            "vitamin", "iron", "calcium", "folic acid", "multivitamin",
        ],
        "purpose": "Supplement support",
        "category": "supportive",
        "family": "supplement",
    },
]


def _normalize_text(value: str) -> str:
    value = str(value).lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _load_medicine_catalog() -> Dict[str, Dict[str, str]]:
    global _MEDICINE_CATALOG
    if _MEDICINE_CATALOG is not None:
        return _MEDICINE_CATALOG

    _MEDICINE_CATALOG = {}
    if not os.path.exists(MEDICINE_DATA_FILE):
        return _MEDICINE_CATALOG

    usecols = ["name", "generic_or_salt", "uses", "description", "side_effects_list", "manufacturer_name"]
    df = pd.read_csv(MEDICINE_DATA_FILE, usecols=usecols).fillna("")

    for _, row in df.iterrows():
        entry = {col: str(row[col]).strip() for col in usecols}
        keys = {
            _normalize_text(entry["name"]),
            _normalize_text(entry["generic_or_salt"]),
        }
        for key in list(keys):
            if key and key not in _MEDICINE_CATALOG:
                _MEDICINE_CATALOG[key] = entry

    return _MEDICINE_CATALOG


def _normalize_generic_token(value: str) -> str:
    value = _normalize_text(value)
    return GENERIC_NAME_ALIASES.get(value, value)


def _split_generic_components_from_text(value: str) -> List[str]:
    text = str(value).lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    parts = re.split(r"\+|,|/| and ", text)
    components = []
    for part in parts:
        normalized = _normalize_text(part)
        normalized = re.sub(r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml|iu|%)\b", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            continue
        normalized = _normalize_generic_token(normalized)
        if len(normalized) >= 4:
            components.append(normalized)
    return list(dict.fromkeys(components))


def _build_generic_term_lookup() -> Dict[str, str]:
    global _GENERIC_TERM_LOOKUP
    if _GENERIC_TERM_LOOKUP is not None:
        return _GENERIC_TERM_LOOKUP

    lookup: Dict[str, str] = {}

    for generic_name in SAFE_GENERIC_USES.keys():
        normalized = _normalize_generic_token(generic_name)
        lookup[normalized] = normalized

    for alias, canonical in GENERIC_NAME_ALIASES.items():
        lookup[_normalize_text(alias)] = canonical

    if os.path.exists(MEDICINE_DATA_FILE):
        df = pd.read_csv(MEDICINE_DATA_FILE, usecols=["generic_or_salt"]).fillna("")
        for value in df["generic_or_salt"].tolist():
            for component in _split_generic_components_from_text(value):
                lookup[component] = component

    _GENERIC_TERM_LOOKUP = lookup
    return _GENERIC_TERM_LOOKUP


def _extract_exact_generic_match(value: str) -> str:
    normalized_line = _normalize_text(value)
    if not normalized_line:
        return ""

    lookup = _build_generic_term_lookup()
    matches = []
    for term, canonical in lookup.items():
        if re.search(rf"\b{re.escape(term)}\b", normalized_line):
            matches.append((term, canonical))

    if not matches:
        return ""

    return max(matches, key=lambda item: len(item[0]))[1]


def _load_interactions() -> pd.DataFrame:
    global _INTERACTION_ROWS
    if _INTERACTION_ROWS is not None:
        return _INTERACTION_ROWS

    if not os.path.exists(INTERACTIONS_FILE):
        _INTERACTION_ROWS = pd.DataFrame()
        return _INTERACTION_ROWS

    usecols = ["drug_name", "generic_name", "interacting_drug", "interaction_severity", "interaction_text"]
    _INTERACTION_ROWS = pd.read_csv(INTERACTIONS_FILE, usecols=usecols).fillna("")
    for col in ["drug_name", "generic_name", "interacting_drug"]:
        _INTERACTION_ROWS[f"{col}_key"] = _INTERACTION_ROWS[col].map(_normalize_text)
    return _INTERACTION_ROWS


def _extract_patient_context(text: str) -> Dict[str, Optional[str]]:
    lower = text.lower()

    age_match = re.search(r"\b(\d{1,3})\s*(?:y|yr|yrs|year|years)\b", lower)
    if age_match is None:
        age_match = re.search(r"\bage\s*/\s*sex\s*[:\-]?\s*(\d{1,3})\s*/", lower)
    if age_match is None:
        age_match = re.search(r"\bage\s*[:\-]?\s*(\d{1,3})\b", lower)
    born_match = re.search(r"\bborn\s+([a-z]+)\s+(\d{1,2})\s+(\d{4})\b", lower)
    gender = None

    if re.search(r"\bage\s*/\s*sex\s*[:\-]?\s*\d{1,3}\s*/\s*male\b", lower) or re.search(r"\b(male|man|boy)\b", lower):
        gender = "male"
    elif re.search(r"\bage\s*/\s*sex\s*[:\-]?\s*\d{1,3}\s*/\s*female\b", lower) or re.search(r"\b(female|woman|girl)\b", lower):
        gender = "female"

    age = int(age_match.group(1)) if age_match else None
    if age is None and born_match:
        month_name, day_value, year_value = born_match.groups()
        month_number = _MONTH_LOOKUP.get(month_name)
        if month_number:
            current_year = 2026
            current_month = 4
            current_day = 18
            age = current_year - int(year_value)
            if (current_month, current_day) < (month_number, int(day_value)):
                age -= 1

    return {
        "age": age,
        "gender": gender,
    }


def _extract_vitals(text: str) -> Dict[str, str]:
    lower = str(text).lower()
    vitals: Dict[str, str] = {}

    weight_match = re.search(r"\bweight\s*(?:\(kg\))?\s*[:\-]?\s*(\d+(?:\.\d+)?)\b", lower)
    height_match = re.search(r"\bheight\s*(?:\(cm\))?\s*[:\-]?\s*(\d+(?:\.\d+)?)\b", lower)
    bp_match = re.search(r"\bbp\s*[:\-]?\s*(\d{2,3}\s*/\s*\d{2,3})\b", lower)

    if weight_match:
        vitals["weight_kg"] = weight_match.group(1)
    if height_match:
        vitals["height_cm"] = height_match.group(1)
    if bp_match:
        vitals["blood_pressure"] = bp_match.group(1).replace(" ", "")

    return vitals


def _extract_diagnosis(text: str) -> List[str]:
    diagnoses: List[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        lower = line.lower()
        match = re.search(
            r"(diagnosis|dx|impression|provisional diagnosis|assessment)\s*[:\-]\s*(.+)",
            lower,
        )
        if match:
            raw = re.split(r"[;,/]| and ", match.group(2))
            diagnoses.extend(item.strip().title() for item in raw if item.strip())

    for condition, rule in CONDITION_RULES.items():
        if any(keyword in text.lower() for keyword in rule["diagnosis_keywords"]):
            diagnoses.append(condition.upper() if condition == "uti" else condition.title())

    return list(dict.fromkeys(item for item in diagnoses if item))


def _extract_symptoms(text: str) -> List[str]:
    hits: List[str] = []
    lower = text.lower()

    for symptom, patterns in SYMPTOM_PATTERNS.items():
        if any(re.search(pattern, lower) for pattern in patterns):
            hits.append(symptom)

    for line in text.splitlines():
        lower_line = line.lower().strip()
        if lower_line.startswith(("c/o", "complaint", "complaints", "symptoms", "history")):
            for symptom, patterns in SYMPTOM_PATTERNS.items():
                if any(re.search(pattern, lower_line) for pattern in patterns):
                    hits.append(symptom)

    return list(dict.fromkeys(hits))


def _extract_tests(text: str) -> List[str]:
    found: List[str] = []
    lower = text.lower()
    for alias, canonical in TEST_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            found.append(canonical)
    return list(dict.fromkeys(found))


def _split_sections(text: str) -> Dict[str, str]:
    section_titles = [
        "prescription",
        "rx",
        "r",
        "symptoms",
        "chief complaints",
        "complaints",
        "vital observation",
        "clinical findings",
        "notes",
        "advice",
        "followup",
        "follow up",
        "diagnosis",
        "tests",
    ]
    pattern = re.compile(
        r"^\s*(" + "|".join(re.escape(title) for title in section_titles) + r")\s*:?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    sections: Dict[str, str] = {}

    if not matches:
        sections["full_text"] = text
        return sections

    if matches[0].start() > 0:
        sections["preamble"] = text[:matches[0].start()].strip()

    for index, match in enumerate(matches):
        name = match.group(1).lower().replace(" ", "_")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[name] = text[start:end].strip()

    return sections


def _extract_strength(line: str) -> str:
    strengths = re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu)\b", line.lower())
    if strengths:
        return ", ".join(dict.fromkeys(strengths))
    return ""


def _extract_frequency(line: str) -> str:
    lower = line.lower()
    schedule = re.search(r"\b([0-3]\s*-\s*[0-3]\s*-\s*[0-3])\b", lower)
    if schedule:
        return schedule.group(1).replace(" ", "")

    phrase_patterns = [
        (r"\b1\s+morning,\s*1\s+night\b", "morning and night"),
        (r"\b1\s+morning\b", "morning"),
        (r"\b1\s+night\b", "night"),
        (r"every\s*4\s*-\s*6\s*hours?\s+as\s+needed", "every 4-6 hours as needed"),
        (r"every\s*4\s*-\s*6\s*hours?", "every 4-6 hours"),
        (r"every\s*8\s*hours?", "every 8 hours"),
        (r"every\s*12\s*hours?", "every 12 hours"),
        (r"twice a day", "twice daily"),
        (r"once a day", "once daily"),
        (r"three times a day", "three times daily"),
        (r"as needed", "as needed"),
        (r"bedtime", "at bedtime"),
    ]
    for pattern, label in phrase_patterns:
        if re.search(pattern, lower):
            return label

    hits = []
    for short, full in FREQUENCY_MAP.items():
        if re.search(rf"\b{re.escape(short)}\b", lower):
            hits.append(full)
    return ", ".join(dict.fromkeys(hits))


def _extract_duration(line: str) -> str:
    match = re.search(r"\bfor\s+(\d+\s*(?:day|days|week|weeks|month|months))\b", line.lower())
    if match:
        return match.group(1)
    match = re.search(r"\bx\s*(\d+\s*(?:day|days|week|weeks|month|months))\b", line.lower())
    if match:
        return match.group(1)
    match = re.search(r"\b(\d+\s*(?:day|days|week|weeks|month|months))\b", line.lower())
    return match.group(1) if match else ""


def _extract_form(line: str) -> str:
    lower = line.lower()
    for word in FORM_WORDS:
        if re.search(rf"\b{re.escape(word)}s?\b", lower):
            return word
    return ""


def _find_medicine_catalog_entry(brand_name: str, generic_name: str) -> Dict[str, str]:
    catalog = _load_medicine_catalog()
    candidates = [_normalize_text(brand_name), _normalize_text(generic_name)]
    for key in candidates:
        if key and key in catalog:
            return catalog[key]

    best_key = ""
    best_score = 0.0
    generic_key = _normalize_text(generic_name)
    for key in catalog.keys():
        if not key or not generic_key:
            continue
        if generic_key in key or key in generic_key:
            score = SequenceMatcher(None, generic_key, key).ratio()
            if score > best_score:
                best_key = key
                best_score = score

    if best_key:
        return catalog[best_key]

    return {}


def _extract_generic_line_candidate(line: str) -> Tuple[str, str]:
    cleaned = str(line).lower()
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml|iu)?\b", " ", cleaned)
    cleaned = re.sub(r"\b(?:tab|tablet|cap|capsule|inj|injection|syrup|syp|drops|drop|od|bd|bid|tds|tid|qid|hs|sos|stat)\b", " ", cleaned)
    cleaned = re.sub(r"[^a-z\s\-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "", ""

    exact_generic = _extract_exact_generic_match(cleaned)
    if exact_generic:
        return exact_generic.title(), exact_generic

    catalog = _load_medicine_catalog()
    token_candidates = []
    words = cleaned.split()
    for size in range(min(4, len(words)), 0, -1):
        for index in range(0, len(words) - size + 1):
            phrase = " ".join(words[index:index + size]).strip()
            if phrase:
                token_candidates.append(phrase)

    seen = set()
    for phrase in token_candidates:
        if phrase in seen:
            continue
        seen.add(phrase)

        if phrase in catalog:
            entry = catalog[phrase]
            return entry.get("name", phrase), _normalize_text(entry.get("generic_or_salt", phrase))

        for rule in THERAPEUTIC_CATEGORY_RULES:
            if phrase in rule["keywords"]:
                return phrase.title(), phrase

    if words:
        return words[0].title(), _normalize_text(words[0])
    return "", ""


def _clean_medicine_cell(value: str) -> str:
    value = str(value).strip().strip("|").strip()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _extract_generic_candidate(value: str) -> str:
    cleaned = _clean_medicine_cell(value)
    tokens = cleaned.split()
    if not tokens:
        return ""
    if len(tokens) >= 2 and tokens[-1].lower() == tokens[-2].lower():
        return tokens[-1]
    return cleaned


def _normalize_table_medicine_name(value: str) -> Tuple[str, str]:
    cleaned = _clean_medicine_cell(value)
    exact_generic = _extract_exact_generic_match(cleaned)
    if exact_generic:
        return exact_generic.title(), exact_generic

    candidates = []

    # Use trailing repeated token or final token as the most likely canonical name.
    extracted = _extract_generic_candidate(value)
    if extracted:
        candidates.append(extracted)

    # Split around bracketed class text and punctuation noise.
    candidates.extend(
        part.strip()
        for part in re.split(r"\s{2,}|/", re.sub(r"\([^)]*\)", " ", cleaned))
        if part.strip()
    )
    candidates.append(cleaned)

    seen = set()
    for candidate in candidates:
        normalized = _normalize_text(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)

        if normalized in {"paracetamol acetaminophen", "acetaminophen paracetamol"}:
            return "Paracetamol", "paracetamol"

        resolved = resolve_medicine_line(candidate)
        generic_name = resolved.get("generic_name", "").strip()
        brand_name = resolved.get("brand_name", "").strip()
        if resolved.get("match_type") != "unmapped" and generic_name:
            return brand_name or candidate, generic_name

        tokens = candidate.split()
        if tokens:
            last_token = tokens[-1].strip()
            if last_token and re.fullmatch(r"[A-Za-z][A-Za-z\-]*", last_token):
                return last_token.title(), _normalize_text(last_token)

    return cleaned, _normalize_text(cleaned)


def _is_markdown_table_row(line: str) -> bool:
    return line.strip().startswith("|") and line.count("|") >= 5


def _is_markdown_separator_row(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells if cell)


def _parse_numbered_medicine_rows(text: str) -> List[Dict[str, object]]:
    medicines: List[Dict[str, object]] = []
    sections = _split_sections(text)
    prescription_text = sections.get("rx") or sections.get("r") or sections.get("prescription") or ""
    if not prescription_text:
        return medicines

    lines = [line.strip() for line in prescription_text.splitlines() if line.strip()]
    index = 0
    while index < len(lines):
        line = lines[index]
        lower = line.lower()

        if any(token in lower for token in ["medicine name", "dosage", "duration", "rx"]):
            index += 1
            continue

        match = re.match(r"^\s*(\d+)[\)\.]?\s*(tab\.|cap\.|tablet|capsule)?\s*(.+)$", line, flags=re.IGNORECASE)
        if not match:
            index += 1
            continue

        _, form_token, rest = match.groups()
        if not rest or len(rest.split()) < 1:
            index += 1
            continue

        duration = _extract_duration(line)
        frequency = _extract_frequency(line)
        strength = _extract_strength(line)

        # Remove schedule/duration fragments from the candidate name line.
        name_candidate = rest
        name_candidate = re.sub(r"\b\d+\s*(?:day|days|week|weeks|month|months)\b", " ", name_candidate, flags=re.IGNORECASE)
        name_candidate = re.sub(r"\b1\s+morning,\s*1\s+night\b", " ", name_candidate, flags=re.IGNORECASE)
        name_candidate = re.sub(r"\b1\s+morning\b", " ", name_candidate, flags=re.IGNORECASE)
        name_candidate = re.sub(r"\b1\s+night\b", " ", name_candidate, flags=re.IGNORECASE)
        name_candidate = re.sub(r"\(after food\)|\(before food\)", " ", name_candidate, flags=re.IGNORECASE)
        name_candidate = re.sub(r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml|iu)\b", " ", name_candidate, flags=re.IGNORECASE)
        name_candidate = re.sub(r"\b\d+\b", " ", name_candidate)
        name_candidate = re.sub(r"\s+", " ", name_candidate).strip(" -")

        display_name, generic_name = _normalize_table_medicine_name(name_candidate)
        catalog_entry = _find_medicine_catalog_entry(display_name, generic_name)

        # Optional continuation lines with generic/salt details.
        instructions = []
        continuation_index = index + 1
        while continuation_index < len(lines):
            extra_line = lines[continuation_index].strip()
            extra_lower = extra_line.lower()
            if re.match(r"^\s*(\d+)[\)\.]?\s*(tab\.|cap\.|tablet|capsule)?\s+", extra_line, flags=re.IGNORECASE):
                break
            if any(token in extra_lower for token in ["advice", "follow up", "medicine name", "dosage", "duration"]):
                break
            if extra_lower.startswith("tot:"):
                continuation_index += 1
                continue
            continuation_index += 1

        medicines.append(
            {
                "original_line": line,
                "brand_name": display_name,
                "generic_name": generic_name,
                "strength": strength,
                "frequency": frequency,
                "duration": duration,
                "form": (form_token or "").strip(".").lower(),
                "instructions": " ".join(instructions).strip(),
                "match_type": "numbered_row",
                "mapping_confidence": 0.85,
                "uses": catalog_entry.get("uses", "").strip(),
                "description": catalog_entry.get("description", "").strip(),
                "side_effects": [],
                "source_hint": name_candidate,
            }
        )
        index = continuation_index

    return medicines


def _parse_medicine_table_rows(text: str) -> List[Dict[str, object]]:
    medicines: List[Dict[str, object]] = []
    sections = _split_sections(text)
    prescription_text = sections.get("prescription") or sections.get("rx") or ""
    if not prescription_text:
        return medicines

    for raw_line in prescription_text.splitlines():
        line = raw_line.strip()
        if not _is_markdown_table_row(line):
            continue
        if re.search(r"\|\s*#\s*\|", line.lower()) or _is_markdown_separator_row(line):
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue

        row_number, medicine_name, dose, frequency, duration, instructions = cells[:6]
        if not row_number.isdigit():
            continue

        cleaned_name = _clean_medicine_cell(medicine_name)
        display_name, generic_name = _normalize_table_medicine_name(medicine_name)
        resolved = resolve_medicine_line(generic_name)
        brand_name = resolved.get("brand_name", "").strip() or display_name
        catalog_entry = _find_medicine_catalog_entry(brand_name, generic_name)

        side_effects = catalog_entry.get("side_effects_list", "").strip()
        parsed_side_effects = []
        if side_effects:
            try:
                parsed_side_effects = list(ast.literal_eval(side_effects))
            except (ValueError, SyntaxError):
                parsed_side_effects = [item.strip() for item in side_effects.split(",") if item.strip()]

        medicines.append(
            {
                "original_line": line,
                "brand_name": display_name,
                "generic_name": generic_name,
                "strength": dose.strip(),
                "frequency": _extract_frequency(frequency) or frequency.strip(),
                "duration": duration.strip().strip("-"),
                "form": _extract_form(cleaned_name),
                "instructions": instructions.strip(),
                "match_type": resolved.get("match_type", "generic_table"),
                "mapping_confidence": resolved.get("confidence", 0.0) or 0.9,
                "uses": catalog_entry.get("uses", "").strip(),
                "description": catalog_entry.get("description", "").strip(),
                "side_effects": parsed_side_effects[:8],
                "source_hint": cleaned_name,
            }
        )

    return medicines


def _is_candidate_medicine_line(line: str) -> bool:
    lower = line.lower().strip()
    if not lower:
        return False

    blocked_prefixes = [
        "dr.",
        "prescription",
        "symptoms",
        "vital observation",
        "blood pressure",
        "heart rate",
        "respiratory rate",
        "body temperature",
        "notes",
        "advice",
        "diagnosis",
        "chief complaints",
        "complaints",
        "clinical findings",
        "followup",
        "follow up",
        "visit on",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "monday",
        "tuesday",
    ]
    if any(lower.startswith(prefix) for prefix in blocked_prefixes):
        return False
    if "clinic" in lower or "france" in lower or "@" in lower or "+" in lower:
        return False
    if ":" in lower and not any(token in lower for token in FORM_WORDS):
        return False
    if not any(token in lower for token in FORM_WORDS) and not re.search(r"\b\d+\s*(mg|mcg|g|ml|iu|day|days|morning|night)\b", lower):
        return False
    if _is_markdown_table_row(line):
        return False
    return True


def _extract_medicines(text: str) -> List[Dict[str, object]]:
    table_medicines = _parse_medicine_table_rows(text)
    if table_medicines:
        return table_medicines

    numbered_row_medicines = _parse_numbered_medicine_rows(text)
    if numbered_row_medicines:
        return numbered_row_medicines

    medicines: List[Dict[str, object]] = []
    seen = set()
    sections = _split_sections(text)
    prescription_text = sections.get("prescription") or sections.get("rx") or sections.get("r") or text
    has_explicit_prescription_section = any(key in sections for key in ["prescription", "rx", "r"])

    if has_explicit_prescription_section and not prescription_text.strip():
        return medicines

    for raw_line in prescription_text.splitlines():
        line = raw_line.strip()
        if not line or not _is_candidate_medicine_line(line):
            continue
        exact_generic = _extract_exact_generic_match(line)
        used_generic_fallback = False

        if exact_generic:
            resolved = {
                "match_type": "generic_exact",
                "confidence": 0.95,
            }
            generic_name = exact_generic
            brand_name = exact_generic.title()
            used_generic_fallback = True
        else:
            resolved = resolve_medicine_line(line)
            generic_name = resolved.get("generic_name", "").strip()
            brand_name = resolved.get("brand_name", "").strip()

        if resolved.get("match_type") == "unmapped" or not generic_name:
            fallback_brand, fallback_generic = _extract_generic_line_candidate(line)
            if fallback_generic:
                brand_name = fallback_brand
                generic_name = fallback_generic
                used_generic_fallback = True

        looks_like_medicine = (
            resolved.get("match_type") != "unmapped"
            or bool(generic_name)
            or bool(_extract_strength(line))
            or bool(_extract_frequency(line))
            or any(word in line.lower() for word in FORM_WORDS)
        )
        if not looks_like_medicine or not generic_name:
            continue

        key = (_normalize_text(brand_name), _normalize_text(generic_name), _extract_strength(line), _extract_frequency(line))
        if key in seen:
            continue
        seen.add(key)

        catalog_entry = _find_medicine_catalog_entry(brand_name, generic_name)
        side_effects = catalog_entry.get("side_effects_list", "").strip()
        parsed_side_effects = []
        if side_effects:
            try:
                parsed_side_effects = list(ast.literal_eval(side_effects))
            except (ValueError, SyntaxError):
                parsed_side_effects = [item.strip() for item in side_effects.split(",") if item.strip()]

        medicines.append(
            {
                "original_line": line,
                "brand_name": generic_name.title() if used_generic_fallback else brand_name,
                "generic_name": generic_name,
                "strength": _extract_strength(line),
                "frequency": _extract_frequency(line),
                "duration": _extract_duration(line),
                "form": _extract_form(line),
                "instructions": "",
                "match_type": resolved.get("match_type", "generic_fallback" if resolved.get("match_type") == "unmapped" else resolved.get("match_type", "unmapped")),
                "mapping_confidence": resolved.get("confidence", 0.0) if resolved.get("match_type") != "unmapped" else 0.7,
                "uses": catalog_entry.get("uses", "").strip(),
                "description": catalog_entry.get("description", "").strip(),
                "side_effects": parsed_side_effects[:8],
                "source_hint": line,
            }
        )

    return medicines


def _condition_from_diagnoses(diagnoses: List[str]) -> List[str]:
    hits = []
    normalized = " ".join(diagnoses).lower()
    for condition, rule in CONDITION_RULES.items():
        if any(keyword in normalized for keyword in rule["diagnosis_keywords"]):
            hits.append(condition)
    return hits


def _condition_from_tests(tests: List[str]) -> List[str]:
    hits = []
    test_blob = " | ".join(tests).lower()
    for condition, rule in CONDITION_RULES.items():
        if any(test_name.lower() in test_blob for test_name in rule["tests_indicative"]):
            hits.append(condition)
    return hits


def _condition_from_medicines(medicines: List[Dict[str, object]]) -> List[str]:
    hits = []
    combined = " ".join(
        f"{item.get('generic_name', '')} {item.get('uses', '')} {item.get('description', '')}".lower()
        for item in medicines
    )
    for condition, rule in CONDITION_RULES.items():
        if rule.get("infer_from_medicine", True) is False:
            continue
        if any(keyword in combined for keyword in rule["medicine_keywords"]):
            hits.append(condition)
    return hits


def _condition_from_symptoms(symptoms: List[str]) -> List[Dict[str, object]]:
    symptom_set = set(symptoms)
    reasoning = []

    if {"fever", "burning urination"} <= symptom_set:
        reasoning.append(
            {
                "condition": "uti",
                "basis": "Fever with burning urination points toward urinary infection.",
                "confidence": "medium",
            }
        )
    if {"fever", "chills"} <= symptom_set:
        reasoning.append(
            {
                "condition": "malaria",
                "basis": "Fever with chills is a classic malaria pattern.",
                "confidence": "medium",
            }
        )
    if {"fever", "body pain", "headache"} <= symptom_set:
        reasoning.append(
            {
                "condition": "dengue",
                "basis": "Fever with headache and body pain can fit dengue or another viral fever.",
                "confidence": "low",
            }
        )
    if {"cough", "sore throat"} <= symptom_set:
        reasoning.append(
            {
                "condition": "upper respiratory infection",
                "basis": "Cough with sore throat is more consistent with an upper respiratory infection.",
                "confidence": "low",
            }
        )

    return reasoning


def _add_finding(findings: List[Dict[str, object]], severity: str, category: str, summary: str, evidence: List[str], recommendation: str) -> None:
    findings.append(
        {
            "severity": severity,
            "category": category,
            "summary": summary,
            "evidence": evidence,
            "recommendation": recommendation,
        }
    )


def _check_diagnosis_medicine_consistency(diagnoses: List[str], medicines: List[Dict[str, object]], findings: List[Dict[str, object]]) -> List[Dict[str, object]]:
    diagnosis_conditions = _condition_from_diagnoses(diagnoses)
    evidence = []

    for condition in diagnosis_conditions:
        rule = CONDITION_RULES[condition]
        med_blob = " ".join(
            f"{item.get('generic_name', '')} {item.get('uses', '')} {item.get('description', '')}".lower()
            for item in medicines
        )
        matched = [keyword for keyword in rule["medicine_keywords"] if keyword in med_blob]
        evidence.append({"condition": condition, "matched_medicine_signals": matched})

        if not matched:
            _add_finding(
                findings,
                "high",
                "missing_essential_treatment",
                rule["required_medicine_note"],
                [f"Diagnosis: {condition}", "No matching treatment signal found in extracted medicines."],
                "Review whether the diagnosis or the prescribed treatment is incomplete.",
            )

        if condition == "dengue":
            avoid_hits = [keyword for keyword in rule.get("avoid_keywords", []) if keyword in med_blob]
            if avoid_hits:
                _add_finding(
                    findings,
                    "high",
                    "wrong_medicine",
                    "Possible dengue with NSAID-type medicine detected.",
                    [f"Diagnosis: {condition}", f"Detected medicine signal: {', '.join(avoid_hits)}"],
                    "Verify whether this is actually dengue and avoid NSAIDs unless the clinician explicitly intended them.",
                )

    return evidence


def _check_diagnosis_test_consistency(diagnoses: List[str], tests: List[str], findings: List[Dict[str, object]]) -> List[Dict[str, object]]:
    diagnosis_conditions = _condition_from_diagnoses(diagnoses)
    test_conditions = _condition_from_tests(tests)
    evidence = []

    for condition in diagnosis_conditions:
        rule = CONDITION_RULES[condition]
        matched_tests = [test for test in tests if test in rule["tests_indicative"]]
        evidence.append({"condition": condition, "matched_tests": matched_tests})

    for diagnosis_condition in diagnosis_conditions:
        for test_condition in test_conditions:
            if diagnosis_condition != test_condition:
                _add_finding(
                    findings,
                    "medium",
                    "diagnosis_test_mismatch",
                    "Diagnosis may be inconsistent with the ordered tests.",
                    [f"Diagnosis suggests {diagnosis_condition}.", f"Tests suggest {test_condition}."],
                    "Recheck whether the stated diagnosis matches the workup being ordered.",
                )

    return evidence


def _check_medicine_patient_consistency(patient_context: Dict[str, Optional[str]], medicines: List[Dict[str, object]], findings: List[Dict[str, object]]) -> List[Dict[str, object]]:
    evidence = []
    age = patient_context.get("age")
    gender = patient_context.get("gender")

    for medicine in medicines:
        generic = str(medicine.get("generic_name", "")).lower()
        for rule in AGE_GENDER_RULES:
            if rule["keyword"] not in generic:
                continue
            rule_evidence = [f"Medicine: {medicine.get('generic_name')}"]
            if age is not None and "max_age" in rule and age <= rule["max_age"]:
                rule_evidence.append(f"Patient age: {age}")
                evidence.append({"medicine": medicine.get("generic_name"), "rule": rule["message"]})
                _add_finding(
                    findings,
                    rule["severity"],
                    "patient_mismatch",
                    rule["message"],
                    rule_evidence,
                    "Verify the patient age and confirm the drug is intentionally prescribed for this age group.",
                )
            if gender and "gender" in rule and gender == rule["gender"]:
                rule_evidence.append(f"Patient gender: {gender}")
                evidence.append({"medicine": medicine.get("generic_name"), "rule": rule["message"]})
                _add_finding(
                    findings,
                    rule["severity"],
                    "patient_mismatch",
                    rule["message"],
                    rule_evidence,
                    "Verify the indication and patient identity details on the prescription.",
                )

    return evidence


def _lookup_interaction(left: str, right: str) -> Optional[Dict[str, str]]:
    interactions = _load_interactions()
    if interactions.empty:
        return None

    left_key = _normalize_text(left)
    right_key = _normalize_text(right)

    mask = (
        (
            interactions["drug_name_key"].isin([left_key, right_key])
            | interactions["generic_name_key"].isin([left_key, right_key])
        )
        & (
            (interactions["drug_name_key"].isin([left_key]) | interactions["generic_name_key"].isin([left_key]))
            & interactions["interacting_drug_key"].isin([right_key])
            |
            (interactions["drug_name_key"].isin([right_key]) | interactions["generic_name_key"].isin([right_key]))
            & interactions["interacting_drug_key"].isin([left_key])
        )
    )

    if not mask.any():
        return None

    row = interactions[mask].iloc[0]
    return {
        "drug_name": str(row["drug_name"]).strip(),
        "interacting_drug": str(row["interacting_drug"]).strip(),
        "interaction_severity": str(row["interaction_severity"]).strip(),
        "interaction_text": str(row["interaction_text"]).strip(),
    }


def _check_interactions(medicines: List[Dict[str, object]], findings: List[Dict[str, object]]) -> List[Dict[str, object]]:
    evidence = []

    for left, right in combinations(medicines, 2):
        left_name = str(left.get("generic_name") or left.get("brand_name"))
        right_name = str(right.get("generic_name") or right.get("brand_name"))
        interaction = _lookup_interaction(left_name, right_name)
        if not interaction:
            continue

        severity = interaction.get("interaction_severity", "").lower()
        mapped_severity = "high" if severity in {"major", "severe", "high"} else "medium"
        evidence.append(interaction)
        _add_finding(
            findings,
            mapped_severity,
            "suspicious_combination",
            f"Potential interaction between {left_name} and {right_name}.",
            [
                f"Reported severity: {interaction.get('interaction_severity', 'unknown')}",
                interaction.get("interaction_text", "Interaction details available in the local drug database."),
            ],
            "Ask a clinician or pharmacist to confirm whether the combination is intended and monitored.",
        )

    return evidence


def _deduplicate_findings(findings: List[Dict[str, object]]) -> List[Dict[str, object]]:
    seen = set()
    output = []
    for finding in findings:
        key = (finding["severity"], finding["category"], finding["summary"])
        if key in seen:
            continue
        seen.add(key)
        output.append(finding)
    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(output, key=lambda item: (severity_order.get(item["severity"], 9), item["category"]))


def _format_strength(value: str) -> str:
    value = str(value).strip()
    if not value:
        return ""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(mg|mcg|g|ml|iu)", value.lower())
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return value


def _summarize_symptoms(symptoms: List[str]) -> Dict[str, object]:
    title_map = {
        "fever": "Fever",
        "cough": "Cough",
        "fatigue": "Fatigue",
        "headache": "Headache",
        "chills": "Chills",
        "body pain": "Body pain",
        "sore throat": "Sore throat",
        "burning urination": "Burning urination",
    }
    display = [title_map.get(item, item.title()) for item in symptoms]

    symptom_set = set(symptoms)
    if {"fever", "cough"} <= symptom_set:
        suggestion = "Suggests mild infection (likely viral or bacterial respiratory illness)"
    elif {"cough", "fatigue", "headache"} <= symptom_set:
        suggestion = "Suggests a respiratory or viral illness pattern"
    elif {"fever", "burning urination"} <= symptom_set:
        suggestion = "Suggests urinary tract infection pattern"
    elif {"fever", "chills"} <= symptom_set:
        suggestion = "Suggests a febrile infection pattern that may need malaria evaluation"
    elif {"abdominal pain", "vomiting"} <= symptom_set:
        suggestion = "Suggests a gastrointestinal illness pattern"
    elif {"rash", "itching"} <= symptom_set:
        suggestion = "Suggests an allergic or dermatologic pattern"
    elif symptoms:
        suggestion = "Symptoms suggest an acute illness pattern that should be correlated clinically"
    else:
        suggestion = "No clear symptom pattern was extracted"

    return {
        "items": display,
        "suggestion": suggestion,
    }


def _purpose_for_medicine(medicine: Dict[str, object]) -> Tuple[str, str, str]:
    generic_name = str(medicine.get("generic_name", "")).lower()
    uses = str(medicine.get("uses", "")).lower()
    description = str(medicine.get("description", "")).lower()
    source_hint = str(medicine.get("source_hint", "")).lower()
    instructions = str(medicine.get("instructions", "")).lower()
    text = " ".join([generic_name, uses, description, source_hint, instructions])

    exact_text = " ".join([generic_name, source_hint])

    for rule in THERAPEUTIC_CATEGORY_RULES:
        if any(keyword in exact_text for keyword in rule["keywords"]):
            return rule["purpose"], rule["category"], rule["family"]

    for keyword, purpose, category in MEDICATION_PURPOSE_RULES:
        if keyword in text:
            family = "general"
            if category == "acute":
                family = "acute_infection" if "antibiotic" in purpose.lower() else "symptomatic_relief"
            elif category == "chronic":
                family = "chronic"
            elif category == "supportive":
                family = "supportive_care"
            return purpose, category, family

    for rule in THERAPEUTIC_CATEGORY_RULES:
        if any(keyword in text for keyword in rule["keywords"]):
            return rule["purpose"], rule["category"], rule["family"]

    return "Purpose needs manual review", "unknown", "unknown"


def _summarize_medications(medicines: List[Dict[str, object]]) -> List[Dict[str, str]]:
    items = []
    for medicine in medicines:
        purpose, category, family = _purpose_for_medicine(medicine)
        name = str(medicine.get("brand_name") or medicine.get("generic_name") or "").strip()
        items.append(
            {
                "name": name,
                "strength": _format_strength(medicine.get("strength", "")),
                "frequency": str(medicine.get("frequency", "")).strip(),
                "purpose": purpose,
                "category": category,
                "family": family,
            }
        )
    return items


def _build_clinical_insight(symptoms: List[str], medications: List[Dict[str, str]], diagnoses: List[str]) -> str:
    categories = {item["category"] for item in medications}
    families = {item["family"] for item in medications}
    symptom_set = set(symptoms)

    if diagnoses:
        return f"This prescription should be interpreted against the documented diagnosis: {', '.join(diagnoses)}."
    if "acute" in categories and "chronic" in categories:
        return (
            "This is a mixed prescription: Acute illness treatment plus chronic disease management."
        )
    if "acute_infection" in families and "supportive_care" in families:
        return "This prescription combines likely infection treatment with supportive symptom control."
    if "cardiometabolic_chronic" in families and len(families) == 1:
        return "This prescription is mainly focused on cardiometabolic chronic disease management."
    if "metabolic_chronic" in families and len(families) == 1:
        return "This prescription is mainly focused on diabetes or metabolic disease management."
    if {"fever", "cough"} <= symptom_set:
        return "This prescription appears focused on symptomatic treatment of a respiratory infection pattern."
    if "chronic" in categories:
        return "This prescription appears focused on chronic disease management."
    return "This prescription should be interpreted in the context of the treating clinician's diagnosis."


def _extract_instruction_lines(text: str, medicines: List[Dict[str, object]]) -> List[str]:
    instructions = []
    for medicine in medicines:
        value = str(medicine.get("instructions", "")).strip()
        if value:
            instructions.append(value)

    sections = _split_sections(text)
    notes = sections.get("notes", "")
    if notes:
        for line in notes.splitlines():
            cleaned = re.sub(r"^[*\-\u2022]+\s*", "", line).strip()
            if cleaned:
                instructions.append(cleaned)

    followup = sections.get("followup") or sections.get("follow_up") or ""
    for line in followup.splitlines():
        cleaned = line.strip()
        if cleaned:
            instructions.append(cleaned)

    preferred = []
    for line in instructions:
        lower = line.lower()
        if "complete the entire course" in lower:
            preferred.append("Complete antibiotic course")
        elif "avoid alcohol" in lower or "grapefruit juice" in lower:
            preferred.append("Avoid alcohol & grapefruit juice")
        elif "do not skip doses" in lower:
            preferred.append("Don't skip doses")
        elif "follow up" in lower or "visit on" in lower:
            preferred.append("Follow-up scheduled in 2 weeks")

    if preferred:
        return list(dict.fromkeys(preferred))

    return list(dict.fromkeys(instructions))[:6]


def _extract_document_dates(text: str) -> Dict[str, str]:
    dates = {
        "prescription_date": "",
        "follow_up_date": "",
    }
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    date_patterns = [
        r"\b\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}\b",
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        r"\b[A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}\b",
    ]

    def _find_date_value(value: str) -> str:
        for pattern in date_patterns:
            match = re.search(pattern, value)
            if match:
                return match.group(0)
        return ""

    for line in lines:
        lower = line.lower()
        if not dates["prescription_date"] and lower.startswith("date"):
            dates["prescription_date"] = _find_date_value(line)
        if not dates["follow_up_date"] and ("follow up" in lower or "followup" in lower or "visit on" in lower):
            dates["follow_up_date"] = _find_date_value(line)

    return dates


def _extract_patient_name(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines[:20]:
        match = re.search(r"\bpatient\s+name\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{1,60})$", line, flags=re.IGNORECASE)
        if match:
            candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
            if 2 <= len(candidate.split()) <= 5:
                return candidate

    for line in lines[:20]:
        match = re.search(r"\bpatient\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{1,60})$", line, flags=re.IGNORECASE)
        if match:
            candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
            if 2 <= len(candidate.split()) <= 5 and not _looks_like_complaint_or_heading(candidate):
                return candidate

    for line in lines[:12]:
        if any(word in line.lower() for word in ["dr.", "hospital", "clinic", "reg. no", "ph:", "timing", "address:", "amount paid", "id:", "age:", "age/sex", "date:"]):
            continue
        if re.search(r"\b(male|female|born|patient)\b", line.lower()):
            parts = re.split(r",|\bmale\b|\bfemale\b|\bborn\b|\bpatient\b", line, maxsplit=1, flags=re.IGNORECASE)
            candidate = parts[0].strip()
            if (
                2 <= len(candidate.split()) <= 4
                and not _looks_like_complaint_or_heading(candidate)
                and not _looks_like_address_or_clinic_line(candidate)
            ):
                return candidate
    return ""


def _extract_text_list(value: str) -> List[str]:
    items = []
    for raw_line in str(value).splitlines():
        cleaned = re.sub(r"^[^\w\d]+", "", raw_line).strip()
        cleaned = re.sub(r"^\d+\)\s*", "", cleaned)
        if cleaned:
            items.append(cleaned)
    return items


def _looks_like_address_or_clinic_line(value: str) -> bool:
    lower = value.lower().strip()
    return bool(
        re.search(r"\b(road|rd\.?|street|st\.?|center|centre|business center|mg road|pune|nantes|france|hospital|clinic|closed|timing|reg\.?\s*no|mob\.?\s*no|phone|ph:|address)\b", lower)
        or re.search(r"\b\d{5,6}\b", lower)
        or re.search(r"^[a-z]/\d+", lower)
    )


def _looks_like_complaint_or_heading(value: str) -> bool:
    lower = value.lower().strip(" -*")
    return bool(
        re.search(r"\b(headache|fever|chills|cough|pain|vomiting|nausea|days?|chief complaints?|clinical findings?|diagnosis|prescription|medicine name|dosage|duration)\b", lower)
    )


def _extract_explicit_symptoms(text: str) -> List[str]:
    sections = _split_sections(text)
    source_blocks = [
        sections.get("symptoms", ""),
        sections.get("chief_complaints", ""),
        sections.get("complaints", ""),
    ]

    hits: List[str] = []
    for block in source_blocks:
        for line in _extract_text_list(block):
            lower = line.lower()
            for symptom, patterns in SYMPTOM_PATTERNS.items():
                if any(re.search(pattern, lower) for pattern in patterns):
                    hits.append(symptom)

    if hits:
        return list(dict.fromkeys(hits))

    return _extract_symptoms(text)


def _extract_explicit_diagnosis(text: str) -> List[str]:
    sections = _split_sections(text)
    diagnoses: List[str] = []
    diagnosis_block = sections.get("diagnosis", "")
    if diagnosis_block:
        for line in _extract_text_list(diagnosis_block):
            lower = line.lower()
            if (
                lower in {"r", "rx"}
                or any(token in lower for token in [
                    "medicine name", "dosage", "duration", "tab.", "cap.", "tot:",
                    "follow up", "advice", "chief complaints", "clinical findings"
                ])
                or re.match(r"^\d+[\)\.]?\s*(tab\.|cap\.|tablet|capsule)\b", lower)
            ):
                continue
            diagnoses.append(line)

    for line in text.splitlines():
        match = re.search(r"^\s*diagnosis\s*[:\-]\s*(.+)$", line, flags=re.IGNORECASE)
        if match:
            diagnoses.extend([item.strip() for item in re.split(r"[;,/]| and ", match.group(1)) if item.strip()])

    cleaned = []
    for item in diagnoses:
        normalized = item.strip(" -*").strip()
        if normalized:
            cleaned.append(normalized)
    return list(dict.fromkeys(cleaned))


def _extract_explicit_tests(text: str) -> List[str]:
    sections = _split_sections(text)
    tests: List[str] = []

    for block_name in ["tests", "clinical_findings"]:
        block = sections.get(block_name, "")
        if not block:
            continue
        for line in _extract_text_list(block):
            for alias, canonical in TEST_ALIASES.items():
                if re.search(rf"\b{re.escape(alias)}\b", line.lower()):
                    tests.append(canonical)

    if tests:
        return list(dict.fromkeys(tests))

    return []


def _extract_advice_and_notes(text: str) -> List[str]:
    sections = _split_sections(text)
    items = []
    for block_name in ["advice", "notes"]:
        for line in _extract_text_list(sections.get(block_name, "")):
            if (
                "follow up" in line.lower()
                or "followup" in line.lower()
                or "substitute with equivalent" in line.lower()
                or "generics as required" in line.lower()
                or _looks_like_address_or_clinic_line(line)
            ):
                continue
            items.append(line)
    return list(dict.fromkeys(items))


def _extract_follow_up_text(text: str) -> str:
    sections = _split_sections(text)
    followup = sections.get("followup") or sections.get("follow_up") or ""
    lines = _extract_text_list(followup)
    if lines:
        return lines[0] if not _looks_like_address_or_clinic_line(lines[0]) else ""
    for line in text.splitlines():
        cleaned = line.strip()
        if "follow up" in cleaned.lower() or "followup" in cleaned.lower() or cleaned.lower().startswith("visit on"):
            date = _extract_document_dates(cleaned).get("follow_up_date", "")
            return date or cleaned
    return ""


def _is_non_prescription_document(text: str) -> bool:
    lower = text.lower()
    receipt_signals = [
        "amount paid", "payment details", "receipt amt", "particulars", "total :", "upi",
        "received with thanks", "price", "unit", "sac",
    ]
    prescription_signals = [
        "prescription", "rx", "diagnosis", "chief complaints", "medicine", "dosage", "advice",
    ]

    receipt_score = sum(1 for signal in receipt_signals if signal in lower)
    prescription_score = sum(1 for signal in prescription_signals if signal in lower)
    has_medicine_line = bool(re.search(r"\b(tab|tablet|cap|capsule|inj|syrup)\b", lower))
    return receipt_score >= 3 and prescription_score <= 1 and not has_medicine_line


def classify_document_text(text: str) -> str:
    lower = str(text).lower()

    if _is_non_prescription_document(text):
        return "non_prescription_document"

    strong_lab_patterns = [
        r"\b(pathology lab|clinical laboratory|lab report|test report)\b",
        r"\b(investigation|result|reference value|unit)\b",
        r"\b(liver function test|complete blood count|cbc|lipid profile|thyroid profile|kidney function test|lft)\b",
    ]
    lab_table_signal = (
        ("investigation" in lower and "reference value" in lower)
        or ("result" in lower and "reference range" in lower)
        or ("sample collected" in lower and "reported on" in lower)
    )
    lab_marker_count = sum(1 for pattern in strong_lab_patterns if re.search(pattern, lower))
    lab_test_count = sum(1 for keyword in LAB_ROUTE_KEYWORDS if keyword in lower)
    explicit_prescription_terms = any(
        term in lower for term in ["prescription", "\nrx\n", " medicine name ", " dosage ", " duration "]
    )
    if (lab_table_signal or lab_marker_count >= 2 or lab_test_count >= 4) and not explicit_prescription_terms:
        return "lab_report"

    prescription_signals = [
        "prescription", "\nrx\n", "rx", "diagnosis", "chief complaints", "complaints",
        "advice", "follow up", "followup", "medicine", "dosage", "duration",
    ]
    prescription_score = sum(1 for signal in prescription_signals if signal in lower)
    prescription_score += len(_extract_medicines(text))
    prescription_score += len(_extract_explicit_diagnosis(text)) * 2
    prescription_score += len(_extract_explicit_symptoms(text))
    prescription_score += len(_extract_advice_and_notes(text))
    if _extract_follow_up_text(text):
        prescription_score += 1

    lab_score = sum(1 for keyword in LAB_ROUTE_KEYWORDS if keyword in lower)
    if re.search(r"\b(hemoglobin|creatinine|platelet|wbc|rbc|tsh|hba1c|bilirubin|sgot|sgpt|ast|alt|ggtp|albumin|globulin)\b", lower):
        lab_score += 2
    if lab_table_signal:
        lab_score += 6

    radiology_terms = [
        "radiology", "impression", "ultrasound", "usg", "ct scan", "mri", "x-ray", "xray",
        "sonography", "findings suggestive",
    ]
    radiology_score = sum(1 for term in radiology_terms if term in lower)

    if radiology_score >= max(prescription_score, lab_score, 2):
        return "radiology_report"
    if lab_score >= max(prescription_score, radiology_score, 2):
        return "lab_report"
    if prescription_score >= max(lab_score, radiology_score, 2):
        return "prescription"
    return "non_prescription_document"


def _build_safe_flags(extracted: Dict[str, object]) -> List[Dict[str, str]]:
    flags = []

    if not extracted["medicines"]:
        flags.append({
            "type": "missing_medicines",
            "message": "No clear medicine entries were extracted from the prescription.",
        })

    if not extracted["diagnosis"]:
        flags.append({
            "type": "missing_diagnosis",
            "message": "No explicit diagnosis was found on the document.",
        })

    low_confidence = [
        medicine.get("original_line", "")
        for medicine in extracted["medicines"]
        if medicine.get("mapping_confidence", 0.0) < 0.75
    ]
    if low_confidence:
        flags.append({
            "type": "uncertain_medicine_mapping",
            "message": "Some medicine names may need manual review.",
        })

    return flags


def _build_basic_medication_view(medicines: List[Dict[str, object]]) -> List[Dict[str, str]]:
    items = []
    for medicine in medicines:
        item = {
            "name": str(medicine.get("brand_name") or medicine.get("generic_name") or "").strip(),
            "generic_name": str(medicine.get("generic_name", "")).strip(),
            "strength": _format_strength(medicine.get("strength", "")),
            "frequency": str(medicine.get("frequency", "")).strip(),
            "duration": str(medicine.get("duration", "")).strip(),
            "instructions": str(medicine.get("instructions", "")).strip(),
        }
        uses_summary = _build_medicine_uses_summary(medicine)
        if uses_summary:
            item["uses"] = uses_summary
        side_effects = medicine.get("side_effects") or []
        if side_effects:
            item["side_effects"] = ", ".join(str(effect) for effect in side_effects[:5])
        items.append(item)
    return items


def _build_medicine_uses_summary(medicine: Dict[str, object]) -> str:
    generic_name = _normalize_text(medicine.get("generic_name", ""))
    if generic_name in SAFE_GENERIC_USES:
        return SAFE_GENERIC_USES[generic_name]

    mapping_confidence = float(medicine.get("mapping_confidence", 0.0) or 0.0)
    if mapping_confidence < 0.9:
        return ""

    uses = str(medicine.get("uses", "")).strip()
    description = str(medicine.get("description", "")).strip()
    source_text = uses or description
    if not source_text:
        return ""

    source_text = re.sub(r"\s+", " ", source_text).strip()
    if source_text and not source_text.endswith((".", "!", "?")):
        source_text += "."

    sentences = re.split(r"(?<=[.!?])\s+", source_text)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    summary = " ".join(sentences[:2]).strip()

    normalized_summary = _normalize_text(summary)
    if generic_name and generic_name not in normalized_summary and len(normalized_summary.split()) > 8:
        return ""

    return summary


def _omit_empty_fields(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            normalized = _omit_empty_fields(item)
            if normalized in ("", None, [], {}):
                continue
            cleaned[key] = normalized
        return cleaned
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            normalized = _omit_empty_fields(item)
            if normalized in ("", None, [], {}):
                continue
            cleaned_list.append(normalized)
        return cleaned_list
    return value


def _build_public_extraction(extracted: Dict[str, object]) -> Dict[str, object]:
    return {
        "patient_name": extracted["patient_name"],
        "patient_context": extracted["patient_context"],
        "vitals": extracted["vitals"],
        "prescription_date": extracted["prescription_date"],
        "diagnosis": extracted["diagnosis"],
        "symptoms": [item.replace("_", " ").title() for item in extracted["symptoms"]],
        "medications": _build_basic_medication_view(extracted["medicines"]),
        "tests": extracted["tests"],
        "advice_notes": extracted["advice_notes"],
        "follow_up": extracted["follow_up"] or extracted["follow_up_date"],
    }


def analyze_prescription_text(text: str) -> Dict[str, object]:
    if _is_non_prescription_document(text):
        return _omit_empty_fields({
            "structured_extraction": {
                "patient_name": "",
                "patient_context": {"age": None, "gender": None},
                "prescription_date": "",
                "diagnosis": [],
                "symptoms": [],
                "medications": [],
                "tests": [],
                "advice_notes": [],
                "follow_up": "",
            },
            "safe_flags": [
                {
                    "type": "unsupported_document",
                    "message": "This looks like a billing receipt or payment document, not a prescription.",
                }
            ],
            "disclaimer": "Only prescription-style medical documents are supported for structured extraction.",
        })

    extracted = {
        "patient_name": _extract_patient_name(text),
        "patient_context": _extract_patient_context(text),
        "vitals": _extract_vitals(text),
        "prescription_date": _extract_document_dates(text).get("prescription_date", ""),
        "follow_up_date": _extract_document_dates(text).get("follow_up_date", ""),
        "diagnosis": _extract_explicit_diagnosis(text),
        "symptoms": _extract_explicit_symptoms(text),
        "tests": _extract_explicit_tests(text),
        "medicines": _extract_medicines(text),
        "advice_notes": _extract_advice_and_notes(text),
        "follow_up": _extract_follow_up_text(text),
    }

    public_extraction = _build_public_extraction(extracted)
    safe_flags = _build_safe_flags(extracted)

    return _omit_empty_fields({
        "structured_extraction": public_extraction,
        "safe_flags": safe_flags,
        "disclaimer": "This response is limited to structured extraction from the document and avoids clinical interpretation.",
    })
