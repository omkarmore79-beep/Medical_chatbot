"use client";

import Navbar from "../components/Navbar";
import Link from "next/link";
import { useRef, useState } from "react";
import ToastProvider from "../components/toast/ToastProvider";
import { useToast } from "../components/toast/useToast";

type Medicine = {
  name: string;
  dosage?: string;
  generic_name?: string;
  uses?: string;
  side_effects?: string;
  strength?: string;
  frequency?: string;
  duration?: string;
  instructions?: string;
};

type LabAnalysisItem = {
  test_name: string;
  panel: string;
  value: number;
  normal_range: string;
  status: string;
  severity: string;
  interpretation: string;
};

type UploadAnalysis = {
  document_type?: string;
  extracted_text?: string;
  analysis?: string;
  answer?: string;
  safe_flags?: Array<{ type?: string; message?: string }>;
  medicines?: Medicine[];
  lab_analysis?: LabAnalysisItem[];
  disclaimer?: string;
  structured_extraction?: {
    patient_context?: {
      age?: number | string | null;
      gender?: string | null;
    };
    vitals?: Record<string, string>;
    prescription_date?: string;
    medications?: Array<{
      name?: string;
      generic_name?: string;
      strength?: string;
      frequency?: string;
      duration?: string;
      instructions?: string;
      uses?: string;
      side_effects?: string;
    }>;
    diagnosis?: string[];
    symptoms?: string[];
    tests?: string[];
    advice_notes?: string[];
    follow_up?: string;
    patient_name?: string;
  };
  study_name?: string;
  impression?: string;
  main_finding?: string;
  abnormal_findings?: string[];
  normal_structures?: string[];
  simple_explanation?: string;
  summary?: string;
  recommended_follow_up?: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const CHAT_CONTEXT_ACTIVE_KEY = "chat_context_active";
const DOCUMENT_INSIGHT_PENDING_KEY = "document_insight_pending";

function joinLines(lines: Array<string | undefined | null>) {
  return lines.filter(Boolean).join("\n");
}

function buildExtractedText(data: UploadAnalysis) {
  if (data.extracted_text?.trim()) return data.extracted_text.trim();

  if (data.document_type === "radiology_report") {
    return joinLines([
      data.study_name ? `Study: ${data.study_name}` : "",
      data.impression ? `Impression: ${data.impression}` : "",
      data.main_finding ? `Main finding: ${data.main_finding}` : "",
      data.abnormal_findings?.length
        ? `Abnormal findings:\n${data.abnormal_findings.map((item) => `- ${item}`).join("\n")}`
        : "",
      data.normal_structures?.length
        ? `Normal structures: ${data.normal_structures.join(", ")}`
        : "",
      data.simple_explanation
        ? `Simple explanation: ${data.simple_explanation}`
        : "",
      data.summary ? `Summary: ${data.summary}` : "",
      data.recommended_follow_up
        ? `Recommended follow-up: ${data.recommended_follow_up}`
        : "",
    ]);
  }

  const structured = data.structured_extraction;
  if (structured) {
    const medications = structured.medications?.map((medicine) =>
      [
        medicine.name,
        medicine.strength,
        medicine.frequency,
        medicine.duration,
        medicine.instructions,
      ]
        .filter(Boolean)
        .join(" - ")
    );

    return joinLines([
      structured.patient_name ? `Patient: ${structured.patient_name}` : "",
      structured.patient_context?.age ? `Age: ${structured.patient_context.age}` : "",
      structured.patient_context?.gender ? `Sex: ${structured.patient_context.gender}` : "",
      structured.prescription_date ? `Prescription Date: ${structured.prescription_date}` : "",
      structured.diagnosis?.length
        ? `Diagnosis: ${structured.diagnosis.join(", ")}`
        : "",
      structured.symptoms?.length
        ? `Symptoms: ${structured.symptoms.join(", ")}`
        : "",
      structured.vitals?.blood_pressure
        ? `Blood Pressure: ${structured.vitals.blood_pressure}`
        : "",
      structured.vitals?.heart_rate
        ? `Heart Rate: ${structured.vitals.heart_rate}`
        : "",
      structured.vitals?.respiratory_rate
        ? `Respiratory Rate: ${structured.vitals.respiratory_rate}`
        : "",
      structured.vitals?.body_temperature
        ? `Body Temperature: ${structured.vitals.body_temperature}`
        : "",
      medications?.length ? `Medications:\n${medications.join("\n")}` : "",
      structured.tests?.length ? `Tests: ${structured.tests.join(", ")}` : "",
      structured.advice_notes?.length
        ? `Advice:\n${structured.advice_notes.join("\n")}`
        : "",
      structured.follow_up ? `Follow up: ${structured.follow_up}` : "",
    ]);
  }

  return joinLines([data.analysis, data.answer, data.summary]);
}

function getMedicines(data: UploadAnalysis): Medicine[] {
  if (data.medicines?.length) return data.medicines;

  return (
    data.structured_extraction?.medications?.map((medicine) => ({
      name: medicine.name || "Unknown medicine",
      generic_name: medicine.generic_name,
      uses: medicine.uses,
      side_effects: medicine.side_effects,
      strength: medicine.strength,
      frequency: medicine.frequency,
      duration: medicine.duration,
      instructions: medicine.instructions,
      dosage: [medicine.strength, medicine.frequency, medicine.duration]
        .filter(Boolean)
        .join(" - "),
    })) || []
  );
}

function getAskLabel(documentType: string) {
  if (documentType === "lab_report") return "Ask about this blood report ->";
  if (documentType === "radiology_report") return "Ask about this radiology report ->";
  if (documentType === "prescription") return "Ask about these medicines ->";
  return "Ask about this document ->";
}

function clearSavedDocumentContext() {
  localStorage.removeItem("prescription_analysis");
  localStorage.removeItem("auto_chat_prompt");
  localStorage.removeItem(CHAT_CONTEXT_ACTIVE_KEY);
  localStorage.removeItem(DOCUMENT_INSIGHT_PENDING_KEY);
}

function hasMeaningfulText(value?: string | null) {
  return Boolean(value && value.trim() && value.trim().toLowerCase() !== "unknown");
}

function isWarningOnlyText(text: string) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return true;
  return (
    /gemini quota exceeded|quota exceeded|please try again later|temporarily unavailable/.test(normalized) ||
    /could not extract|unable to extract|no readable content|not enough structured details/.test(normalized) ||
    /^warning[:\s]/.test(normalized)
  );
}

