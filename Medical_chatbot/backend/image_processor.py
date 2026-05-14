from google import genai
from google.genai import types
import os
import time
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


class ImageOCRException(Exception):
    pass


def _classify_vision_error(error: Exception) -> str:
    message = str(error).lower()
    if "503" in message or "unavailable" in message or "high demand" in message:
        return "The image OCR service is temporarily busy. Please try again."
    if "429" in message or "resource_exhausted" in message or "quota" in message or "rate limit" in message:
        return "Gemini quota exceeded. Please try again later."
    if "401" in message or "403" in message or "api key" in message or "permission" in message or "unauthorized" in message:
        return "Invalid Gemini API key or permission denied."
    if "mime" in message or "unsupported" in message or "invalid_argument" in message or "400" in message:
        return "Unsupported image type or invalid image input."
    return "Image OCR failed due to an upstream AI service error."


def _is_retryable_vision_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        signal in message
        for signal in ["503", "unavailable", "high demand", "deadline", "timeout"]
    )


def extract_text_from_prescription(image_bytes: bytes, mime_type: str) -> str:
    """
    Extract text from medical image using Gemini Vision.
    """

    prompt = """
You are a medical OCR system.
Extract all readable medical text.
Keep table rows intact and preserve line breaks.
Do not summarize, correct, or infer values.
Return only plain extracted text.
"""

    models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    last_error: Exception | None = None

    for model in models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type
                        )
                    ],
                )

                if response.text:
                    return response.text.strip()

                raise ImageOCRException("No readable text was returned by the OCR model.")

            except Exception as e:
                print("Vision error:", e)
                if isinstance(e, ImageOCRException):
                    raise
                last_error = e
                if not _is_retryable_vision_error(e):
                    raise ImageOCRException(_classify_vision_error(e)) from e
                if attempt == 0:
                    time.sleep(1.2)

    if last_error:
        raise ImageOCRException(_classify_vision_error(last_error)) from last_error

    raise ImageOCRException("No readable text was returned by the OCR model.")
