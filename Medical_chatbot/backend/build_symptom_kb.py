import os
import pandas as pd

KB_DIR = "knowledge_base"
SYMPTOM_FILE = os.path.join(KB_DIR, "Symptom_Disease_Mapping_3000.xlsx")
OUT_FILE = os.path.join(KB_DIR, "symptom_kb.csv")


def find_col(df, candidates):
    norm = {
        str(c).strip().lower().replace(" ", "").replace("_", ""): c
        for c in df.columns
    }
    for cand in candidates:
        key = cand.strip().lower().replace(" ", "").replace("_", "")
        if key in norm:
            return norm[key]
    return None


def main():
    if not os.path.exists(SYMPTOM_FILE):
        raise FileNotFoundError(f"Missing: {SYMPTOM_FILE}")

    df = pd.read_excel(SYMPTOM_FILE)

    disease_col = find_col(df, ["prognosis", "disease"]) or df.columns[-1]
    synonyms_col = find_col(df, ["symptom_synonyms", "synonyms"])
    followups_col = find_col(df, ["follow_up_questions", "followup_questions"])
    severity_col = find_col(df, ["severity_level", "severity"])
    action_col = find_col(df, ["recommended_action", "recommendedaction"])

    exclude = {disease_col}
    for c in [synonyms_col, followups_col, severity_col, action_col]:
        if c:
            exclude.add(c)

    symptom_cols = [c for c in df.columns if c not in exclude]

    rows = []

    for i, r in df.iterrows():
        disease = str(r[disease_col]).strip()

        active_symptoms = []
        for s in symptom_cols:
            try:
                if int(r[s]) == 1:
                    active_symptoms.append(str(s).replace("_", " ").strip())
            except:
                pass

        synonyms = str(r[synonyms_col]).strip() if synonyms_col else "N/A"
        followups = str(r[followups_col]).strip() if followups_col else "N/A"
        severity = str(r[severity_col]).strip() if severity_col else "N/A"
        action = str(r[action_col]).strip() if action_col else "N/A"

        text = f"""TYPE: SYMPTOM_DISEASE
DISEASE: {disease}
SYMPTOMS: {", ".join(active_symptoms)}
SYMPTOM_SYNONYMS: {synonyms}
FOLLOW_UP_QUESTIONS: {followups}
SEVERITY_LEVEL: {severity}
RECOMMENDED_ACTION: {action}
""".strip()

        rows.append({"id": f"sym_{i}", "text": text})

    pd.DataFrame(rows).to_csv(OUT_FILE, index=False, encoding="utf-8")

    print("OK: Symptom KB built")
    print("Output:", OUT_FILE)
    print("Docs:", len(rows))


if __name__ == "__main__":
    main()