function isUnsupportedUpload(data: UploadAnalysis) {
  return (
    data.document_type === "unsupported_document" ||
    data.document_type === "non_prescription_document" ||
    Boolean(data.safe_flags?.some((flag) => flag.type === "unsupported_document"))
  );
}

function hasStructuredMedicalDetails(data: UploadAnalysis) {
  const structured = data.structured_extraction;
  if (!structured) return false;

  const hasPatient =
    hasMeaningfulText(structured.patient_name) ||
    hasMeaningfulText(`${structured.patient_context?.age ?? ""}`) ||
    hasMeaningfulText(structured.patient_context?.gender);
  const hasVitals = Boolean(
    structured.vitals && Object.values(structured.vitals).some((value) => hasMeaningfulText(value))
  );
  const hasMedication = Boolean(
    structured.medications?.some((medicine) =>
      [
        medicine.name,
        medicine.generic_name,
        medicine.strength,
        medicine.frequency,
        medicine.duration,
        medicine.instructions,
        medicine.uses,
        medicine.side_effects,
      ].some(hasMeaningfulText)
    )
  );

  return Boolean(
    hasPatient ||
      hasVitals ||
      hasMedication ||
      structured.diagnosis?.length ||
      structured.symptoms?.length ||
      structured.tests?.length ||
      structured.advice_notes?.length ||
      hasMeaningfulText(structured.prescription_date) ||
      hasMeaningfulText(structured.follow_up)
  );
}

