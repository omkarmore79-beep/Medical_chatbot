import re

# ==========================================================
# 1) NORMAL RANGES (General Adult Reference Ranges)
# NOTE: These are generalized ranges. Clinical labs vary.
# ==========================================================

NORMAL_RANGES = {

    # ---------------------------
    # Vitamins
    # ---------------------------
    "vitamin_d": (30, 100),                 # ng/mL
    "vitamin_b12": (200, 900),              # pg/mL
    "folate": (3, 20),                      # ng/mL
    "vitamin_a": (20, 60),                  # mcg/dL
    "vitamin_e": (5, 20),                   # mg/L
    "vitamin_k1": (0.2, 3.2),               # ng/mL
    "vitamin_b1": (70, 180),                # nmol/L
    "vitamin_b6": (5, 50),                  # mcg/L
    "vitamin_c": (0.4, 2.0),                # mg/dL

    # ---------------------------
    # CBC & Hematology
    # ---------------------------
    "hemoglobin": (13.0, 17.0),
    "rbc": (4.5, 5.9),
    "pcv": (40, 50),
    "mcv": (83, 101),
    "mch": (27, 32),
    "mchc": (31.5, 34.5),
    "rdw": (11.5, 14.5),
    "wbc": (4000, 11000),
    "neutrophils": (40, 80),
    "lymphocytes": (20, 40),
    "monocytes": (2, 10),
    "eosinophils": (1, 6),
    "basophils": (0, 2),
    "platelet": (150000, 450000),
    "mpv": (7.5, 11.5),
    "esr": (0, 20),

    # ---------------------------
    # Diabetes
    # ---------------------------
    "fbs": (70, 100),
    "ppbs": (70, 140),
    "rbs": (70, 140),
    "hba1c": (4.0, 5.6),
    "insulin": (2, 25),
    "c_peptide": (0.5, 2.0),

    # ---------------------------
    # Lipid Profile
    # ---------------------------
    "total_cholesterol": (0, 200),
    "ldl": (0, 100),
    "hdl": (40, 100),
    "vldl": (5, 40),
    "triglycerides": (0, 150),
    "tc_hdl_ratio": (0, 5),

    # ---------------------------
    # Liver Function
    # ---------------------------
    "total_bilirubin": (0.3, 1.2),
    "direct_bilirubin": (0, 0.3),
    "sgot": (0, 40),
    "sgpt": (0, 40),
    "ast_alt_ratio": (0, 1.0),
    "alp": (44, 147),
    "total_protein": (6.0, 8.3),
    "albumin": (3.5, 5.0),
    "globulin": (2.0, 3.5),
    "a_g_ratio": (1.0, 2.2),
    "ggt": (0, 60),

    # ---------------------------
    # Kidney Function
    # ---------------------------
    "creatinine": (0.7, 1.3),
    "bun": (7, 20),
    "uric_acid": (3.5, 7.2),
    "urea": (15, 40),
    "egfr": (90, 120),

    # ---------------------------
    # Thyroid
    # ---------------------------
    "tsh": (0.4, 4.0),
    "t3": (80, 200),
    "t4": (5, 12),
    "ft3": (2.0, 4.4),
    "ft4": (0.8, 1.8),

    # ---------------------------
    # Minerals & Electrolytes
    # ---------------------------
    "serum_iron": (60, 170),
    "ferritin": (30, 400),
    "tibc": (240, 450),
    "calcium": (8.6, 10.2),
    "magnesium": (1.7, 2.2),
    "phosphorus": (2.5, 4.5),
    "sodium": (135, 145),
    "potassium": (3.5, 5.0),
    "chloride": (98, 107),
}

# ==========================================================
# 2) TEST SYNONYMS
# ==========================================================

