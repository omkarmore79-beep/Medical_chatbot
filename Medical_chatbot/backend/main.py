from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_engine import get_answer
from image_processor import extract_text_from_prescription, ImageOCRException
import logging
import time

from medicine_parser import (
    extract_medicine_lines,
    resolve_medicine_line
)
from prescription_analyzer import analyze_prescription_text
from prescription_analyzer import classify_document_text

from lab_report_parser import (
    is_lab_report,
    extract_lab_values,
    interpret_lab_results,
    extract_lab_report_metadata
)
from radiology_report_parser import (
    is_radiology_report,
    summarize_radiology_report
)

from lab_analyzer import generate_final_lab_output


# -----------------------------
# Create API server
# -----------------------------

app = FastAPI(
    title="Medical Chatbot (Tanmay, Parth, Omkar)",
    description="Medical AI Assistant with RAG + Prescription OCR + Smart Lab Report Analysis",
    version="5.1"
)

# -----------------------------
# CORS Middleware
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Configure Logging
# -----------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# -----------------------------
# Emergency Rules (TEXT)
# -----------------------------

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


# -----------------------------
# Prescription Risk Keywords
# -----------------------------

PRESCRIPTION_ALERT_KEYWORDS = [
    "nitroglycerin",
    "adrenaline",
    "epinephrine",
    "morphine",
    "dopamine",
    "dobutamine"
]


def check_prescription_alert(extracted_text: str) -> bool:
    return any(word in extracted_text.lower() for word in PRESCRIPTION_ALERT_KEYWORDS)


def _needs_medicine_analysis_fallback(text: str) -> bool:
    lower_text = text.lower()
    return (
        "retrieved information was broad" in lower_text
        or lower_text.startswith("boxed warning:")
        or lower_text.startswith("key precautions:")
        or lower_text.startswith("warnings:")
    )


# -----------------------------
# Request Body Model
# -----------------------------

class QueryIn(BaseModel):
    query: str


# -----------------------------
# Health Check Route
# -----------------------------

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Medical Chatbot API running (Text + Prescription + Lab Analyzer)"
    }


# -----------------------------
# TEXT CHAT ROUTE
# -----------------------------

@app.post("/ask")
def ask(payload: QueryIn):

    start_time = time.time()
    user_query = payload.query.strip()

    logging.info(f"User Query: {user_query}")

    if check_emergency(user_query):
        logging.warning("Emergency case detected (text)")
        return {
            "answer": (
                "Warning: Your symptoms may indicate a medical emergency.\n"
                "Please seek immediate medical care immediately.\n\n"
                "This AI system cannot provide emergency assistance."
            ),
            "response_time_seconds": round(time.time() - start_time, 3)
        }

    try:
        response = get_answer(user_query)
    except Exception as e:
        logging.error(f"RAG error: {str(e)}")
        return {
            "answer": "Warning: The AI system is temporarily unavailable. Please try again shortly.",
            "response_time_seconds": round(time.time() - start_time, 3)
        }

    return {
        "answer": response.get("answer", "No response generated."),
        "confidence": response.get("confidence", 0.0),
        "detected_domain": response.get("detected_domain", "unknown"),
        "response_time_seconds": round(time.time() - start_time, 3)
    }


# -----------------------------
# PRESCRIPTION + LAB IMAGE ROUTE
# -----------------------------

@app.post("/analyze-prescription")
async def analyze_prescription(file: UploadFile = File(...)):

    start_time = time.time()
    logging.info(f"Image received: {file.filename}")

    try:
        image_bytes = await file.read()
        mime_type = file.content_type

        try:
            extracted_text = extract_text_from_prescription(
                image_bytes=image_bytes,
                mime_type=mime_type
            )
        except ImageOCRException as e:
            return {
                "answer": f"Warning: {str(e)}",
                "response_time_seconds": round(time.time() - start_time, 3)
            }

        if not extracted_text:
            return {
                "answer": "Warning: Unable to extract readable text from the image.",
                "response_time_seconds": round(time.time() - start_time, 3)
            }

        document_type = classify_document_text(extracted_text)

        if document_type == "non_prescription_document":
            unsupported_output = analyze_prescription_text(extracted_text)
            unsupported_output["document_type"] = "unsupported_document"
            unsupported_output["extracted_text"] = extracted_text
            unsupported_output["response_time_seconds"] = round(time.time() - start_time, 3)
            return unsupported_output

        # =====================================================
        # STEP 1 - DOCUMENT ROUTING
        # =====================================================

        if document_type == "radiology_report" and is_radiology_report(extracted_text):
            radiology_output = summarize_radiology_report(extracted_text)
            radiology_output["document_type"] = "radiology_report"
            radiology_output["extracted_text"] = extracted_text
            radiology_output["response_time_seconds"] = round(time.time() - start_time, 3)
            return radiology_output

        if document_type == "lab_report" and is_lab_report(extracted_text):
            lab_values = extract_lab_values(extracted_text)

            if not lab_values:
                return {
                    "document_type": "lab_report",
                    "extracted_text": extracted_text,
                    "analysis": "No recognizable lab values found.",
                    "disclaimer": "Warning: Please consult your doctor for proper medical interpretation.",
                    "response_time_seconds": round(time.time() - start_time, 3)
                }

            interpreted_results = interpret_lab_results(lab_values, include_normal=True)

            final_output = generate_final_lab_output(interpreted_results)
            lab_metadata = extract_lab_report_metadata(extracted_text)

            final_output["document_type"] = "lab_report"
            final_output["extracted_text"] = extracted_text
            if lab_metadata:
                final_output["lab_metadata"] = lab_metadata
                final_output["structured_extraction"] = {
                    "patient_name": lab_metadata.get("patient_name", ""),
                    "patient_context": {
                        "age": lab_metadata.get("age", ""),
                        "gender": lab_metadata.get("gender", ""),
                    },
                    "tests": [lab_metadata.get("report_title", "")] if lab_metadata.get("report_title") else [],
                    "advice_notes": [lab_metadata.get("report_interpretation", "")] if lab_metadata.get("report_interpretation") else [],
                }
            final_output["response_time_seconds"] = round(time.time() - start_time, 3)

            return final_output

        # =====================================================
        # STEP 2 - PRESCRIPTION PROCESSING
        # =====================================================

        medicine_lines = extract_medicine_lines(extracted_text)
        prescription_output = analyze_prescription_text(extracted_text)

        if not prescription_output["structured_extraction"]["medications"] and medicine_lines:
            recovered_medicines = []
            for line in medicine_lines:
                resolved = resolve_medicine_line(line)
                recovered_medicines.append(
                    {
                        "name": resolved.get("brand_name", "") or resolved.get("generic_name", ""),
                        "strength": "",
                        "frequency": "",
                        "duration": "",
                        "instructions": "",
                    }
                )
            prescription_output["structured_extraction"]["medications"] = recovered_medicines

        prescription_output["document_type"] = "prescription"
        prescription_output["extracted_text"] = extracted_text
        prescription_output["response_time_seconds"] = round(time.time() - start_time, 3)
        return prescription_output

    except Exception as e:
        logging.error(f"Image processing error: {str(e)}")

        return {
            "answer": "Warning: Image processing failed. Please try again.",
            "response_time_seconds": round(time.time() - start_time, 3)
        }
