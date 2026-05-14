from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import time

# Render stability change: imports are normal top-level imports again, while
# heavy model/index loading now happens lazily inside the imported modules.
from image_processor import (
    ImageOCRException,
    extract_text_from_prescription,
)
from lab_analyzer import generate_final_lab_output
from lab_report_parser import (
    extract_lab_report_metadata,
    extract_lab_values,
    interpret_lab_results,
    is_lab_report,
)
from medicine_parser import (
    extract_medicine_lines,
    resolve_medicine_line,
)
from prescription_analyzer import (
    analyze_prescription_text,
    classify_document_text,
)
from radiology_report_parser import (
    is_radiology_report,
    summarize_radiology_report,
)
from rag_engine import get_answer

# ==========================================
# FASTAPI APP
# ==========================================

app = FastAPI(
    title="Medical Chatbot (Tanmay, Parth, Omkar)",
    description="Medical AI Assistant with RAG + Prescription OCR + Smart Lab Report Analysis",
    version="5.1"
)

# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==========================================
# REQUEST MODEL
# ==========================================

class QueryIn(BaseModel):
    query: str


# ==========================================
# EMERGENCY RULES
# ==========================================

EMERGENCY_KEYWORDS = [
    "chest pain",
    "shortness of breath",
    "unconscious",
    "severe bleeding",
    "stroke",
    "heart attack",
    "seizure"
]


def check_emergency(query: str) -> bool:
    return any(word in query.lower() for word in EMERGENCY_KEYWORDS)


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Medical Chatbot API running"
    }


@app.get("/health")
def health():
    return {
        "health": "healthy"
    }


# ==========================================
# TEXT CHAT ROUTE
# ==========================================

@app.post("/ask")
def ask(payload: QueryIn):

    start_time = time.time()

    try:
        user_query = payload.query.strip()

        logging.info(f"User Query: {user_query}")

        if check_emergency(user_query):
            return {
                "answer": (
                    "Warning: Your symptoms may indicate a medical emergency.\n"
                    "Please seek immediate medical care immediately.\n\n"
                    "This AI system cannot provide emergency assistance."
                ),
                "response_time_seconds": round(time.time() - start_time, 3)
            }

        response = get_answer(user_query)

        return {
            "answer": response.get("answer", "No response generated."),
            "confidence": response.get("confidence", 0.0),
            "detected_domain": response.get("detected_domain", "unknown"),
            "response_time_seconds": round(time.time() - start_time, 3)
        }

    except Exception as e:
        logging.error(f"RAG error: {str(e)}")

        return {
            "answer": "Warning: The AI system is temporarily unavailable.",
            "response_time_seconds": round(time.time() - start_time, 3)
        }


# ==========================================
# PRESCRIPTION + LAB ROUTE
# ==========================================

@app.post("/analyze-prescription")
async def analyze_prescription(file: UploadFile = File(...)):

    start_time = time.time()

    try:
        logging.info(f"Image received: {file.filename}")

        image_bytes = await file.read()

        try:
            extracted_text = extract_text_from_prescription(
                image_bytes=image_bytes,
                mime_type=file.content_type
            )

        except ImageOCRException as e:
            return {
                "answer": f"Warning: {str(e)}",
                "response_time_seconds": round(time.time() - start_time, 3)
            }

        if not extracted_text:
            return {
                "answer": "Unable to extract readable text from image.",
                "response_time_seconds": round(time.time() - start_time, 3)
            }

        document_type = classify_document_text(extracted_text)

        # ==========================================
        # RADIOLOGY REPORT
        # ==========================================

        if (
            document_type == "radiology_report"
            and is_radiology_report(extracted_text)
        ):

            radiology_output = summarize_radiology_report(extracted_text)

            radiology_output["document_type"] = "radiology_report"
            radiology_output["extracted_text"] = extracted_text
            radiology_output["response_time_seconds"] = round(
                time.time() - start_time,
                3
            )

            return radiology_output

        # ==========================================
        # LAB REPORT
        # ==========================================

        if (
            document_type == "lab_report"
            and is_lab_report(extracted_text)
        ):

            lab_values = extract_lab_values(extracted_text)

            if not lab_values:
                return {
                    "document_type": "lab_report",
                    "analysis": "No recognizable lab values found.",
                    "extracted_text": extracted_text,
                    "response_time_seconds": round(
                        time.time() - start_time,
                        3
                    )
                }

            interpreted_results = interpret_lab_results(
                lab_values,
                include_normal=True
            )

            final_output = generate_final_lab_output(interpreted_results)

            lab_metadata = extract_lab_report_metadata(extracted_text)

            final_output["document_type"] = "lab_report"
            final_output["extracted_text"] = extracted_text

            if lab_metadata:
                final_output["lab_metadata"] = lab_metadata

            final_output["response_time_seconds"] = round(
                time.time() - start_time,
                3
            )

            return final_output

        # ==========================================
        # PRESCRIPTION PROCESSING
        # ==========================================

        medicine_lines = extract_medicine_lines(extracted_text)

        prescription_output = analyze_prescription_text(extracted_text)

        if (
            not prescription_output["structured_extraction"]["medications"]
            and medicine_lines
        ):

            recovered_medicines = []

            for line in medicine_lines:

                resolved = resolve_medicine_line(line)

                recovered_medicines.append(
                    {
                        "name": (
                            resolved.get("brand_name", "")
                            or resolved.get("generic_name", "")
                        ),
                        "strength": "",
                        "frequency": "",
                        "duration": "",
                        "instructions": "",
                    }
                )

            prescription_output["structured_extraction"]["medications"] = recovered_medicines

        prescription_output["document_type"] = "prescription"
        prescription_output["extracted_text"] = extracted_text
        prescription_output["response_time_seconds"] = round(
            time.time() - start_time,
            3
        )

        return prescription_output

    except Exception as e:

        logging.error(f"Image processing error: {str(e)}")

        return {
            "answer": "Warning: Image processing failed.",
            "response_time_seconds": round(time.time() - start_time, 3)
        }