TEST_SYNONYMS = {
    "vitamin_d": ["vitamin d", "25-hydroxy"],
    "vitamin_b12": ["vitamin b12", "cobalamin"],
    "folate": ["folate", "vitamin b9"],
    "vitamin_a": ["vitamin a", "retinol"],
    "vitamin_e": ["vitamin e", "tocopherol"],
    "vitamin_k1": ["vitamin k1"],
    "vitamin_b1": ["vitamin b1", "thiamine"],
    "vitamin_b6": ["vitamin b6", "pyridoxine"],
    "vitamin_c": ["vitamin c", "ascorbic acid"],

    "hemoglobin": ["hemoglobin", "hb", "hemoglobin (hb)", "hb%", "haemoglobin"],
    "rbc": ["rbc", "red blood cell"],
    "pcv": ["pcv", "hematocrit", "hct", "packed cell volume (pcv)"],
    "mcv": ["mcv"],
    "mch": ["mch"],
    "mchc": ["mchc"],
    "rdw": ["rdw"],
    "wbc": ["wbc", "tlc", "total leukocyte count", "total count", "white blood cell count"],
    "neutrophils": ["neutrophil", "neutrophils"],
    "lymphocytes": ["lymphocyte", "lymphocytes"],
    "monocytes": ["monocyte", "monocytes"],
    "eosinophils": ["eosinophil", "eosinophils"],
    "basophils": ["basophil", "basophils"],
    "platelet": ["platelet", "platelets", "platelet count"],
    "mpv": ["mpv"],
    "esr": ["esr"],

    "fbs": [
        "fasting blood sugar",
        "blood sugar fasting",
        "blood glucose fasting",
        "blood glucose f",
        "blood glucose(f)",
        "fbs",
    ],
    "ppbs": [
        "post prandial",
        "post-prandial",
        "blood sugar post prandial",
        "blood glucose pp",
        "blood glucose(pp)",
        "blood glucose post prandial",
        "ppbs",
    ],
    "rbs": [
        "random blood sugar",
        "random blood glucose",
        "blood sugar random",
        "glucose random plasma",
        "rbs",
    ],
    "hba1c": ["hba1c", "glycated hemoglobin"],
    "insulin": ["insulin"],
    "c_peptide": ["c-peptide", "c peptide"],

    "total_cholesterol": ["total cholesterol"],
    "ldl": ["ldl"],
    "hdl": ["hdl"],
    "vldl": ["vldl"],
    "triglycerides": ["triglycerides"],
    "tc_hdl_ratio": ["tc/hdl", "tc hdl ratio", "tc:hdl"],

    "total_bilirubin": ["total bilirubin", "bilirubin total"],
    "direct_bilirubin": ["direct bilirubin", "bilirubin direct"],
    "sgot": ["sgot", "ast", "ast (sgot)"],
    "sgpt": ["sgpt", "alt", "alt (sgpt)"],
    "ast_alt_ratio": ["ast alt ratio", "ast : alt ratio", "ast:alt ratio"],
    "alp": ["alkaline phosphatase", "alp"],
    "total_protein": ["total protein"],
    "albumin": ["albumin"],
    "globulin": ["globulin"],
    "a_g_ratio": ["a/g ratio", "a:g ratio", "a : g ratio", "albumin globulin ratio"],
    "ggt": ["ggt", "ggtp"],

    "creatinine": ["creatinine", "serum creatinine", "sr creatinine", "s.creatinine"],
    "bun": ["bun", "blood urea nitrogen"],
    "uric_acid": ["uric acid"],
    "urea": ["urea"],
    "egfr": ["egfr"],

    "tsh": ["tsh", "thyroid stimulating hormone"],
    "t3": ["total t3", "t3 total serum", "tri-iodo thyronin", "triiodothyronine", "t3"],
    "t4": ["total t4", "t4 total serum", "thyroxin", "thyroxine", "t4"],
    "ft3": ["free t3", "ft3"],
    "ft4": ["free t4", "ft4"],

    "serum_iron": ["serum iron"],
    "ferritin": ["ferritin"],
    "tibc": ["tibc"],
    "calcium": ["calcium"],
    "magnesium": ["magnesium"],
    "phosphorus": ["phosphorus"],
    "sodium": ["sodium"],
    "potassium": ["potassium"],
    "chloride": ["chloride"],
}

