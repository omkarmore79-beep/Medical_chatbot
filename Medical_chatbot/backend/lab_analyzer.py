# lab_analyzer.py

from typing import List, Dict
from lab_explainer import generate_explanation


DISCLAIMER = "⚠ Please consult your doctor for proper medical evaluation and personalized treatment advice."


# ==========================================================
# 1️⃣ PANEL MAPPING
# ==========================================================

TEST_PANELS = {

    # Vitamins
    "VITAMIN_D": "Essential Vitamin Panel",
    "VITAMIN_B12": "Essential Vitamin Panel",
    "FOLATE": "Essential Vitamin Panel",
    "VITAMIN_A": "Essential Vitamin Panel",
    "VITAMIN_E": "Essential Vitamin Panel",
    "VITAMIN_K1": "Essential Vitamin Panel",
    "VITAMIN_B1": "Essential Vitamin Panel",
    "VITAMIN_B6": "Essential Vitamin Panel",
    "VITAMIN_C": "Essential Vitamin Panel",

    # CBC
    "HEMOGLOBIN": "Complete Blood Count (CBC)",
    "RBC": "Complete Blood Count (CBC)",
    "PCV": "Complete Blood Count (CBC)",
    "MCV": "Complete Blood Count (CBC)",
    "MCH": "Complete Blood Count (CBC)",
    "MCHC": "Complete Blood Count (CBC)",
    "RDW": "Complete Blood Count (CBC)",
    "WBC": "Complete Blood Count (CBC)",
    "NEUTROPHILS": "Complete Blood Count (CBC)",
    "LYMPHOCYTES": "Complete Blood Count (CBC)",
    "MONOCYTES": "Complete Blood Count (CBC)",
    "EOSINOPHILS": "Complete Blood Count (CBC)",
    "BASOPHILS": "Complete Blood Count (CBC)",
    "PLATELET": "Complete Blood Count (CBC)",
    "MPV": "Complete Blood Count (CBC)",
    "ESR": "Complete Blood Count (CBC)",

    # Diabetes
    "FBS": "Diabetes & Metabolic Profile",
    "PPBS": "Diabetes & Metabolic Profile",
    "RBS": "Diabetes & Metabolic Profile",
    "HBA1C": "Diabetes & Metabolic Profile",
    "INSULIN": "Diabetes & Metabolic Profile",
    "C_PEPTIDE": "Diabetes & Metabolic Profile",

    # Lipid
    "TOTAL_CHOLESTEROL": "Lipid Profile",
    "LDL": "Lipid Profile",
    "HDL": "Lipid Profile",
    "VLDL": "Lipid Profile",
    "TRIGLYCERIDES": "Lipid Profile",
    "TC_HDL_RATIO": "Lipid Profile",

    # Liver
    "TOTAL_BILIRUBIN": "Liver Function Test (LFT)",
    "DIRECT_BILIRUBIN": "Liver Function Test (LFT)",
    "SGOT": "Liver Function Test (LFT)",
    "SGPT": "Liver Function Test (LFT)",
    "AST_ALT_RATIO": "Liver Function Test (LFT)",
    "ALP": "Liver Function Test (LFT)",
    "TOTAL_PROTEIN": "Liver Function Test (LFT)",
    "ALBUMIN": "Liver Function Test (LFT)",
    "GLOBULIN": "Liver Function Test (LFT)",
    "A_G_RATIO": "Liver Function Test (LFT)",
    "GGT": "Liver Function Test (LFT)",

    # Kidney
    "CREATININE": "Kidney Function Test (KFT)",
    "BUN": "Kidney Function Test (KFT)",
    "URIC_ACID": "Kidney Function Test (KFT)",
    "UREA": "Kidney Function Test (KFT)",
    "EGFR": "Kidney Function Test (KFT)",

    # Thyroid
    "TSH": "Thyroid Profile",
    "T3": "Thyroid Profile",
    "T4": "Thyroid Profile",
    "FT3": "Thyroid Profile",
    "FT4": "Thyroid Profile",

    # Minerals
    "SERUM_IRON": "Minerals & Electrolytes",
    "FERRITIN": "Minerals & Electrolytes",
    "TIBC": "Minerals & Electrolytes",
    "CALCIUM": "Minerals & Electrolytes",
    "MAGNESIUM": "Minerals & Electrolytes",
    "PHOSPHORUS": "Minerals & Electrolytes",
    "SODIUM": "Minerals & Electrolytes",
    "POTASSIUM": "Minerals & Electrolytes",
    "CHLORIDE": "Minerals & Electrolytes",
}


# ==========================================================
# 2️⃣ OPTIONAL SEVERITY GRADING
# ==========================================================

def calculate_severity(value: float, normal_range: str, status: str) -> str:
    try:
        low, high = normal_range.split("-")
        low = float(low.strip())
        high = float(high.strip())

        if status == "LOW":
            deviation = (low - value) / (high - low)
        else:
            deviation = (value - high) / (high - low)

        if deviation < 0.25:
            return "Mild"
        elif deviation < 0.75:
            return "Moderate"
        else:
            return "Severe"

    except:
        return "Unclassified"


# ==========================================================
# 3️⃣ FINAL OUTPUT GENERATOR
# ==========================================================

def generate_final_lab_output(lab_results: List[Dict]) -> Dict:

    if not lab_results:
        return {
            "lab_analysis": [],
            "message": "No recognizable lab values were found.",
            "disclaimer": DISCLAIMER
        }

    abnormal_results = [item for item in lab_results if item.get("status") not in {"NORMAL", "BORDERLINE"}]
    attention_results = [item for item in lab_results if item.get("status") != "NORMAL"]
    explanations = generate_explanation(abnormal_results) if abnormal_results else {}

    final_output = []

    for item in lab_results:

        test_name = item["test_name"]
        panel = TEST_PANELS.get(test_name, "General Lab Test")

        severity = (
            "Normal"
            if item["status"] == "NORMAL"
            else "Borderline"
            if item["status"] == "BORDERLINE"
            else calculate_severity(
                item["value"],
                item["normal_range"],
                item["status"]
            )
        )

        final_output.append({
            "test_name": test_name,
            "panel": panel,
            "value": item["value"],
            "normal_range": item["normal_range"],
            "status": item["status"],
            "severity": severity,
            "interpretation": explanations.get(
                test_name,
                "This value is within the provided reference range."
                if item["status"] == "NORMAL"
                else "This value is at the lower limit of the provided reference range."
                if item["status"] == "BORDERLINE"
                else "This value is outside the normal reference range."
            )
        })

    return {
        "lab_analysis": final_output,
        "message": (
            "All detected values are within the supported reference ranges."
            if not attention_results
            else f"{len(attention_results)} detected value(s) need attention."
        ),
        "disclaimer": DISCLAIMER
    }
