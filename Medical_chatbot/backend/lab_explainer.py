# lab_explainer.py

import os
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)
_lab_client = None


def get_lab_client():
    global _lab_client
    if _lab_client is None:
        # Render stability change: initialize the Gemini lab explainer client
        # only when abnormal lab explanations are requested.
        from google import genai

        logger.info("Model loading started: Gemini lab explainer client")
        _lab_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        logger.info("Model loading completed: Gemini lab explainer client")
    return _lab_client


def generate_explanation(abnormal_results: List[Dict]) -> Dict:

    if not abnormal_results:
        return {}

    # Convert list into clean readable format for LLM
    formatted_tests = [
        {
            "test_name": item["test_name"],
            "value": item["value"],
            "normal_range": item["normal_range"],
            "status": item["status"]
        }
        for item in abnormal_results
    ]

    prompt = f"""
You are a clinical laboratory medical assistant.

Return STRICT JSON only.

For EACH abnormal test provided, return:

{{
  "TEST_NAME": {{
    "interpretation": "What this abnormal value may indicate in simple educational terms.",
    "lifestyle_precautions": "General lifestyle advice only."
  }}
}}

Rules:
- No markdown
- No code block
- No extra text
- No diagnosis
- No medicines
- No emergency instructions
- Educational tone only
- Be medically safe

Abnormal Tests:
{json.dumps(formatted_tests, indent=2)}
"""

    try:
        response = get_lab_client().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        raw_text = response.text.strip()

        # Clean markdown if model adds it
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(raw_text)

        formatted_output = {}

        for test_name, content in parsed.items():
            interpretation = content.get("interpretation", "").strip()
            lifestyle = content.get("lifestyle_precautions", "").strip()

            if not interpretation:
                interpretation = "This value is outside the normal reference range and may require medical evaluation."

            if not lifestyle:
                lifestyle = "Maintain a balanced diet, regular exercise, and consult your doctor for guidance."

            formatted_output[test_name.upper()] = (
                f"{interpretation}\n\nLifestyle precautions: {lifestyle}"
            )

        return formatted_output

    except Exception as e:
        logger.error("Gemini Parsing Error: %s", e)

        # 🔥 SAFE FALLBACK
        fallback = {}
        for item in abnormal_results:
            fallback[item["test_name"]] = (
                "This laboratory value is outside the normal reference range. "
                "Please consult a qualified healthcare professional for proper evaluation."
            )
        return fallback