# ==========================================================
# 3) MATCHING HELPERS
# ==========================================================

NUMBER_REGEX = re.compile(r"(?<![a-z0-9])(\d{1,3}(?:,\d{3})*(?:\.\d{1,4})?|\d{1,6}(?:\.\d{1,4})?)(?![a-z0-9])")
SECTION_STOP_TOKENS = [
    "note",
    "notes",
    "interpretation",
    "impression",
    "opinion",
    "advice",
    "thanks for reference",
    "end of report",
]


def _prepare_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[\t\r]+", " ", lowered)
    lowered = re.sub(r"\n+", "\n", lowered)
    return lowered


def _truncate_non_result_sections(text: str) -> str:
    lines = text.split("\n")
    kept = []

    for line in lines:
        compact = re.sub(r"[^a-z\s]", "", line).strip()
        if compact in SECTION_STOP_TOKENS or any(
            compact.startswith(token + " ") for token in SECTION_STOP_TOKENS
        ):
            break
        kept.append(line)

    return "\n".join(kept)


def _alias_to_regex(alias: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", alias.lower())
    if not tokens:
        return ""

    # Allow OCR punctuation/spacing noise between words.
    sep = r"[\s,;:()\/\-]*"
    return rf"\b{sep.join(map(re.escape, tokens))}\b"


def _find_test_in_text(text: str):
    for test_key, synonyms in TEST_SYNONYMS.items():
        for keyword in synonyms:
            alias_pattern = _alias_to_regex(keyword)
            if not alias_pattern:
                continue
            match = re.search(alias_pattern, text, flags=re.IGNORECASE)
            if match:
                return test_key, match.end()
    return None, None


def _parse_first_valid_number(text: str, test_key: str | None = None):
    value_match = NUMBER_REGEX.search(text)
    if not value_match:
        return None

    value = float(value_match.group(1).replace(",", ""))
    if value > 100000 and test_key not in {"platelet"}:
        return None
    return value


def _looks_like_table_header(line: str) -> bool:
    header_tokens = ["test", "investigation", "parameter", "result", "value", "observed"]
    hit_count = sum(1 for token in header_tokens if token in line)
    return hit_count >= 2


def _run_fallback_table_parser(searchable_text: str, results: list, seen: set):
    lines = [line.strip() for line in searchable_text.split("\n") if line.strip()]
    pending_test = None
    table_mode = False

    for line in lines:
        if any(line.startswith(token) for token in SECTION_STOP_TOKENS):
            break

        if _looks_like_table_header(line):
            table_mode = True
            pending_test = None
            continue

        if not table_mode:
            continue

        found_test, found_test_end = _find_test_in_text(line)
        found_value = None

        if found_test and found_test_end is not None:
            # Avoid capturing values embedded in test labels like "(T3)".
            found_value = _parse_first_valid_number(line[found_test_end:], found_test)
        else:
            found_value = _parse_first_valid_number(line)

        if found_test and found_test in seen:
            pending_test = None
            continue

        if found_test and found_value is not None:
            results.append({"test": found_test, "value": found_value})
            seen.add(found_test)
            pending_test = None
            continue

        if found_test and found_value is None:
            pending_test = found_test
            continue

        if pending_test and found_value is not None and pending_test not in seen:
            results.append({"test": pending_test, "value": found_value})
            seen.add(pending_test)
            pending_test = None


# ==========================================================
# 4) LAB REPORT DETECTION
# ==========================================================

def is_lab_report(text: str) -> bool:
    text_lower = _prepare_text(text)

    for synonyms in TEST_SYNONYMS.values():
        for keyword in synonyms:
            alias_pattern = _alias_to_regex(keyword)
            if alias_pattern and re.search(alias_pattern, text_lower, flags=re.IGNORECASE):
                return True

    return False


# ==========================================================
# 5) SAFE VALUE EXTRACTION
# ==========================================================
def extract_lab_values(text: str):
    results = []
    seen = set()

    searchable_text = _truncate_non_result_sections(_prepare_text(text))

    for test_key, synonyms in TEST_SYNONYMS.items():
        if test_key in seen:
            continue

        for keyword in synonyms:
            alias_pattern = _alias_to_regex(keyword)
            if not alias_pattern:
                continue

            for alias_match in re.finditer(alias_pattern, searchable_text, flags=re.IGNORECASE):
                # Look after test name on the same row. This avoids reading
                # values from the next test when a title contains words like ESR.
                line_end = searchable_text.find("\n", alias_match.end())
                if line_end == -1:
                    line_end = alias_match.end() + 150
                window = searchable_text[alias_match.end(): line_end]
                value_match = NUMBER_REGEX.search(window)

                if not value_match:
                    continue

                value = float(value_match.group(1).replace(",", ""))

                # Ignore obvious OCR garbage values.
                if value > 100000 and test_key not in {"platelet"}:
                    continue

                results.append({
                    "test": test_key,
                    "value": value
                })
                seen.add(test_key)
                break

            if test_key in seen:
                break

    # Fallback parser for table OCR where test/value may split across lines.
    if len(results) < 2:
        _run_fallback_table_parser(searchable_text, results, seen)

    return results


def extract_lab_report_metadata(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    metadata = {
        "patient_name": "",
        "age": "",
        "gender": "",
        "report_title": "",
        "report_interpretation": "",
    }

    for idx, line in enumerate(lines[:40]):
        lower = line.lower()

        if not metadata["patient_name"] and idx + 2 < len(lines):
            if lines[idx + 1].lower().startswith("age") and lines[idx + 2].lower().startswith("sex"):
                if re.match(r"^[A-Za-z][A-Za-z\s.'-]{2,60}$", line) and not any(
                    token in lower for token in ["lab", "pathology", "doctor", "sample", "registered", "collected", "reported"]
                ):
                    metadata["patient_name"] = re.sub(r"\s+", " ", line).strip()

        if not metadata["age"]:
            age_match = re.search(r"\bage\s*[:\-]?\s*(\d{1,3})", line, flags=re.IGNORECASE)
            if age_match:
                metadata["age"] = age_match.group(1)

        if not metadata["gender"]:
            sex_match = re.search(r"\bsex\s*[:\-]?\s*(male|female|m|f)\b", line, flags=re.IGNORECASE)
            if sex_match:
                raw = sex_match.group(1).lower()
                metadata["gender"] = "Male" if raw in {"male", "m"} else "Female"

        if not metadata["report_title"] and re.search(r"\b(complete blood count|cbc|esr|lipid profile|thyroid|liver function|kidney function|blood count)\b", lower):
            if not any(token in lower for token in ["reference", "investigation", "interpretation"]):
                metadata["report_title"] = re.sub(r"\s+", " ", line).strip()

        if not metadata["report_interpretation"]:
            interpretation_match = re.search(r"\binterpretation\s*[:\-]\s*(.+)$", line, flags=re.IGNORECASE)
            if interpretation_match:
                metadata["report_interpretation"] = interpretation_match.group(1).strip()

    return {key: value for key, value in metadata.items() if value}


# ==========================================================
# 6) INTERPRET RESULTS (Abnormal Only)
# ==========================================================

def interpret_lab_results(results, include_normal=False):
    interpreted = []

    for item in results:
        test = item["test"]
        value = item["value"]

        if test not in NORMAL_RANGES:
            continue

        low, high = NORMAL_RANGES[test]

        if value < low:
            status = "LOW"
        elif value > high:
            status = "HIGH"
        elif include_normal and test == "platelet" and value <= low:
            status = "BORDERLINE"
        elif include_normal:
            status = "NORMAL"
        else:
            continue

        interpreted.append({
            "test_name": test.upper(),
            "value": value,
            "normal_range": f"{low} - {high}",
            "status": status
        })

    return interpreted
