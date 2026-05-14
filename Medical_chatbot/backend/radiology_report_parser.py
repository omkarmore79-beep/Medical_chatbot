import re
from typing import Dict, List


RADIOLOGY_KEYWORDS = [
    "radiology",
    "impression",
    "sonography",
    "ultrasound",
    "usg",
    "ct scan",
    "mri",
    "x-ray",
    "xray",
    "scan",
]

STUDY_PATTERNS = [
    r"\busg\s+[a-z&\s]+",
    r"\bultrasound\s+[a-z&\s]+",
    r"\bct\s+[a-z&\s]+",
    r"\bmri\s+[a-z&\s]+",
    r"\bx[\s-]?ray\s+[a-z&\s]+",
    r"\bsonography\s+[a-z&\s]+",
]

ABNORMAL_HINTS = [
    "lesion",
    "mass",
    "nodule",
    "cyst",
    "hemangioma",
    "stone",
    "calculus",
    "hydroureter",
    "hydronephrosis",
    "fatty liver",
    "hepatomegaly",
    "thickening",
    "fluid",
    "effusion",
    "fracture",
    "opacity",
    "consolidation",
    "fibroid",
    "adenoma",
    "collection",
    "abnormal",
    "suggestive",
]

NORMAL_HINTS = [
    "appears normal",
    "normal in size",
    "normal in echotexture",
    "normal echopattern",
    "no focal lesion",
    "no evidence of calculus",
    "no hydronephrosis",
    "well distended and appears normal",
    "no evidence of any adnexal pathology",
    "no free fluid",
    "shows normal peristalsis",
]

SECTION_STOP_HINTS = [
    "not valid for medico legal purpose",
    "professional opinion",
    "end of the report",
    "should always be considered in correlation",
    "clinical and laboratory findings",
    "clinical and lab findings",
    "advised clinical correlation",
    "correlate clinically",
]

ORGAN_LABELS = [
    "liver",
    "gall bladder",
    "gallbladder",
    "spleen",
    "pancreas",
    "kidney",
    "kidneys",
    "urinary bladder",
    "bladder",
    "uterus",
    "ovaries",
    "ovary",
    "bowel loops",
]


def _normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", str(line)).strip(" -:\t")


def is_radiology_report(text: str) -> bool:
    normalized = _normalize_text(text).lower()
    score = sum(1 for keyword in RADIOLOGY_KEYWORDS if keyword in normalized)
    if any(token in normalized for token in ["department of radiology", "impression", "findings suggestive"]):
        score += 2
    if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in STUDY_PATTERNS):
        score += 2
    return score >= 2


def _extract_study_name(lines: List[str]) -> str:
    for line in lines[:20]:
        cleaned = _clean_line(line)
        lower = cleaned.lower()
        if any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in STUDY_PATTERNS):
            return cleaned.upper()
    return ""


def _extract_impression(text: str) -> str:
    normalized = _normalize_text(text)
    block = ""

    lines = normalized.splitlines()
    for index, raw_line in enumerate(lines):
        line = _clean_line(raw_line)
        lower = line.lower()
        if not lower.startswith("impression"):
            continue

        after_label = re.sub(r"^impression[:\-\s]*", "", line, flags=re.IGNORECASE).strip()
        collected = []
        if after_label:
            collected.append(after_label)

        next_index = index + 1
        while next_index < len(lines):
            next_line = _clean_line(lines[next_index])
            if not next_line:
                break
            if re.match(r"^[A-Z][A-Z\s/&()-]{3,}:?$", next_line):
                break
            collected.append(next_line)
            if any(hint in next_line.lower() for hint in SECTION_STOP_HINTS):
                break
            next_index += 1

        block = " ".join(collected).strip()
        break

    if not block:
        return ""

    lines = []
    for raw_line in block.splitlines():
        line = _clean_line(raw_line)
        if not line:
            break
        lines.append(line)
        if any(hint in line.lower() for hint in SECTION_STOP_HINTS):
            break
    impression = " ".join(lines).strip()

    # Trim trailing disclaimer fragments that may appear on the same line.
    inline_stop_patterns = [
        r"\(\s*the sonography findings should always be considered.*$",
        r"\bthe sonography findings should always be considered.*$",
        r"\bclinical and laboratory findings.*$",
        r"\badvised clinical correlation.*$",
        r"\bcorrelate clinically.*$",
    ]
    for pattern in inline_stop_patterns:
        impression = re.sub(pattern, "", impression, flags=re.IGNORECASE).strip(" .-(")

    if impression:
        impression = impression.strip()
        if not impression.endswith("."):
            impression += "."
    return impression


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]


