from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import time

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
# LAZY LOADED MODULE VARIABLES
# ==========================================

get_answer = None

extract_text_from_prescription = None
ImageOCRException = None

extract_medicine_lines = None
resolve_medicine_line = None

analyze_prescription_text = None
classify_document_text = None

is_lab_report = None
extract_lab_values = None
interpret_lab_results = None
extract_lab_report_metadata = None

is_radiology_report = None
summarize_radiology_report = None

generate_final_lab_output = None

# ==========================================
# STARTUP EVENT
# ==========================================

@app.on_event("startup")
async def startup_event():

    global get_answer

    global extract_text_from_prescription
    global ImageOCRException

    global extract_medicine_lines
    global resolve_medicine_line

    global analyze_prescription_text
    global classify_document_text

    global is_lab_report
    global extract_lab_values
    global interpret_lab_results
    global extract_lab_report_metadata

    global is_radiology_report
    global summarize_radiology_report

    global generate_final_lab_output

    try:
        logging.info("Loading AI modules...")

        from rag_engine import get_answer as rag_get_answer

        from image_processor import (
            extract_text_from_prescription as ocr_extract,
            ImageOCRException as OCRException
        )

        from medicine_parser import (
            extract_medicine_lines as med_lines,
            resolve_medicine_line as med_resolve
        )

        from prescription_analyzer import (
            analyze_prescription_text as prescription_analyze,
            classify_document_text as classify_doc
        )

        from lab_report_parser import (
            is_lab_report as check_lab,
            extract_lab_values as extract_labs,
            interpret_lab_results as interpret_labs,
            extract_lab_report_metadata as extract_metadata
        )

        from radiology_report_parser import (
            is_radiology_report as check_radiology,
            summarize_radiology_report as summarize_radio
        )

        from lab_analyzer import (
            generate_final_lab_output as final_lab_output
        )

        # ASSIGN TO GLOBALS
        get_answer = rag_get_answer

        extract_text_from_prescription = ocr_extract
        ImageOCRException = OCRException

        extract_medicine_lines = med_lines
        resolve_medicine_line = med_resolve

        analyze_prescription_text = prescription_analyze
        classify_document_text = classify_doc

        is_lab_report = check_lab
        extract_lab_values = extract_labs
        interpret_lab_results = interpret_labs
        extract_lab_report_metadata = extract_metadata

        is_radiology_report = check_radiology
        summarize_radiology_report = summarize_radio

        generate_final_lab_output = final_lab_output

        logging.info("All AI modules loaded successfully.")

    except Exception as e:
        logging.error(f"Startup loading failed: {str(e)}")


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

    if get_answer is None:
        return {
            "answer": "AI modules are still loading. Please wait."
        }

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

    if extract_text_from_prescription is None:
        return {
            "answer": "OCR system still loading."
        }

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