function hasUsefulUploadData(
  data: UploadAnalysis,
  text: string,
  medicineList: Medicine[],
  labItems: LabAnalysisItem[]
) {
  if (isUnsupportedUpload(data) || isWarningOnlyText(text)) return false;

  if (data.document_type === "prescription") {
    return medicineList.length > 0 || hasStructuredMedicalDetails(data);
  }

  if (data.document_type === "lab_report") {
    return labItems.length > 0 || /\b(hemoglobin|platelet|bilirubin|sgot|sgpt|creatinine|tsh|hba1c|reference value|investigation)\b/i.test(text);
  }

  if (data.document_type === "radiology_report") {
    return Boolean(
      data.study_name ||
        data.impression ||
        data.main_finding ||
        data.summary ||
        data.abnormal_findings?.length ||
        data.normal_structures?.length
    );
  }

  return false;
}

function UploadInner() {
  const { showToast } = useToast();
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [dragOver, setDragOver] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [fileSelected, setFileSelected] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [showExtracted, setShowExtracted] = useState(false);
  const [extractedText, setExtractedText] = useState("");
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [documentType, setDocumentType] = useState("");
  const [labAnalysis, setLabAnalysis] = useState<LabAnalysisItem[]>([]);
  const [labDisclaimer, setLabDisclaimer] = useState("");
  const [analysisData, setAnalysisData] = useState<UploadAnalysis | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  function triggerUpload() {
    // Reset the input value so onChange fires even if the same file is re-selected
    if (inputRef.current) inputRef.current.value = "";
    inputRef.current?.click();
  }

  async function processFile(file: File) {
    // Reset all state for a fresh analysis
    setProcessing(true);
    setFileSelected(true);
    setShowExtracted(false);
    setExtractedText("");
    setMedicines([]);
    setDocumentType("");
    setLabAnalysis([]);
    setLabDisclaimer("");
    setAnalysisData(null);
    setApiError(null);
    clearSavedDocumentContext();

    if (file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_URL}/analyze-prescription`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        // Read the error body so the UI can show a meaningful message.
        const errorText = await res.text().catch(() => `HTTP ${res.status}`);
        throw new Error(`Server error (${res.status}): ${errorText}`);
      }

      const data: UploadAnalysis = await res.json();
      const nextExtractedText = buildExtractedText(data);
      const nextMedicines = getMedicines(data);
      const nextLabAnalysis = data.lab_analysis || [];
      const hasUsefulResult = hasUsefulUploadData(
        data,
        nextExtractedText,
        nextMedicines,
        nextLabAnalysis
      );

      setDocumentType(data.document_type || "");
      setExtractedText(nextExtractedText);
      setMedicines(nextMedicines);
      setLabAnalysis(nextLabAnalysis);
      setLabDisclaimer(data.disclaimer || "");
      setAnalysisData({
        ...data,
        extracted_text: nextExtractedText,
        medicines: nextMedicines,
        lab_analysis: nextLabAnalysis,
      });

      if (hasUsefulResult) {
        setShowExtracted(true);
        localStorage.setItem(
          "prescription_analysis",
          JSON.stringify({
            ...data,
            extracted_text: nextExtractedText,
            medicines: nextMedicines,
            lab_analysis: nextLabAnalysis,
          })
        );
        showToast("File processed successfully!", "success");
      } else {
        setShowExtracted(false);
        clearSavedDocumentContext();
        const unsupportedMessage = isUnsupportedUpload(data)
          ? "This does not look like a supported medical prescription, lab report, or radiology report."
          : "I could not read enough medical details from this upload. Please try a clearer medical document.";
        setApiError(unsupportedMessage);
        showToast("Unsupported or unreadable medical document.", "error");
      }
    } catch (error) {
      console.error("Upload error:", error);
      const message =
        error instanceof Error ? error.message : "Failed to process file.";
      setApiError(message);
      setShowExtracted(false);
      clearSavedDocumentContext();
      showToast("Failed to process prescription/report", "error");
    } finally {
      setProcessing(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  }

  function handleAskInChat(e?: React.MouseEvent<HTMLAnchorElement>) {
    const currentAnalysis = analysisData || {};
    const hasUsefulResult = hasUsefulUploadData(
      currentAnalysis,
      extractedText,
      medicines,
      labAnalysis
    );
    if (!hasUsefulResult) {
      e?.preventDefault();
      clearSavedDocumentContext();
      showToast("Please upload a supported medical document first.", "error");
      return;
    }

    const inferredDocumentType =
      documentType ||
      currentAnalysis.document_type ||
      (medicines.length > 0 ? "prescription" : "medical_document");
    const nextAnalysis = {
      ...currentAnalysis,
      document_type: inferredDocumentType,
      extracted_text: extractedText,
      medicines,
      lab_analysis: labAnalysis,
      disclaimer: labDisclaimer || currentAnalysis.disclaimer,
    };

    localStorage.setItem("prescription_analysis", JSON.stringify(nextAnalysis));

    try {
      const parsed = nextAnalysis;

      const autoPrompt =
        parsed.document_type === "lab_report"
          ? "Please explain this blood report in simple language and tell me the important findings."
          : parsed.document_type === "radiology_report"
            ? "Please explain this radiology report in simple language and tell me the important findings."
            : parsed.document_type === "prescription"
              ? "What medicines are present in this prescription?"
              : "Please explain this uploaded document in simple language.";

      localStorage.setItem("auto_chat_prompt", autoPrompt);
      localStorage.setItem(CHAT_CONTEXT_ACTIVE_KEY, "true");
      localStorage.setItem(DOCUMENT_INSIGHT_PENDING_KEY, "true");
      showToast("Context loaded in chat!", "success");
    } catch (error) {
      console.error("Failed to prepare auto chat prompt:", error);
    }
  }

  // Only open the file picker from the upload card before a file is selected.
  function handleCardClick() {
    if (!fileSelected && !processing) {
      triggerUpload();
    }
  }

  return (
    <>
      <Navbar />

      <div className="upload-page">
        <div className="upload-page-inner">
          <Link
            className="btn btn-ghost btn-sm"
            style={{ marginBottom: 24 }}
            href="/"
          >
            {"<- Back to Home"}
          </Link>

          <div className="section-label">MEDICAL DOCUMENT UPLOAD</div>
          <h1 className="upload-page-title">Upload Your Medical Document</h1>
          <p className="upload-page-sub">
            Upload a prescription, lab report, or radiology report for
            educational analysis and structured medical information.
          </p>

          <div className="upload-grid">
            {/* Left column: drop zone */}
            <div>
              <div
                className={`upload-card ${dragOver ? "drag-over" : ""} ${fileSelected ? "file-loaded" : ""}`}
                id="uploadCard"
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                onClick={handleCardClick}
                style={{
                  // Visual cue: once a file is loaded, remove the pointer cursor
                  // so the card doesn't invite re-clicking.
                  cursor: fileSelected ? "default" : "pointer",
                }}
              >
                <div className="upload-icon" aria-hidden="true">
                  <span className="upload-icon-sheet" />
                </div>
                <div className="upload-title">
                  {fileSelected
                    ? apiError
                      ? "Unsupported document"
                      : "Document loaded"
                    : "Drag & Drop your document"}
                </div>
                <div className="upload-desc">
                  {fileSelected && apiError
                    ? "Please upload a prescription, lab report, or radiology report."
                    : fileSelected
                    ? "Your document is ready. Continue to chat for the analysis."
                    : "Drop a prescription, radiology report, or lab report here, or click to browse your files."}
                </div>

                {!fileSelected && (
                  <>
                    <div className="upload-formats">
                      <span className="format-badge">JPG</span>
                      <span className="format-badge">PNG</span>
                      <span className="format-badge">PDF</span>
                    </div>

                    <div className="upload-or">- or -</div>

                    <button
                      className="btn btn-primary"
                      type="button"
                      // stopPropagation so the card's onClick doesn't also fire
                      onClick={(e) => {
                        e.stopPropagation();
                        triggerUpload();
                      }}
                    >
                      Browse Files
                    </button>
                  </>
                )}

                {/* Show a reset button after a file is loaded. */}
                {fileSelected && !processing && (
                  <button
                    className="btn btn-ghost btn-sm"
                    type="button"
                    style={{ marginTop: 16 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      // Reset everything so the user can start fresh
                      setFileSelected(false);
                      setShowExtracted(false);
                      setPreviewUrl(null);
                      setApiError(null);
                      clearSavedDocumentContext();
                      triggerUpload();
                    }}
                  >
                    Upload a different file
                  </button>
                )}

                {/* Hidden file input is always present. */}
                <input
                  ref={inputRef}
                  type="file"
                  accept=".jpg,.jpeg,.png,.pdf"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) processFile(file);
                  }}
                />
              </div>

              <div
                style={{
                  marginTop: 16,
                  padding: 16,
                  background: "var(--amber-pale)",
                  border: "1px solid #fde68a",
                  borderRadius: "var(--radius)",
                  fontSize: 13,
                  color: "#92400e",
                }}
              >
                <strong>Privacy Notice:</strong> Uploaded medical documents
                are processed during your session and are not stored. For
                educational use only.
              </div>
            </div>

            {/* Right column: preview + results */}
            <div>
              <div className="preview-card" style={{ position: "relative" }}>
                {processing && (
                  <div className="processing-overlay" id="processingOverlay">
                    <div className="processing-spinner"></div>
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: "var(--gray-600)",
                      }}
                    >
                      Extracting text with OCR...
                    </div>
                  </div>
                )}

                <div className="preview-card-title">Preview</div>

                <div className="preview-image-area" id="previewArea">
                  {previewUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={previewUrl}
                      alt="Prescription preview"
                      style={{
                        maxWidth: "100%",
                        maxHeight: "100%",
                        objectFit: "contain",
                        borderRadius: 8,
                      }}
                    />
                  ) : (
                    <div className="preview-placeholder">
                      <div style={{ fontSize: 44, marginBottom: 8 }} aria-hidden="true">
                        🖼️
                      </div>
                      <div>Preview will appear here</div>
                    </div>
                  )}
                </div>

                {/* Show a clear error panel if the analysis failed or the document is unsupported. */}
                {apiError && !processing && (
                  <div
                    style={{
                      marginTop: 16,
                      padding: 14,
                      background: "#fef2f2",
                      border: "1.5px solid #fecaca",
                      borderRadius: 10,
                      fontSize: 13,
                      color: "#b91c1c",
                      lineHeight: 1.6,
                    }}
                  >
                    <strong>Analysis not available.</strong>
                    <br />
                    <code style={{ fontSize: 12, wordBreak: "break-all" }}>
                      {apiError}
                    </code>
                    <br />
                    <span style={{ color: "#6b7280" }}>
                      Supported uploads: prescriptions, lab reports, and radiology reports.
                    </span>
                  </div>
                )}

                {showExtracted ? (
                  <div id="extractedSection">
                    <Link
                      className="btn btn-primary"
                      style={{ width: "100%", marginTop: 20 }}
                      href="/chat"
                      onClick={handleAskInChat}
                    >
                      {getAskLabel(documentType)}
                    </Link>
                  </div>
                ) : (
                  // Avoid duplicate upload controls after a file has been selected.
                  !processing && !apiError && (
                    <div
                      id="demoExtractBtn"
                      style={{ marginTop: 16, textAlign: "center" }}
                    >
                      {!fileSelected && (
                        <button
                          className="btn btn-teal btn-sm"
                          type="button"
                          onClick={triggerUpload}
                        >
                          Upload & Analyze
                        </button>
                      )}
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default function UploadPage() {
  return (
    <ToastProvider>
      <UploadInner />
    </ToastProvider>
  );
}