def _extract_finding_sentences(text: str) -> List[str]:
    normalized = _normalize_text(text)
    sentences = _split_sentences(normalized.replace("\n", " "))
    findings = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(stop in lower for stop in SECTION_STOP_HINTS):
            continue
        if lower.startswith("impression"):
            continue
        if lower.startswith("no ") or "no evidence of" in lower or "no focal lesion" in lower:
            continue
        if any(hint in lower for hint in ABNORMAL_HINTS):
            findings.append(sentence)
    return findings


def _extract_normal_sentences(text: str) -> List[str]:
    normalized = _normalize_text(text)
    sentences = _split_sentences(normalized.replace("\n", " "))
    normals = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(hint in lower for hint in NORMAL_HINTS):
            normals.append(sentence)
    return normals


def _shorten_finding(sentence: str) -> str:
    sentence = _clean_line(sentence)
    sentence = re.sub(r"^(a|an)\s+", "", sentence, flags=re.IGNORECASE)
    return sentence


def _extract_organs_noted_normal(normal_sentences: List[str]) -> List[str]:
    organs = []
    lowered = " ".join(normal_sentences).lower()
    for organ in ORGAN_LABELS:
        if organ in lowered:
            organs.append(organ.title())
    filtered = []
    for organ in organs:
        if organ == "Kidney" and "Kidneys" in organs:
            continue
        if organ == "Bladder" and "Urinary Bladder" in organs:
            continue
        filtered.append(organ)
    return list(dict.fromkeys(filtered))


def _simple_meaning(impression: str, findings: List[str]) -> str:
    text = f"{impression} {' '.join(findings)}".lower()
    if "hemangioma" in text:
        return (
            "A liver hemangioma is usually a benign blood-vessel lesion in the liver. "
            "It is often found incidentally on imaging."
        )
    if "cyst" in text:
        return "A cyst usually means a fluid-filled sac. Its significance depends on the organ, size, and report context."
    if "stone" in text or "calculus" in text:
        return "This suggests a stone is present in the reported organ or duct."
    if "fatty liver" in text:
        return "This suggests fat deposition in the liver, which is commonly called fatty liver."
    return "This report should be correlated with your symptoms and your doctor's clinical assessment."


def summarize_radiology_report(text: str) -> Dict:
    normalized = _normalize_text(text)
    lines = [line for line in normalized.splitlines() if _clean_line(line)]

    study_name = _extract_study_name(lines)
    impression = _extract_impression(normalized)
    abnormal_findings = [_shorten_finding(item) for item in _extract_finding_sentences(normalized)]
    normal_sentences = _extract_normal_sentences(normalized)
    normal_organs = _extract_organs_noted_normal(normal_sentences)

    main_finding = impression or (abnormal_findings[0] if abnormal_findings else "")
    summary_parts = []
    if study_name:
        summary_parts.append(f"Scan type: {study_name}.")
    if main_finding:
        summary_parts.append(f"Main finding: {main_finding}")
    if normal_organs:
        summary_parts.append(f"Structures described as normal include: {', '.join(normal_organs[:8])}.")

    follow_up = (
        "Discuss this report with your treating doctor, especially if you have symptoms, ongoing pain, "
        "or if follow-up imaging has been advised."
    )

    return {
        "study_name": study_name or "Radiology study",
        "impression": impression or "No separate impression section was clearly extracted.",
        "main_finding": main_finding or "No clear abnormal finding was extracted.",
        "abnormal_findings": abnormal_findings[:6],
        "normal_structures": normal_organs[:10],
        "simple_explanation": _simple_meaning(impression, abnormal_findings),
        "summary": " ".join(summary_parts).strip(),
        "recommended_follow_up": follow_up,
        "disclaimer": "This is an educational summary of the report text, not a medical diagnosis.",
    }
