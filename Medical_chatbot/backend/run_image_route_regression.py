import json
import sys

from fastapi.testclient import TestClient

import main


SAMPLES = {
    "prescription_good": """Rx
Tab Dolo 650 BD x 3 days
Cap Augmentin 625 Duo TDS
Tab Pantocid DSR OD before food""",
    "prescription_ocr_noisy": """R
Tob D0lo 650 1-0-1
Cap Auginentin 625 Duo tds
Tab Montek-LC hs""",
    "lab_good": """Complete Blood Count
Hemoglobin 10.2 g/dL
WBC 12,400 /uL
Platelet Count 210000 /uL
Serum Creatinine 1.8 mg/dL""",
    "lab_table_split": """Investigation Result Unit
Hb%
9.8
g/dL
S.Creatinine
1.6
mg/dL
TSH
6.2
uIU/mL""",
    "radiology_usg": """DEPARTMENT OF RADIOLOGY
USG ABDOMEN & PELVIS
Liver - 12.48 cm, appears normal in size and echotexture. No focal lesion is seen.
A well defined round shaped hyperechoic lesion of approx size 1.54 x 1.40 cm is noted in segment VI of right lobe of liver. Findings suggestive of liver hemangioma.
Gall bladder is well distended. No evidence of calculus.
Spleen appears normal.
Both the kidneys appear normal in size, shape and echopattern.
Urinary Bladder is well distended and appears normal.
Both ovaries normal in size, shape and echotexture.
No free fluid is noted in the abdomen and pelvic region.
IMPRESSION:
Small liver hemangioma in the right lobe of liver (Segment VI).""",
}


def main_run() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    client = TestClient(main.app)

    for name, text in SAMPLES.items():
        main.extract_text_from_prescription = lambda image_bytes, mime_type, text=text: text
        response = client.post(
            "/analyze-prescription",
            files={"file": ("sample.png", b"fake", "image/png")},
        )
        print("=" * 80)
        print(name, response.status_code)
        print(json.dumps(response.json(), indent=2)[:2500])


if __name__ == "__main__":
    main_run()
