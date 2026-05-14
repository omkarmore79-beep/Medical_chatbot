import re
from difflib import SequenceMatcher

from brand_mapping import brand_aliases, brand_to_generic


DOSAGE_WORDS = [
    "tab", "tab.", "tablet", "tablets",
    "cap", "cap.", "capsule", "capsules",
    "syp", "syp.", "syr", "syr.", "syrup",
    "inj", "inj.", "injection",
    "drop", "drops",
]

FREQUENCY_WORDS = [
    "od", "bd", "tds", "hs", "sos", "qid", "tid", "bid",
    "morning", "night", "after", "food", "before", "daily",
]

STOP_WORDS = {
    "rx", "r", "ml", "mg", "mcg", "gm", "g", "iu", "units", "x",
    "days", "day", "months", "month", "weeks", "week", "if", "fever",
    "for", "times", "once", "twice", "thrice", "needed", "pain",
    "stat", "afterfood", "beforefood",
}


def _normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _normalize_ocr_token(token: str) -> str:
    token = token.lower()
    if re.search(r"[a-z]", token):
        token = token.replace("0", "o")
        token = token.replace("5", "s")
        token = token.replace("8", "b")
        token = token.replace("6", "g")
    return token


def _build_brand_lookup():
    lookup = {}

    for brand, generic in brand_to_generic.items():
        key = _normalize_text(brand)
        if key:
            lookup[key] = {
                "brand": brand,
                "generic": generic,
                "match_type": "exact",
            }

    for alias, canonical in brand_aliases.items():
        alias_key = _normalize_text(alias)
        canonical_key = _normalize_text(canonical)
        if not alias_key or alias_key in lookup:
            continue

        if canonical_key in lookup:
            lookup[alias_key] = {
                "brand": lookup[canonical_key]["brand"],
                "generic": lookup[canonical_key]["generic"],
                "match_type": "alias",
            }
        elif canonical_key in brand_to_generic:
            lookup[alias_key] = {
                "brand": canonical,
                "generic": brand_to_generic[canonical_key],
                "match_type": "alias",
            }

    return lookup


BRAND_LOOKUP = _build_brand_lookup()
BRAND_KEYS = list(BRAND_LOOKUP.keys())


def _clean_medicine_tokens(line: str):
    line = line.lower()
    line = re.sub(r"^[\d\s\)\(\.-]*", "", line)
    line = line.replace("℞", " ")
    line = re.sub(r"\brx\b", " ", line)
    line = re.sub(r"\(.*?\)", " ", line)
    line = re.sub(r"\b\d+\s*-\s*\d+\s*-\s*\d+\b", " ", line)
    line = re.sub(r"\b\d+/\d+/\d+\b", " ", line)
    line = _normalize_text(line)

    tokens = []
    for token in line.split():
        token = _normalize_ocr_token(token)
        if token in DOSAGE_WORDS or token in FREQUENCY_WORDS or token in STOP_WORDS:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?", token):
            continue
        tokens.append(token)

    return tokens


def _generate_candidate_phrases(tokens):
    if not tokens:
        return []

    candidates = []
    max_size = min(4, len(tokens))

    for size in range(max_size, 0, -1):
        for i in range(0, len(tokens) - size + 1):
            phrase = " ".join(tokens[i:i + size]).strip()
            if phrase and phrase not in candidates:
                candidates.append(phrase)

    return candidates


def _best_fuzzy_match(candidates):
    best = None

    for candidate in candidates:
        if len(candidate) < 4:
            continue

        for key in BRAND_KEYS:
            score = SequenceMatcher(None, candidate, key).ratio()
            min_score = 0.88
            if len(candidate) >= 7:
                min_score = 0.78
            if score < min_score:
                continue

            if best is None or score > best["score"]:
                best = {
                    "key": key,
                    "score": score,
                    "candidate": candidate,
                }

    return best


def resolve_medicine_line(line: str):
    tokens = _clean_medicine_tokens(line)
    candidates = _generate_candidate_phrases(tokens)

    for phrase in candidates:
        if phrase in BRAND_LOOKUP:
            hit = BRAND_LOOKUP[phrase]
            return {
                "input_line": line,
                "brand_name": hit["brand"],
                "generic_name": hit["generic"],
                "match_type": hit["match_type"],
                "confidence": 1.0 if hit["match_type"] == "exact" else 0.95,
            }

    fuzzy = _best_fuzzy_match(candidates)
    if fuzzy:
        hit = BRAND_LOOKUP[fuzzy["key"]]
        return {
            "input_line": line,
            "brand_name": hit["brand"],
            "generic_name": hit["generic"],
            "match_type": "fuzzy",
            "confidence": round(fuzzy["score"], 3),
        }

    fallback = " ".join(tokens[:2]).strip() if tokens else ""
    return {
        "input_line": line,
        "brand_name": fallback,
        "generic_name": fallback,
        "match_type": "unmapped",
        "confidence": 0.0,
    }


def extract_medicine_lines(text: str):
    lines = []

    for line in text.split("\n"):
        clean_line = line.strip()
        lower_line = clean_line.lower()

        if not clean_line:
            continue

        if any(dose in lower_line for dose in DOSAGE_WORDS):
            lines.append(clean_line)
            continue

        tokens = _clean_medicine_tokens(clean_line)
        candidates = _generate_candidate_phrases(tokens)
        has_known_candidate = any(phrase in BRAND_LOOKUP for phrase in candidates)
        has_schedule = bool(re.search(r"\b\d+\s*-\s*\d+\s*-\s*\d+\b", lower_line))

        if has_known_candidate or has_schedule:
            lines.append(clean_line)

    return lines


def normalize_medicine_name(line: str):
    resolved = resolve_medicine_line(line)
    return resolved["generic_name"]
