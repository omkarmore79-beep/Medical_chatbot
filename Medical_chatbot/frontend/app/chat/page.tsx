"use client";

import Link from "next/link";
import { useEffect, useEffectEvent, useRef, useState } from "react";

type Msg = {
  role: "user" | "ai";
  text: string;
  sources?: string[];
  time: string;
};

type StoredMedicine = {
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

type PrescriptionAnalysisItem = {
  original_line?: string;
  brand_name?: string;
  generic_name?: string;
  display_name?: string;
  analysis?: string;
  confidence?: number;
  uses?: string;
  side_effects?: string;
  strength?: string;
  frequency?: string;
  duration?: string;
  instructions?: string;
};

type StoredAnalysis = {
  document_type?: string;
  extracted_text?: string;
  analysis?: string;
  answer?: string;
  summary?: string;
  study_name?: string;
  impression?: string;
  main_finding?: string;
  abnormal_findings?: string[];
  normal_structures?: string[];
  simple_explanation?: string;
  recommended_follow_up?: string;
  message?: string;
  lab_metadata?: {
    patient_name?: string;
    age?: string;
    gender?: string;
    report_title?: string;
    report_interpretation?: string;
  };
  medicines?: StoredMedicine[];
  medicines_detected?: string[];
  detailed_analysis?: PrescriptionAnalysisItem[];
  lab_analysis?: LabAnalysisItem[];
  structured_extraction?: {
    patient_name?: string;
    patient_context?: {
      age?: number | string | null;
      gender?: string | null;
    };
    vitals?: Record<string, string>;
    prescription_date?: string;
    diagnosis?: string[];
    symptoms?: string[];
    tests?: string[];
    advice_notes?: string[];
    follow_up?: string;
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
  };
  disclaimer?: string;
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

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const CHAT_CONTEXT_ACTIVE_KEY = "chat_context_active";
const DOCUMENT_INSIGHT_PENDING_KEY = "document_insight_pending";
const LAB_TEST_LABELS: Record<string, string[]> = {
  SGOT: ["ast", "sgot", "ast sgot"],
  SGPT: ["alt", "sgpt", "alt sgpt"],
  AST_ALT_RATIO: ["ast alt ratio", "ast:alt ratio", "ast : alt ratio"],
  A_G_RATIO: ["a/g ratio", "ag ratio", "a g ratio"],
  GGT: ["ggt", "ggtp"],
  ALP: ["alp", "alkaline phosphatase"],
  TOTAL_BILIRUBIN: ["total bilirubin", "bilirubin total"],
  DIRECT_BILIRUBIN: ["direct bilirubin", "bilirubin direct"],
  INDIRECT_BILIRUBIN: ["indirect bilirubin", "bilirubin indirect"],
  TOTAL_PROTEIN: ["total protein"],
  ALBUMIN: ["albumin"],
  GLOBULIN: ["globulin"],
};

function getCurrentTime() {
  return new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getDocumentLabel(documentType?: string) {
  if (documentType === "prescription") return "Prescription";
  if (documentType === "lab_report") return "Lab report";
  if (documentType === "radiology_report") return "Radiology report";
  return "Document";
}

function buildContextualQuery(question: string, stored: StoredAnalysis) {
  const context = [
    stored.extracted_text,
    stored.summary,
    stored.impression,
    stored.main_finding,
    stored.simple_explanation,
  ]
    .filter(Boolean)
    .join("\n\n");

  if (!context.trim()) return question;

  return [
    `Uploaded ${getDocumentLabel(stored.document_type).toLowerCase()} text/context:`,
    context,
    "",
    "User question:",
    question,
    "",
    "Please answer using the uploaded document context where relevant. Keep it educational and advise consulting a doctor for medical decisions.",
  ].join("\n");
}

function htmlToPlainText(value: string) {
  return value
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function stripMarkdown(value: string) {
  return value
    .replace(/\*\*/g, "")
    .replace(/^\s*[*]\s+/gm, "- ")
    .replace(/\r/g, "")
    .trim();
}

function isLikelyFollowUp(question: string, history: Msg[]) {
  const hasPreviousUserSymptom = history.some(
    (message) =>
      message.role === "user" &&
      /\b(fever|headache|cough|pain|stomach|abdominal|weak|weakness|sore|vomit|vomiting|nausea|rash|diarrhea|loose stools|muscle|body|burning urination|urination)\b/i.test(
        message.text
      )
  );

  if (!hasPreviousUserSymptom) return false;

  const trimmed = question.trim();
  return (
    /^(yes|no|also|and|i also|i feel|i have|i am|i'm|my|it|same|weak|muscle|body|headache|fever|experiencing|from|since|for|past)\b/i.test(
      trimmed
    ) || /\b(day|days|hour|hours|week|weeks|month|months|since|past)\b/i.test(trimmed)
  );
}

function buildRecentConversationQuery(question: string, history: Msg[]) {
  if (!isLikelyFollowUp(question, history)) return question;

  const previousUserMessages = history
    .filter((message) => message.role === "user")
    .slice(-3)
    .map((message) => `- ${htmlToPlainText(message.text)}`);

  if (!previousUserMessages.length) return question;

  return [
    "Previous user symptom context:",
    ...previousUserMessages,
    "",
    "Current user follow-up:",
    question,
    "",
    "Answer by combining the previous symptom context with the current follow-up. Do not treat the current follow-up as a completely new case.",
  ].join("\n");
}

function getSection(text: string, label: string, nextLabels: string[]) {
  const start = text.indexOf(label);
  if (start === -1) return "";

  const afterLabel = start + label.length;
  const nextIndexes = nextLabels
    .map((nextLabel) => text.indexOf(nextLabel, afterLabel))
    .filter((index) => index !== -1);
  const end = nextIndexes.length ? Math.min(...nextIndexes) : text.length;
  return text.slice(afterLabel, end).trim();
}

function cleanListLine(line: string) {
  return line.replace(/^\s*[-*]\s*/, "").replace(/^\s*\d+[.)]\s*/, "").trim();
}

function capitalizeSentence(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
}

function toTitleCase(value: string) {
  return value
    .trim()
    .split(/\s+/)
    .map((word) => {
      const lower = word.toLowerCase();
      if (["UTI", "GERD", "COVID", "CFS"].includes(word.toUpperCase())) {
        return word.toUpperCase();
      }
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

function getConditionIcon(conditionName: string) {
  const name = conditionName.toLowerCase();
  if (name.includes("typhoid") || name.includes("infection")) return "🦠";
  if (name.includes("gerd") || name.includes("reflux") || name.includes("acidity")) return "🔥";
  if (name.includes("allerg")) return "⚡";
  if (name.includes("jaundice") || name.includes("liver")) return "🟡";
  if (name.includes("uti") || name.includes("urinary")) return "💧";
  if (name.includes("malaria") || name.includes("fever")) return "🌡️";
  if (name.includes("chicken") || name.includes("rash") || name.includes("skin")) return "🔴";
  if (name.includes("diabetes") || name.includes("sugar")) return "🩸";
  if (name.includes("thyroid") || name.includes("hyperthyroid")) return "⚕️";
  return "📌";
}

function formatDefaultAnswer(rawAnswer: string) {
  const cleaned = stripMarkdown(rawAnswer);
  const lines = cleaned.split("\n").map((line) => line.trim()).filter(Boolean);
  const intro: string[] = [];
  const sections: Array<{ title: string; items: string[] }> = [];
  let currentSection: { title: string; items: string[] } | null = null;

  for (const line of lines) {
    const headingMatch = line.match(/^([A-Za-z][A-Za-z\s/()-]{2,45}):$/);
    if (headingMatch) {
      currentSection = { title: headingMatch[1], items: [] };
      sections.push(currentSection);
      continue;
    }

    if (/^[-]\s+/.test(line)) {
      const item = capitalizeSentence(line.replace(/^[-]\s+/, ""));
      if (!currentSection) {
        currentSection = { title: "Key Points", items: [] };
        sections.push(currentSection);
      }
      currentSection.items.push(item);
      continue;
    }

    if (currentSection) {
      currentSection.items.push(capitalizeSentence(line));
    } else {
      intro.push(capitalizeSentence(line));
    }
  }

  const visibleSections = sections
    .map((section) => ({
      ...section,
      items: section.items.filter(Boolean),
    }))
    .filter((section) => section.items.length);

  if (!intro.length && !visibleSections.length) {
    return `<p>${escapeHtml(capitalizeSentence(cleaned))}</p>`;
  }

  return `
    <div class="general-answer">
      <div class="general-answer-header">
        <span class="general-answer-icon">💡</span>
        <span>Answer</span>
      </div>
      ${intro.map((line) => `<p class="general-summary">${escapeHtml(line)}</p>`).join("")}
      ${
        visibleSections.length
          ? `<div class="general-section-grid">${visibleSections
              .slice(0, 4)
              .map(
                (section) => `
                  <div class="general-section-card">
                    <div class="general-section-title">${escapeHtml(
                      section.title.toLowerCase() === "key points"
                        ? "At a Glance"
                        : toTitleCase(section.title)
                    )}</div>
                    <div class="general-point-list">
                      ${section.items
                        .slice(0, 5)
                        .map(
                          (item, index) => `
                            <div class="general-point-row">
                              <span class="general-point-number">${index + 1}</span>
                              <span>${escapeHtml(item)}</span>
                            </div>
                          `
                        )
                        .join("")}
                    </div>
                  </div>
                `
              )
              .join("")}</div>`
          : ""
      }
    </div>
  `;
}

function formatDrugInteractionAnswer(rawAnswer: string) {
  const cleaned = stripMarkdown(rawAnswer).replace(/\s+/g, " ").trim();
  const exactMatch = cleaned.match(
    /^Yes,\s+(.+?)\s+interacts with\s+(.+?)\.\s+Severity:\s+(.+?)\.\s+Details:\s+(.+)$/i
  );
  const generalMatch = cleaned.match(/^(.+?)\s+have a\s+(.+?)\s+drug interaction\.\s*(.*)$/i);
  const noConfirmMatch = cleaned.match(
    /^I cannot confidently confirm a direct interaction between\s+(.+?)\s+and\s+(.+?)\s+from the available information\.\s*(.*)$/i
  );

  const makeNote = (text: string) =>
    `<div class="safety-note"><span class="safety-note-icon">⚠️</span><span>${escapeHtml(text)}</span></div>`;

  if (exactMatch) {
    const [, drugA, drugB, severity, details] = exactMatch;
    const normalizedSeverity = toTitleCase(severity);
    const caution =
      /warfarin|anticoagulant|blood thinner|bleeding/i.test(`${drugA} ${drugB} ${details}`)
        ? "This combination can be clinically important. Ask a doctor or pharmacist and follow any monitoring advice."
        : "Do not stop or change prescribed medicines yourself. Ask a doctor or pharmacist if you are taking them together.";

    return `
      <div class="general-answer">
        <div class="general-answer-header">
          <span class="general-answer-icon">💊</span>
          <span>Drug Interaction</span>
        </div>
        <p class="general-summary">Interaction found between <strong>${escapeHtml(drugA)}</strong> and <strong>${escapeHtml(drugB)}</strong>.</p>
        <div class="general-section-grid">
          <div class="general-section-card">
            <div class="general-section-title">At a Glance</div>
            <div class="general-point-list">
              <div class="general-point-row"><span class="general-point-number">1</span><span><strong>Medicines:</strong> ${escapeHtml(drugA)} + ${escapeHtml(drugB)}</span></div>
              <div class="general-point-row"><span class="general-point-number">2</span><span><strong>Severity:</strong> ${escapeHtml(normalizedSeverity)}</span></div>
              <div class="general-point-row"><span class="general-point-number">3</span><span><strong>Meaning:</strong> ${escapeHtml(capitalizeSentence(details))}</span></div>
            </div>
          </div>
        </div>
        ${makeNote(caution)}
      </div>
    `;
  }

  if (generalMatch) {
    const [, pairText, severity, details] = generalMatch;
    const normalizedSeverity = toTitleCase(severity);
    const caution = /warfarin|anticoagulant|blood thinner|bleeding/i.test(`${pairText} ${details}`)
      ? "Warfarin interactions can be clinically important. Ask a doctor or pharmacist before combining these medicines."
      : "Ask a doctor or pharmacist before combining medicines, especially if they were not prescribed together.";
    return `
      <div class="general-answer">
        <div class="general-answer-header">
          <span class="general-answer-icon">💊</span>
          <span>Drug Interaction</span>
        </div>
        <p class="general-summary">Interaction information found for ${escapeHtml(pairText)}.</p>
        <div class="general-section-card">
          <div class="general-section-title">At a Glance</div>
          <div class="general-point-list">
            <div class="general-point-row"><span class="general-point-number">1</span><span><strong>Severity:</strong> ${escapeHtml(normalizedSeverity)}</span></div>
            ${details ? `<div class="general-point-row"><span class="general-point-number">2</span><span><strong>Meaning:</strong> ${escapeHtml(capitalizeSentence(details))}</span></div>` : ""}
          </div>
        </div>
        ${makeNote(caution)}
      </div>
    `;
  }

  if (noConfirmMatch) {
    const [, drugA, drugB, advice] = noConfirmMatch;
    return `
      <div class="general-answer">
        <div class="general-answer-header">
          <span class="general-answer-icon">💊</span>
          <span>Drug Interaction</span>
        </div>
        <p class="general-summary">I cannot confidently confirm a direct interaction between <strong>${escapeHtml(drugA)}</strong> and <strong>${escapeHtml(drugB)}</strong> from the available information.</p>
        ${makeNote(capitalizeSentence(advice || "That does not mean the combination is safe. Please confirm with your doctor or pharmacist."))}
      </div>
    `;
  }

  return "";
}

function formatSymptomAnswer(rawAnswer: string) {
  const cleaned = stripMarkdown(rawAnswer);
  const summary = getSection(cleaned, "SUMMARY:", [
    "POSSIBLE_CONDITIONS:",
    "FOLLOW_UP_QUESTIONS:",
    "SAFETY_NOTE:",
  ]);
  const conditionsText = getSection(cleaned, "POSSIBLE_CONDITIONS:", [
    "FOLLOW_UP_QUESTIONS:",
    "SAFETY_NOTE:",
  ]);
  const questionsText = getSection(cleaned, "FOLLOW_UP_QUESTIONS:", ["SAFETY_NOTE:"]);
  const safetyNote = getSection(cleaned, "SAFETY_NOTE:", []);

  const conditionCards = conditionsText
    .split("\n")
    .map(cleanListLine)
    .filter(Boolean)
    .slice(0, 4)
    .map((line) => {
      const [rawTitle, ...reasonParts] = line.includes("|")
        ? line.split("|")
        : line.split(/:\s+/);
      const title = toTitleCase(rawTitle || "Possible condition");
      const reason = capitalizeSentence(
        reasonParts.join(": ").trim() || "May be related to the symptoms described."
      );
      return `
        <div class="symptom-card">
          <div class="symptom-card-heading">
            <span class="symptom-card-icon">${getConditionIcon(title)}</span>
            <span class="symptom-card-title">${escapeHtml(title)}</span>
          </div>
          <div class="symptom-card-text">${escapeHtml(reason)}</div>
        </div>
      `;
    });

  const questionItems = questionsText
    .split("\n")
    .map(cleanListLine)
    .filter(Boolean)
    .slice(0, 5)
    .map(
      (question, index) => `
        <div class="follow-question">
          <span class="follow-number">${index + 1}</span>
          <span>${escapeHtml(capitalizeSentence(question))}</span>
        </div>
      `
    );

  if (!summary && !conditionCards.length && !questionItems.length) {
    return formatDefaultAnswer(cleaned);
  }

  return `
    <div class="structured-answer">
      ${summary ? `<p class="structured-summary">${escapeHtml(capitalizeSentence(summary))}</p>` : ""}
      ${
        conditionCards.length
          ? `<div class="structured-label">Possible Conditions</div><div class="symptom-card-grid">${conditionCards.join("")}</div>`
          : ""
      }
      ${
        questionItems.length
          ? `<div class="structured-divider"></div><div class="structured-label">Follow-up Questions to Better Understand Your Situation</div><div class="follow-question-list">${questionItems.join("")}</div>`
          : ""
      }
      <div class="safety-note"><span class="safety-note-icon">⚠️</span><span>${escapeHtml(
        capitalizeSentence(
          safetyNote ||
          "This is educational information only. Please consult a qualified doctor for diagnosis or treatment. Do not use this for emergencies."
        )
      )}</span></div>
    </div>
  `;
}

function formatAiAnswer(rawAnswer: string, detectedDomain?: string) {
  const interactionAnswer = formatDrugInteractionAnswer(rawAnswer);
  if (interactionAnswer) return interactionAnswer;
  if (detectedDomain === "symptoms") {
    return formatSymptomAnswer(rawAnswer);
  }
  return formatDefaultAnswer(rawAnswer);
}

const initialAiMessage: Msg = {
  role: "ai",
  text: `
    <p>Hello! I'm <strong>MedInsight AI</strong>, your academic medical information assistant.</p>
    <p>I can help you with:</p>
    <ul>
      <li>- Understanding symptoms in simple language.</li>
      <li>- Medicine information and basic precautions.</li>
      <li>- Explaining prescription medicines.</li>
      <li>- Interpreting clinical lab reports.</li>
      <li>- Analyzing radiology report text.</li>
    </ul>
    <p style="margin-top: 8px; font-size: 13px; color: #6b7280;">Warning: This is for educational use only and is not a substitute for a doctor or emergency care.</p>
  `,
  time: "",
};

function getInitialMessages(): Msg[] {
  return [initialAiMessage];
}

function hasPrescriptionContext(stored: StoredAnalysis) {
  return (
    stored.document_type === "prescription" ||
    Boolean(stored.medicines?.length) ||
    Boolean(stored.medicines_detected?.length) ||
    Boolean(stored.detailed_analysis?.length) ||
    /\b(medications?|prescription|dose|frequency|duration|tablet|capsule|syrup)\b/i.test(
      stored.extracted_text || ""
    )
  );
}

function extractTextField(text: string, label: string) {
  const match = text.match(new RegExp(`^${label}:\\s*(.+)$`, "im"));
  return match?.[1]?.trim() || "";
}

function looksLikeAddressOrClinicLine(value: string) {
  return /\b(road|rd\.?|street|st\.?|center|centre|business center|mg road|pune|nantes|france|hospital|clinic|closed|timing|reg\.?\s*no|mob\.?\s*no|phone|ph:|address)\b/i.test(
    value
  ) || /\b\d{5,6}\b/.test(value);
}

function looksLikeComplaintOrHeading(value: string) {
  return /\b(headache|fever|chills|cough|pain|vomiting|nausea|days?|chief complaints?|clinical findings?|diagnosis|prescription|medicine name|dosage|duration)\b/i.test(
    value
  );
}

function sanitizePatientName(value: string) {
  const cleaned = value.trim().replace(/^[*\-\s]+/, "").replace(/\s+/g, " ");
  if (!cleaned) return "";
  if (looksLikeAddressOrClinicLine(cleaned) || looksLikeComplaintOrHeading(cleaned)) return "";
  if (/\b(patient|opd|id:|mob\.?|date:|age|sex)\b/i.test(cleaned)) return "";
  const words = cleaned.split(/\s+/);
  if (words.length < 2 || words.length > 5) return "";
  return cleaned;
}

function sanitizeFollowUp(value: string) {
  const cleaned = value.trim();
  if (!cleaned || looksLikeAddressOrClinicLine(cleaned)) return "";
  const dateMatch = cleaned.match(/\b\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b[A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}\b/);
  return dateMatch?.[0] || cleaned;
}

function sanitizeAdviceItems(items: string[]) {
  return items.filter(
    (item) =>
      !looksLikeAddressOrClinicLine(item) &&
      !/substitute with equivalent|generics as required/i.test(item)
  );
}

function extractListField(text: string, label: string) {
  const value = extractTextField(text, label);
  if (!value) return [];
  return value.split(/,\s*/).map((item) => item.trim()).filter(Boolean);
}

function extractSectionLines(text: string, label: string) {
  const labels = [
    "Patient",
    "Diagnosis",
    "Symptoms",
    "Medications",
    "Tests",
    "Advice",
    "Follow up",
    "Follow-up",
    "Vitals",
  ];
  const lines = text.split(/\r?\n/);
  const start = lines.findIndex((line) => line.trim().toLowerCase() === `${label.toLowerCase()}:`);
  if (start === -1) return [];

  const sectionLines: string[] = [];
  for (const line of lines.slice(start + 1)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (labels.some((nextLabel) => trimmed.toLowerCase() === `${nextLabel.toLowerCase()}:`)) break;
    sectionLines.push(trimmed);
  }
  return sectionLines;
}

function parseMedicineLine(line: string): StoredMedicine {
  const parts = line.split(/\s+-\s+/).map((part) => part.trim()).filter(Boolean);
  return {
    name: parts[0] || line,
    strength: parts[1],
    frequency: parts[2],
    duration: parts[3],
    instructions: parts.slice(4).join(" - "),
    dosage: parts.slice(1).join(" - "),
  };
}

function hasUsefulDocumentDetails(stored: StoredAnalysis) {
  const text = stored.extracted_text || "";
  return (
    Boolean(stored.structured_extraction) ||
    Boolean(stored.medicines?.length) ||
    Boolean(stored.lab_analysis?.length) ||
    /\b(patient|age|sex|diagnosis|symptoms|medications|blood pressure|heart rate|advice|follow up)\b/i.test(
      text
    )
  );
}

function getStoredMedicines(stored: StoredAnalysis) {
  if (stored.medicines?.length) return stored.medicines;
  if (stored.structured_extraction?.medications?.length) {
    return stored.structured_extraction.medications.map((medicine) => ({
      name: medicine.name || "Unknown medicine",
      generic_name: medicine.generic_name,
      strength: medicine.strength,
      frequency: medicine.frequency,
      duration: medicine.duration,
      instructions: medicine.instructions,
      uses: medicine.uses,
      side_effects: medicine.side_effects,
      dosage: [medicine.strength, medicine.frequency, medicine.duration].filter(Boolean).join(" - "),
    }));
  }
  return extractSectionLines(stored.extracted_text || "", "Medications").map(parseMedicineLine);
}

function getStoredVitals(stored: StoredAnalysis) {
  const vitals = stored.structured_extraction?.vitals || {};
  const text = stored.extracted_text || "";
  return {
    blood_pressure: vitals.blood_pressure || extractTextField(text, "Blood Pressure"),
    heart_rate: vitals.heart_rate || extractTextField(text, "Heart Rate"),
    respiratory_rate: vitals.respiratory_rate || extractTextField(text, "Respiratory Rate"),
    body_temperature: vitals.body_temperature || extractTextField(text, "Body Temperature"),
  };
}

function formatLabTestName(name: string) {
  return name.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function getLabStatusStyle(status: string) {
  const normalized = status.toUpperCase();
  if (normalized === "NORMAL") return "background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;";
  if (normalized === "HIGH") return "background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;";
  if (normalized === "LOW") return "background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;";
  if (normalized === "BORDERLINE") return "background:#fffbeb;color:#b45309;border:1px solid #fde68a;";
  return "background:#f8fafc;color:#475569;border:1px solid #e2e8f0;";
}

function getLabAttentionItems(items: LabAnalysisItem[]) {
  return items.filter((item) => item.status !== "NORMAL");
}

function cleanMedicalDisclaimer(value?: string) {
  const fallback = "Please review lab reports with a qualified healthcare provider.";
  return (value || fallback).replace(/^\s*⚠️?\s*/, "").trim();
}

function buildLabAttentionSummary(items: LabAnalysisItem[]) {
  const attentionItems = getLabAttentionItems(items);
  if (!attentionItems.length) return "All detected values are within the supported reference ranges.";
  return `${attentionItems.length} value(s) need attention: ${attentionItems
    .map((item) => `${formatLabTestName(item.test_name)} ${item.status.toLowerCase()}`)
    .join(", ")}.`;
}

function buildLabResultsTable(items: LabAnalysisItem[]) {
  if (!items.length) return "";
  return `
    <div class="document-insight-section">
      <div class="document-insight-label">Lab Results</div>
      <div class="document-medicine-table">
        <div class="document-medicine-head">Test</div>
        <div class="document-medicine-head">Value</div>
        <div class="document-medicine-head">Reference Range</div>
        <div class="document-medicine-head">Status</div>
        ${items
          .map(
            (item) => `
              <div>${escapeHtml(formatLabTestName(item.test_name))}</div>
              <div>${escapeHtml(`${item.value}`)}</div>
              <div>${escapeHtml(item.normal_range || "-")}</div>
              <div><span style="display:inline-flex;align-items:center;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:700;${getLabStatusStyle(item.status)}">${escapeHtml(item.status)}</span></div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function isDocumentInsightQuery(query: string) {
  return /\b(insight|summary|summarize|analysis|analyze|what does.*prescription|prescription.*tell|what.*document.*tell|explain.*document)\b/i.test(
    query
  );
}

function buildDocumentInsightCard(stored: StoredAnalysis) {
  const structured = stored.structured_extraction;
  const text = stored.extracted_text || "";
  const patientName = sanitizePatientName(
    structured?.patient_name?.trim() || extractTextField(text, "Patient")
  );
  const age = structured?.patient_context?.age || extractTextField(text, "Age");
  const gender = structured?.patient_context?.gender || extractTextField(text, "Sex");
  const medicines = getStoredMedicines(stored);
  const diagnoses = structured?.diagnosis?.length ? structured.diagnosis : extractListField(text, "Diagnosis");
  const symptoms = structured?.symptoms?.length ? structured.symptoms : extractListField(text, "Symptoms");
  const tests = structured?.tests?.length ? structured.tests : extractListField(text, "Tests");
  const labItems = stored.lab_analysis || [];
  const abnormalLabItems = getLabAttentionItems(labItems);
  const advice = sanitizeAdviceItems(
    structured?.advice_notes?.length ? structured.advice_notes : extractSectionLines(text, "Advice")
  );
  const reportTitle = stored.lab_metadata?.report_title || tests[0] || "";
  const reportInterpretation =
    stored.lab_metadata?.report_interpretation ||
    advice.find((item) => item && !looksLikeAddressOrClinicLine(item)) ||
    "";
  const followUp = sanitizeFollowUp(
    structured?.follow_up || stored.recommended_follow_up || extractTextField(text, "Follow up") || extractTextField(text, "Follow-up")
  );
  const vitals = getStoredVitals(stored);
  const prescriptionDate = structured?.prescription_date || extractTextField(text, "Prescription Date");
  const documentLabel = hasPrescriptionContext(stored)
    ? "Prescription"
    : getDocumentLabel(stored.document_type);

  if (!hasUsefulDocumentDetails(stored)) {
    return `
      <div class="document-insight">
        <div class="document-insight-header">
          <span class="document-insight-icon">📋</span>
          <div>
            <div class="document-insight-title">Document Uploaded</div>
            <div class="document-insight-subtitle">I could not extract enough structured details from this upload.</div>
          </div>
        </div>
        <div class="document-insight-note">
          Please try a clearer image or upload the document again. You can still ask a question if the preview is readable.
        </div>
      </div>
    `;
  }

  const patientRows = [
    patientName ? ["Patient", patientName] : null,
    age !== undefined && age !== null && `${age}`.trim() ? ["Age", `${age}`] : null,
    gender ? ["Sex", capitalizeSentence(gender)] : null,
    ["Document", documentLabel],
    reportTitle ? ["Report", reportTitle] : null,
    prescriptionDate ? ["Date", prescriptionDate] : null,
  ].filter(Boolean) as string[][];

  const insightRows = [
    diagnoses.length ? ["Diagnosis", diagnoses.slice(0, 3).join(", ")] : null,
    symptoms.length ? ["Symptoms", symptoms.slice(0, 5).join(", ")] : null,
    tests.length && !reportTitle ? ["Tests", tests.slice(0, 4).join(", ")] : null,
    reportInterpretation ? ["Report Note", reportInterpretation] : null,
    followUp ? ["Follow-up", followUp] : null,
  ].filter(Boolean) as string[][];

  const vitalRows = [
    vitals.blood_pressure ? ["Blood Pressure", vitals.blood_pressure] : null,
    vitals.heart_rate ? ["Heart Rate", vitals.heart_rate] : null,
    vitals.respiratory_rate ? ["Respiratory Rate", vitals.respiratory_rate] : null,
    vitals.body_temperature ? ["Temperature", vitals.body_temperature] : null,
  ].filter(Boolean) as string[][];

  return `
    <div class="document-insight">
      <div class="document-insight-header">
        <span class="document-insight-icon">📋</span>
        <div>
          <div class="document-insight-title">${escapeHtml(documentLabel)} Uploaded</div>
          <div class="document-insight-subtitle">${
            stored.document_type === "lab_report"
              ? abnormalLabItems.length
                ? buildLabAttentionSummary(labItems)
                : "All detected values are within the supported reference ranges"
              : patientName
              ? `Summary of the medication plan and observations for ${escapeHtml(patientName)}`
              : "Summary of the medication plan and observations found in the document"
          }</div>
        </div>
      </div>

      <div class="document-insight-grid">
        ${patientRows
          .map(
            ([label, value]) => `
              <div class="document-insight-item">
                <span>${escapeHtml(label)}</span>
                <strong>${escapeHtml(value)}</strong>
              </div>
            `
          )
          .join("")}
      </div>

      ${
        insightRows.length
          ? `<div class="document-insight-section">${insightRows
              .map(
                ([label, value]) => `
                  <div class="document-insight-line">
                    <strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}
                  </div>
                `
              )
              .join("")}</div>`
          : ""
      }

      ${buildLabResultsTable(labItems)}

      ${
        medicines.length
          ? `<div class="document-insight-section">
              <div class="document-insight-label">Prescription Details</div>
              <div class="document-medicine-table">
                <div class="document-medicine-head">Medicine</div>
                <div class="document-medicine-head">Dose</div>
                <div class="document-medicine-head">Frequency</div>
                <div class="document-medicine-head">Instructions</div>
                ${medicines
                  .slice(0, 8)
                  .map((medicine) => {
                    const name = `${medicine.name || "Unknown medicine"}${medicine.generic_name ? ` (${medicine.generic_name})` : ""}`;
                    return `
                      <div>${escapeHtml(name)}</div>
                      <div>${escapeHtml(medicine.strength || "-")}</div>
                      <div>${escapeHtml(medicine.frequency || medicine.duration || "-")}</div>
                      <div>${escapeHtml(medicine.instructions || medicine.dosage || "Follow as prescribed.")}</div>
                    `;
                  })
                  .join("")}
              </div>
            </div>`
          : ""
      }

      ${
        symptoms.length || vitalRows.length
          ? `<div class="document-insight-section">
              <div class="document-insight-label">Symptom & Vital Observations</div>
              ${
                symptoms.length
                  ? `<div class="document-insight-line"><strong>Symptoms:</strong> ${escapeHtml(symptoms.slice(0, 6).join(", "))}</div>`
                  : ""
              }
              ${
                vitalRows.length
                  ? `<div class="document-vital-grid">${vitalRows
                      .map(
                        ([label, value]) => `
                          <div class="document-vital-card">
                            <span>${escapeHtml(label)}</span>
                            <strong>${escapeHtml(value)}</strong>
                          </div>
                        `
                      )
                      .join("")}</div>`
                  : ""
              }
            </div>`
          : ""
      }

      ${
        advice.length
          ? `<div class="document-insight-section">
              <div class="document-insight-label">Important Care Notes</div>
              ${advice
                .slice(0, 5)
                .map((item) => `<div class="document-insight-pill">📝 ${escapeHtml(item)}</div>`)
                .join("")}
            </div>`
          : ""
      }

      ${
        followUp
          ? `<div class="document-insight-note"><strong>Follow-up:</strong> ${escapeHtml(followUp)}</div>`
          : ""
      }
    </div>
  `;
}

function buildDocumentInsightText(stored: StoredAnalysis) {
  const structured = stored.structured_extraction;
  const text = stored.extracted_text || "";

  if (!hasUsefulDocumentDetails(stored)) {
    return `
      <div class="general-answer">
        <div class="general-answer-header">
          <span class="general-answer-icon">📋</span>
          <span>Document Summary</span>
        </div>
        <p class="general-summary">I could not extract enough structured details from this upload to summarize it reliably.</p>
        <div class="safety-note"><span class="safety-note-icon">⚠️</span><span>Please try a clearer image or upload the document again.</span></div>
      </div>
    `;
  }

  const patientName =
    sanitizePatientName(structured?.patient_name?.trim() || extractTextField(text, "Patient")) ||
    "the patient";
  const medicines = getStoredMedicines(stored);
  const diagnoses = structured?.diagnosis?.length ? structured.diagnosis : extractListField(text, "Diagnosis");
  const symptoms = structured?.symptoms?.length ? structured.symptoms : extractListField(text, "Symptoms");
  const labItems = stored.lab_analysis || [];
  const advice = sanitizeAdviceItems(
    structured?.advice_notes?.length ? structured.advice_notes : extractSectionLines(text, "Advice")
  );
  const reportInterpretation =
    stored.lab_metadata?.report_interpretation ||
    advice.find((item) => item && !looksLikeAddressOrClinicLine(item)) ||
    "";
  const followUp = sanitizeFollowUp(
    structured?.follow_up || stored.recommended_follow_up || extractTextField(text, "Follow up") || extractTextField(text, "Follow-up")
  );
  const vitals = getStoredVitals(stored);
  const vitalRows = [
    vitals.blood_pressure ? `Blood pressure: ${vitals.blood_pressure}` : "",
    vitals.heart_rate ? `Heart rate: ${vitals.heart_rate}` : "",
    vitals.respiratory_rate ? `Respiratory rate: ${vitals.respiratory_rate}` : "",
    vitals.body_temperature ? `Temperature: ${vitals.body_temperature}` : "",
  ].filter(Boolean);

  if (stored.document_type === "lab_report" || labItems.length) {
    return `
      <div class="general-answer">
        <div class="general-answer-header">
          <span class="general-answer-icon">🧪</span>
          <span>Lab Report Summary</span>
        </div>
        <p class="general-summary">${buildLabAttentionSummary(labItems)}</p>
        ${buildLabResultsTable(labItems)}
        ${
          reportInterpretation
            ? `<div class="general-section-card"><div class="general-section-title">Report Note</div><p>${escapeHtml(reportInterpretation)}</p></div>`
            : ""
        }
        <div class="safety-note"><span class="safety-note-icon">⚠️</span><span>${escapeHtml(
          cleanMedicalDisclaimer(stored.disclaimer)
        )}</span></div>
      </div>
    `;
  }

  const medicineLines = medicines.length
    ? medicines
        .slice(0, 8)
        .map((medicine) => {
          const details = [medicine.strength, medicine.frequency, medicine.duration]
            .filter(Boolean)
            .join(", ");
          const instructions = medicine.instructions || medicine.dosage;
          return `
            <div class="general-point-row">
              <span class="general-point-number">💊</span>
              <span><strong>${escapeHtml(medicine.name || "Unknown medicine")}</strong>${
                medicine.generic_name ? ` (${escapeHtml(medicine.generic_name)})` : ""
              }${details ? ` - ${escapeHtml(details)}` : ""}${
                instructions ? `<br />${escapeHtml(instructions)}` : ""
              }</span>
            </div>
          `;
        })
        .join("")
    : `<p class="general-summary">No clear medicine list was detected in the uploaded document.</p>`;

  return `
    <div class="general-answer">
      <div class="general-answer-header">
        <span class="general-answer-icon">📋</span>
        <span>Document Summary</span>
      </div>
      <p class="general-summary">Based on the uploaded document for <strong>${escapeHtml(
        patientName
      )}</strong>, here is a concise summary of what it contains.</p>

      <div class="general-section-card">
        <div class="general-section-title">Prescription Details</div>
        <div class="general-point-list">${medicineLines}</div>
      </div>

      ${
        symptoms.length || diagnoses.length || vitalRows.length
          ? `<div class="general-section-card">
              <div class="general-section-title">Health Observations</div>
              ${
                diagnoses.length
                  ? `<div class="rx-row"><strong>Diagnosis:</strong> ${escapeHtml(diagnoses.join(", "))}</div>`
                  : ""
              }
              ${
                symptoms.length
                  ? `<div class="rx-row"><strong>Symptoms:</strong> ${escapeHtml(symptoms.join(", "))}</div>`
                  : ""
              }
              ${
                vitalRows.length
                  ? `<div class="rx-row"><strong>Vitals:</strong> ${escapeHtml(vitalRows.join(" | "))}</div>`
                  : ""
              }
            </div>`
          : ""
      }

      ${
        advice.length
          ? `<div class="general-section-card">
              <div class="general-section-title">Important Care Notes</div>
              <div class="general-point-list">${advice
                .slice(0, 5)
                .map(
                  (item, index) => `
                    <div class="general-point-row">
                      <span class="general-point-number">${index + 1}</span>
                      <span>${escapeHtml(item)}</span>
                    </div>
                  `
                )
                .join("")}</div>
            </div>`
          : ""
      }

      ${
        followUp
          ? `<div class="safety-note"><span class="safety-note-icon">📅</span><span><strong>Follow-up:</strong> ${escapeHtml(
              followUp
            )}</span></div>`
          : ""
      }
    </div>
  `;
}

function getStoredContextMessages(): Msg[] {
  const initialMessages = [initialAiMessage];
  const isChatContextActive =
    localStorage.getItem(CHAT_CONTEXT_ACTIVE_KEY) === "true";
  const shouldShowInsight =
    localStorage.getItem(DOCUMENT_INSIGHT_PENDING_KEY) === "true";
  if (!isChatContextActive || !shouldShowInsight) return initialMessages;

  const stored = localStorage.getItem("prescription_analysis");
  if (!stored) return initialMessages;

  try {
    const parsed: StoredAnalysis = JSON.parse(stored);
    localStorage.removeItem(DOCUMENT_INSIGHT_PENDING_KEY);
    return [
      ...initialMessages,
      {
        role: "ai",
        text: buildDocumentInsightCard(parsed),
        time: getCurrentTime(),
      },
    ];
  } catch (error) {
    console.error("Failed to parse prescription_analysis:", error);
    return initialMessages;
  }
}

export default function ChatPage() {
  const [showEmergency, setShowEmergency] = useState(true);
  const [typing, setTyping] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>(getInitialMessages);

  const listRef = useRef<HTMLDivElement | null>(null);
  const autoPromptSentRef = useRef(false);
  const sendAutoPrompt = useEffectEvent((prompt: string) => {
    void send(prompt);
  });

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, typing]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setMessages(getStoredContextMessages());
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const autoPrompt = localStorage.getItem("auto_chat_prompt");
    if (!autoPrompt || autoPromptSentRef.current) return;

    autoPromptSentRef.current = true;
    localStorage.removeItem("auto_chat_prompt");

    const timer = setTimeout(() => {
      sendAutoPrompt(autoPrompt);
    }, 300);

    return () => clearTimeout(timer);
  }, []);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || typing) return;

    setMessages((m) => [
      ...m,
      { role: "user", text: trimmed, time: getCurrentTime() },
    ]);

    setInput("");
    setTyping(true);

    try {
      const stored = localStorage.getItem("prescription_analysis");
      const isChatContextActive =
        localStorage.getItem(CHAT_CONTEXT_ACTIVE_KEY) === "true";
      let backendQuery = trimmed;

      if (stored && isChatContextActive) {
        const parsed: StoredAnalysis = JSON.parse(stored);

        if (isDocumentInsightQuery(trimmed)) {
          setMessages((m) => [
            ...m,
            { role: "ai", text: buildDocumentInsightText(parsed), time: getCurrentTime() },
          ]);
          setTyping(false);
          return;
        }

        if (hasPrescriptionContext(parsed)) {
          const prescriptionReply = buildPrescriptionChatAnswer(trimmed, parsed);
          if (prescriptionReply) {
            setMessages((m) => [
              ...m,
              { role: "ai", text: prescriptionReply, time: getCurrentTime() },
            ]);
            setTyping(false);
            return;
          }
        } else if (parsed.document_type === "lab_report") {
          const labReply = buildLabChatAnswer(trimmed, parsed);
          if (labReply) {
            setMessages((m) => [
              ...m,
              { role: "ai", text: labReply, time: getCurrentTime() },
            ]);
            setTyping(false);
            return;
          }
        }

        backendQuery = buildContextualQuery(trimmed, parsed);
      }

      if (backendQuery === trimmed) {
        backendQuery = buildRecentConversationQuery(trimmed, messages);
      }

      const res = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: backendQuery }),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      const data = await res.json();
      const formattedAnswer = formatAiAnswer(
        data.answer || "No response generated.",
        data.detected_domain
      );

      setMessages((m) => [
        ...m,
        {
          role: "ai",
          text: formattedAnswer,
          sources: data.sources || [],
          time: getCurrentTime(),
        },
      ]);
    } catch (error) {
      console.error("Chat request failed:", error);
      setMessages((m) => [
        ...m,
        {
          role: "ai",
          text: `
            <p>Warning: Unable to connect to backend.</p>
            <p>Please make sure:</p>
            <ul>
              <li>FastAPI server is running</li>
              <li>Backend URL is correct</li>
              <li>CORS is enabled in backend</li>
            </ul>
          `,
          time: getCurrentTime(),
        },
      ]);
    } finally {
      setTyping(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  function startNewChat() {
    setMessages([initialAiMessage]);
    setInput("");
    localStorage.removeItem("auto_chat_prompt");
    localStorage.removeItem(CHAT_CONTEXT_ACTIVE_KEY);
    localStorage.removeItem(DOCUMENT_INSIGHT_PENDING_KEY);
    localStorage.removeItem("prescription_analysis");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "var(--white, #fff)" }}>

      {/* EMERGENCY BANNER */}
      {showEmergency && (
        <div className="emergency-banner">
          <div>
            <strong>EMERGENCY?</strong> If experiencing chest pain,
            difficulty breathing, or other emergencies - call{" "}
            <strong>112 / 911 immediately.</strong> Do not use this chatbot.
          </div>
          <button className="emergency-close" onClick={() => setShowEmergency(false)}>
            x
          </button>
        </div>
      )}

      {/* CHAT LAYOUT */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* SIDEBAR */}
        <aside className="chat-sidebar">

          {/* Brand logo links to home */}
          <div style={{ padding: "20px 16px 12px", borderBottom: "1px solid var(--gray-200, #e5e7eb)" }}>
            <Link
              href="/"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                textDecoration: "none",
              }}
            >
              <div style={{
                width: 34,
                height: 34,
                borderRadius: 10,
                background: "linear-gradient(135deg, #2563eb 0%, #06b6d4 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontSize: 16,
                fontWeight: 700,
                flexShrink: 0,
              }}>
                M
              </div>
              <span style={{
                fontWeight: 700,
                fontSize: 16,
                color: "var(--gray-900, #111827)",
                letterSpacing: "-0.02em",
              }}>
                MedInsight AI
              </span>
            </Link>
          </div>

          {/* New Chat */}
          <div className="sidebar-top" style={{ paddingTop: 16 }}>
            <button className="sidebar-new-chat" onClick={startNewChat}>
              + New Chat
            </button>
          </div>

          {/* Chat history */}
          <div className="sidebar-section">
            <div className="sidebar-section-title">Recent</div>
            <div className="chat-history-item active">
              <span className="chat-history-dot" style={{ background: "var(--blue, #2563eb)" }} />
              <span className="chat-history-text">Current conversation</span>
            </div>
          </div>

          {/* Settings at bottom */}
          <div className="sidebar-footer">
            <button className="sidebar-settings-btn">
              Settings & Preferences
            </button>
          </div>
        </aside>

        {/* MAIN CHAT */}
        <main className="chat-main">

          {/* Top bar */}
          <div className="chat-topbar">
            <div style={{ flex: 1 }}>
              <div className="chat-topbar-title">Symptom, Medicine & Medical Document Assistant</div>
              <span className="chat-topbar-subtitle">
                Academic Mode | RAG-powered | Educational responses only
              </span>
            </div>

            {/* Clear button (replaces dustbin) */}
            <button
              onClick={startNewChat}
              style={{
                padding: "7px 16px",
                borderRadius: "var(--radius-full, 9999px)",
                border: "1.5px solid var(--gray-200, #e5e7eb)",
                background: "var(--white, #fff)",
                color: "var(--gray-600, #4b5563)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                transition: "all .15s",
                fontFamily: "var(--font, sans-serif)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "#fef2f2";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "#fca5a5";
                (e.currentTarget as HTMLButtonElement).style.color = "#dc2626";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "var(--white, #fff)";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--gray-200, #e5e7eb)";
                (e.currentTarget as HTMLButtonElement).style.color = "var(--gray-600, #4b5563)";
              }}
            >
              Clear
            </button>

            {/* Back link */}
            <Link className="btn btn-ghost btn-sm" href="/">
              {"<- Back"}
            </Link>
          </div>

          {/* Messages */}
          <div className="chat-messages" ref={listRef}>
            {messages.map((m, idx) => (
              <div key={idx} className={`chat-message ${m.role}`}>
                <div className={`chat-avatar ${m.role}`}>
                  {m.role === "ai" ? "🩺" : "You"}
                </div>
                <div className="chat-bubble-wrap">
                  <div
                    className="chat-bubble"
                    dangerouslySetInnerHTML={{ __html: m.text }}
                  />
                  {m.role === "ai" && m.sources?.length ? (
                    <div className="chat-sources">
                      {m.sources.map((s) => (
                        <span key={s} className="source-chip">{s}</span>
                      ))}
                    </div>
                  ) : null}
                  {m.time ? <div className="chat-timestamp">{m.time}</div> : null}
                </div>
              </div>
            ))}

            {typing && (
              <div className="chat-message ai">
                <div className="chat-avatar ai">🩺</div>
                <div className="chat-bubble-wrap">
                  <div className="typing-bubble">
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input area */}
          <div className="chat-input-area">
            <div className="chat-disclaimer">
              Academic use only | No data stored | Not medical advice
            </div>

            <div className="chat-input-box">
              <textarea
                className="chat-input-field"
                placeholder="Ask about symptoms, medicines, prescriptions, lab reports, or radiology reports..."
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
              />

              <div className="chat-input-actions">
                {/* + button for upload (replaces paperclip emoji) */}
                <Link
                  href="/upload"
                  title="Upload prescription or lab report"
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 8,
                    background: "var(--blue, #2563eb)",
                    color: "#fff",
                    fontSize: 20,
                    fontWeight: 400,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    textDecoration: "none",
                    flexShrink: 0,
                    lineHeight: 1,
                    transition: "background .15s",
                  }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLAnchorElement).style.background = "#1d4ed8")
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLAnchorElement).style.background = "var(--blue, #2563eb)")
                  }
                >
                  +
                </Link>

                {/* Send button */}
                <button
                  className="chat-send-button"
                  onClick={() => send(input)}
                  disabled={typing}
                >
                  ➤
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

// Helper functions

function normalizeLabName(name: string) {
  return name.replace(/[()]/g, "_").replace(/\s+/g, "_").replace(/[^A-Z_]/g, "");
}

function splitInterpretation(text: string) {
  const marker = "Lifestyle precautions:";
  const idx = text.indexOf(marker);
  if (idx === -1) {
    return {
      interpretation: text.trim(),
      lifestyle:
        "General precautions: stay hydrated, avoid self-medication, follow a balanced diet, and review the result with your doctor.",
    };
  }
  return {
    interpretation: text.slice(0, idx).trim(),
    lifestyle: text.slice(idx + marker.length).trim(),
  };
}

function findRelevantLabItems(query: string, items: LabAnalysisItem[]) {
  const lower = query.toLowerCase();
  const matched = items.filter((item) => {
    const rawName = item.test_name.toLowerCase().replace(/_/g, " ");
    if (lower.includes(rawName)) return true;
    const normalized = normalizeLabName(item.test_name);
    const aliases = LAB_TEST_LABELS[normalized] || [];
    return aliases.some((alias) => lower.includes(alias));
  });
  return matched.length ? matched : items;
}

function buildLabChatAnswer(query: string, stored: StoredAnalysis) {
  const items = stored.lab_analysis || [];
  if (!items.length) return null;

  const relevant = findRelevantLabItems(query, items);
  const lower = query.toLowerCase();
  const asksAbnormalOnly =
    lower.includes("abnormal value") ||
    lower.includes("abnormal values") ||
    lower.includes("highlight abnormal") ||
    lower.includes("which values are abnormal") ||
    lower.includes("show abnormal");
  const wantsLifestyle =
    lower.includes("lifestyle") ||
    lower.includes("precaution") ||
    lower.includes("diet") ||
    lower.includes("exercise") ||
    lower.includes("what should i do");
  const wantsMeaning =
    lower.includes("abnormal") ||
    lower.includes("mean") ||
    lower.includes("explain") ||
    lower.includes("why") ||
    lower.includes("highlight") ||
    lower.includes("report");
  const asksNormalOnly =
    lower.includes("which values are normal") ||
    lower.includes("normal values") ||
    lower.includes("show normal");
  const wantsDetailedAnswer = wantsLifestyle || wantsMeaning;
  const abnormalItems = getLabAttentionItems(relevant);
  const normalItems = relevant.filter((item) => item.status === "NORMAL");
  const selectedAttentionItems =
    abnormalItems.length && relevant.length === items.length ? abnormalItems : relevant;
  const displayItems = asksNormalOnly
    ? normalItems
    : asksAbnormalOnly || wantsMeaning || wantsLifestyle
      ? selectedAttentionItems
      : relevant;

  if (asksAbnormalOnly && !abnormalItems.length) {
    return `
      <div class="general-answer">
        <div class="general-answer-header">
          <span class="general-answer-icon">🧪</span>
          <span>Lab Report</span>
        </div>
        <p class="general-summary">I did not find any detected values outside the supported reference ranges.</p>
        ${buildLabResultsTable(relevant)}
      </div>
    `;
  }

  const lines = displayItems.map((item) => {
    const parts = splitInterpretation(item.interpretation || "");
    const header = `<strong>${formatLabTestName(item.test_name)}</strong>: ${item.value} (${item.status}, reference ${item.normal_range})`;
    if (asksAbnormalOnly || !wantsDetailedAnswer) return header;
    if (item.status === "NORMAL") return `${header}<br />Interpretation: This value is within the provided reference range.`;
    if (item.test_name === "HEMOGLOBIN" && item.status === "LOW") {
      return `${header}<br />Interpretation: Low hemoglobin can be associated with anemia, but this report alone cannot confirm the cause.`;
    }
    if (item.test_name === "PCV" && item.status === "HIGH") {
      return `${header}<br />Interpretation: High PCV means the percentage of red blood cells in the blood is above the listed range. Dehydration and other medical causes can affect it.`;
    }
    if (item.status === "BORDERLINE") {
      return `${header}<br />Interpretation: This value is at the lower limit of the provided reference range.`;
    }
    if (wantsLifestyle && !wantsMeaning)
      return `${header}<br />Lifestyle precautions: ${parts.lifestyle}`;
    return `${header}<br />Interpretation: ${parts.interpretation}<br />Lifestyle precautions: ${parts.lifestyle}`;
  });

  const intro =
    asksNormalOnly
      ? "Here are the values that are within the supported reference ranges:"
      : asksAbnormalOnly || !wantsDetailedAnswer
      ? abnormalItems.length
        ? "Here are the abnormal values from your uploaded lab report:"
        : "Here are the detected values from your uploaded lab report:"
      : displayItems.length === abnormalItems.length && abnormalItems.length
        ? "Your report mainly shows these value(s) needing attention:"
        : "Here is what your selected result may indicate:";
  const reportInterpretation =
    stored.lab_metadata?.report_interpretation ||
    stored.structured_extraction?.advice_notes?.[0] ||
    "";

  const disclaimer = stored.disclaimer
    ? `<div class="safety-note"><span class="safety-note-icon">⚠️</span><span>${escapeHtml(cleanMedicalDisclaimer(stored.disclaimer))}</span></div>`
    : "";
  return `
    <div class="general-answer">
      <div class="general-answer-header">
        <span class="general-answer-icon">🧪</span>
        <span>Lab Report</span>
      </div>
      <p class="general-summary">${intro}</p>
      ${buildLabResultsTable(displayItems)}
      ${
        wantsDetailedAnswer
          ? `<div class="general-section-card">
              <div class="general-section-title">Explanation</div>
              <p>${lines.join("<br /><br />")}${
                reportInterpretation ? `<br /><br />Report note: ${escapeHtml(reportInterpretation)}` : ""
              }</p>
            </div>`
          : ""
      }
      ${disclaimer}
    </div>
  `;
}

const COMMON_MEDICINE_FALLBACKS: Record<
  string,
  { generic: string; uses: string; sideEffects: string; precautions: string }
> = {
  paracetamol: {
    generic: "Paracetamol / Acetaminophen",
    uses: "Fever and mild to moderate pain relief.",
    sideEffects: "Usually well tolerated; nausea or rash can occur. High doses can seriously harm the liver.",
    precautions: "Avoid taking multiple products that contain paracetamol and avoid excess alcohol.",
  },
  acetaminophen: {
    generic: "Paracetamol / Acetaminophen",
    uses: "Fever and mild to moderate pain relief.",
    sideEffects: "Usually well tolerated; nausea or rash can occur. High doses can seriously harm the liver.",
    precautions: "Avoid taking multiple products that contain acetaminophen and avoid excess alcohol.",
  },
  amoxicillin: {
    generic: "Amoxicillin",
    uses: "Antibiotic used for bacterial infections when prescribed by a doctor.",
    sideEffects: "Nausea, diarrhea, stomach upset, rash, or allergy.",
    precautions: "Tell your doctor about penicillin allergy. Complete the course unless your doctor advises otherwise.",
  },
  augmentin: {
    generic: "Amoxicillin + Clavulanic Acid",
    uses: "Antibiotic combination used for bacterial infections when prescribed.",
    sideEffects: "Diarrhea, nausea, vomiting, stomach upset, rash, or allergy.",
    precautions: "Take only as prescribed and tell your doctor about penicillin allergy or liver problems.",
  },
  "amoxicillin clavulanic acid": {
    generic: "Amoxicillin + Clavulanic Acid",
    uses: "Antibiotic combination used for bacterial infections when prescribed.",
    sideEffects: "Diarrhea, nausea, vomiting, stomach upset, rash, or allergy.",
    precautions: "Take only as prescribed and tell your doctor about penicillin allergy or liver problems.",
  },
  metformin: {
    generic: "Metformin",
    uses: "Helps control blood sugar in type 2 diabetes.",
    sideEffects: "Nausea, loose stools, stomach upset, gas, or metallic taste.",
    precautions: "Take with meals if prescribed. Kidney problems or heavy alcohol use need medical review.",
  },
  atorvastatin: {
    generic: "Atorvastatin",
    uses: "Helps lower cholesterol and reduce cardiovascular risk.",
    sideEffects: "Muscle pain, headache, stomach upset, or raised liver enzymes.",
    precautions: "Report unexplained muscle pain. Avoid grapefruit unless your doctor says it is safe.",
  },
  clarithromycin: {
    generic: "Clarithromycin",
    uses: "Antibiotic used for certain bacterial infections when prescribed.",
    sideEffects: "Nausea, diarrhea, stomach pain, altered taste, or headache.",
    precautions: "Tell your doctor about liver disease, heart rhythm problems, or other regular medicines.",
  },
  zoclar: {
    generic: "Clarithromycin",
    uses: "Antibiotic used for certain bacterial infections when prescribed.",
    sideEffects: "Nausea, diarrhea, stomach pain, altered taste, or headache.",
    precautions: "Tell your doctor about liver disease, heart rhythm problems, or other regular medicines.",
  },
  vomilast: {
    generic: "Doxylamine + Pyridoxine + Folic Acid",
    uses: "Used for nausea and vomiting, especially pregnancy-related nausea, when prescribed.",
    sideEffects: "Sleepiness, dizziness, dry mouth, or tiredness.",
    precautions: "Avoid driving if sleepy. Use in pregnancy only as advised by a doctor.",
  },
  gestakind: {
    generic: "Isoxsuprine",
    uses: "Used in selected circulation or pregnancy-related conditions only when prescribed.",
    sideEffects: "Dizziness, flushing, nausea, fast heartbeat, or low blood pressure.",
    precautions: "Use only under medical supervision, especially with heart or blood pressure problems.",
  },
  isoxsuprine: {
    generic: "Isoxsuprine",
    uses: "Used in selected circulation or pregnancy-related conditions only when prescribed.",
    sideEffects: "Dizziness, flushing, nausea, fast heartbeat, or low blood pressure.",
    precautions: "Use only under medical supervision, especially with heart or blood pressure problems.",
  },
  benadryl: {
    generic: "Diphenhydramine combination",
    uses: "Cough and allergy symptom relief, depending on the formulation.",
    sideEffects: "Sleepiness, dizziness, dry mouth, stomach upset, or impaired coordination.",
    precautions: "Avoid alcohol and driving if sleepy. Ask a doctor before use in pregnancy or liver/kidney disease.",
  },
  omeprazole: {
    generic: "Omeprazole",
    uses: "Reduces stomach acid; used for acidity, GERD, and ulcer-related symptoms when prescribed.",
    sideEffects: "Headache, nausea, stomach pain, gas, diarrhea, or constipation.",
    precautions: "Use as prescribed. Long-term use should be reviewed by a doctor.",
  },
};

function normalizeMedicineKey(value?: string) {
  return (value || "").toLowerCase().replace(/[^a-z0-9\s+]/g, " ").replace(/\s+/g, " ").trim();
}

function getMedicineFallback(item: PrescriptionAnalysisItem) {
  const values = [item.display_name, item.brand_name, item.generic_name, item.original_line]
    .filter(Boolean)
    .map((value) => normalizeMedicineKey(value));

  for (const value of values) {
    if (COMMON_MEDICINE_FALLBACKS[value]) return COMMON_MEDICINE_FALLBACKS[value];
    for (const key of Object.keys(COMMON_MEDICINE_FALLBACKS)) {
      if (value.includes(key) || key.includes(value)) {
        return COMMON_MEDICINE_FALLBACKS[key];
      }
    }
  }
  return null;
}

function getPrescriptionIntent(query: string) {
  const lower = query.toLowerCase();
  return {
    analysis: /\b(analysis|analyze|summary|summarize|explain prescription)\b/.test(lower),
    list: /\b(which medicine|which medicines|list medicine|list medicines|what medicines|show medicines)\b/.test(lower),
    uses: /\b(use|uses|used for|why prescribed)\b/.test(lower),
    sideEffects: /\b(side effect|side effects|adverse)\b/.test(lower),
    precautions: /\b(precaution|precautions|warning|warnings|careful|avoid)\b/.test(lower),
    interaction: /\b(interaction|interact|take together|combine|with)\b/.test(lower),
    dosage: /\b(dose|dosage|frequency|duration|how to take|when to take)\b/.test(lower),
  };
}

function makePrescriptionItemCard(item: PrescriptionAnalysisItem, intent: ReturnType<typeof getPrescriptionIntent>) {
  const name = item.display_name || item.brand_name || item.generic_name || "Unknown medicine";
  const fallback = getMedicineFallback(item);
  const generic = item.generic_name || fallback?.generic || "";
  const rows: string[] = [];

  if (generic && normalizeMedicineKey(generic) !== normalizeMedicineKey(name)) {
    rows.push(`<div class="rx-row"><strong>Generic:</strong> ${escapeHtml(generic)}</div>`);
  }
  if (intent.dosage) {
    const dose = [item.strength, item.frequency, item.duration].filter(Boolean).join(" | ");
    rows.push(`<div class="rx-row"><strong>Dosage:</strong> ${escapeHtml(dose || "Follow the uploaded prescription exactly.")}</div>`);
    if (item.instructions) rows.push(`<div class="rx-row"><strong>Instructions:</strong> ${escapeHtml(item.instructions)}</div>`);
  }
  if (intent.uses) {
    rows.push(`<div class="rx-row"><strong>Uses:</strong> ${escapeHtml(item.uses || fallback?.uses || "Use is not confirmed from the uploaded prescription context. Please verify with your doctor.")}</div>`);
  }
  if (intent.sideEffects) {
    rows.push(`<div class="rx-row"><strong>Common side effects:</strong> ${escapeHtml(item.side_effects || fallback?.sideEffects || "Side effect details are not confirmed here. Ask your doctor or pharmacist for medicine-specific advice.")}</div>`);
  }
  if (intent.precautions) {
    rows.push(`<div class="rx-row"><strong>Precautions:</strong> ${escapeHtml(fallback?.precautions || "Take only as prescribed. Tell your doctor about allergies, pregnancy, liver/kidney disease, and other medicines.")}</div>`);
  }

  if (!rows.length) {
    rows.push(`<div class="rx-row"><strong>Detected:</strong> ${escapeHtml([item.strength, item.frequency, item.duration].filter(Boolean).join(" | ") || "Medicine found in uploaded prescription.")}</div>`);
  }

  return `
    <div class="rx-medicine-card">
      <div class="rx-medicine-title">💊 ${escapeHtml(name)}</div>
      ${rows.join("")}
    </div>
  `;
}

function getMedicineSearchTerms(item: PrescriptionAnalysisItem) {
  const values = [item.display_name, item.brand_name, item.generic_name, item.original_line]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  const tokens = values.split(/[^a-z0-9]+/).filter((token) => token.length >= 3);
  const fallback = getMedicineFallback(item);
  if (fallback?.generic) {
    tokens.push(...fallback.generic.toLowerCase().split(/[^a-z0-9]+/).filter((token) => token.length >= 3));
  }
  return Array.from(new Set(tokens));
}

function getPrescriptionItems(stored: StoredAnalysis): PrescriptionAnalysisItem[] {
  if (stored.detailed_analysis?.length) return stored.detailed_analysis;
  if (stored.medicines?.length) {
    return stored.medicines.map((medicine) => ({
      display_name: medicine.name,
      original_line: medicine.dosage || medicine.instructions,
      brand_name: medicine.name,
      generic_name: medicine.generic_name,
      uses: medicine.uses,
      side_effects: medicine.side_effects,
      strength: medicine.strength,
      frequency: medicine.frequency,
      duration: medicine.duration,
      instructions: medicine.instructions,
      analysis: "",
    }));
  }
  return [];
}

function findRelevantPrescriptionItems(query: string, items: PrescriptionAnalysisItem[]) {
  const lower = query.toLowerCase();
  const directMatches = items.filter((item) =>
    getMedicineSearchTerms(item).some((term) => lower.includes(term))
  );
  if (directMatches.length) return directMatches;
  return items.filter((item) => {
    const values = [item.display_name, item.brand_name, item.generic_name, item.original_line]
      .filter(Boolean)
      .map((value) => value!.toLowerCase());
    return values.some((value) => value.includes(lower) || lower.includes(value));
  });
}

function buildPrescriptionChatAnswer(query: string, stored: StoredAnalysis) {
  const items = getPrescriptionItems(stored);
  if (!items.length) return null;

  const lower = query.toLowerCase();
  const relevant = findRelevantPrescriptionItems(query, items);
  const intent = getPrescriptionIntent(query);
  const asksForDetails =
    intent.uses ||
    intent.sideEffects ||
    intent.precautions ||
    intent.dosage ||
    lower.includes("about") ||
    lower.includes("tell me") ||
    lower.includes("explain");

  if (intent.interaction) {
    return null;
  }

  if (intent.analysis) {
    const meds = items
      .slice(0, 6)
      .map((item) => {
        const name = item.display_name || item.brand_name || item.generic_name || "Unknown medicine";
        const details = [item.strength, item.frequency, item.duration].filter(Boolean).join(" | ");
        return `<div class="rx-row"><strong>${escapeHtml(name)}:</strong> ${escapeHtml(details || "Detected in uploaded prescription.")}</div>`;
      })
      .join("");
    const diagnosis = stored.analysis ? `<p>${escapeHtml(stored.analysis)}</p>` : "";
    return `
      <div class="rx-answer">
        <div class="rx-answer-title">Prescription Summary</div>
        ${diagnosis}
        <div class="rx-medicine-card">${meds}</div>
        <div class="rx-note">This is a short educational summary of the uploaded prescription. Follow your doctor's written instructions.</div>
      </div>
    `;
  }

  if (intent.list && !relevant.length) {
    const names = items.map(
      (item) => item.display_name || item.brand_name || item.generic_name || "Unknown medicine"
    );
    return `
      <div class="rx-answer">
        <div class="rx-answer-title">Medicines Detected</div>
        <div class="rx-medicine-card">${names.map((name) => `<div class="rx-row">💊 ${escapeHtml(name)}</div>`).join("")}</div>
      </div>
    `;
  }

  if (!relevant.length) {
    return `<div class="rx-answer"><div class="rx-answer-title">Prescription Context Loaded</div><p>Ask about a specific medicine from the uploaded prescription, and I will show only the details you request.</p></div>`;
  }

  if (!asksForDetails && relevant.length > 1) {
    const names = relevant.map(
      (item) => item.display_name || item.brand_name || item.generic_name || "Unknown medicine"
    );
    return `
      <div class="rx-answer">
        <div class="rx-answer-title">Multiple Medicines Found</div>
        <div class="rx-medicine-card">${names.map((name) => `<div class="rx-row">💊 ${escapeHtml(name)}</div>`).join("")}</div>
        <div class="rx-note">Ask about one medicine specifically, or ask for uses, side effects, precautions, or dosage.</div>
      </div>
    `;
  }

  const effectiveIntent = {
    ...intent,
    uses: intent.uses || (!intent.sideEffects && !intent.precautions && !intent.dosage),
  };

  if (lower.includes("uses and side") || lower.includes("use and side")) {
    effectiveIntent.uses = true;
    effectiveIntent.sideEffects = true;
  }

  return `
    <div class="rx-answer">
      <div class="rx-answer-title">Medicine Information</div>
      ${relevant.slice(0, 4).map((item) => makePrescriptionItemCard(item, effectiveIntent)).join("")}
      <div class="rx-note">Educational information only. Do not start, stop, or combine medicines without your doctor or pharmacist.</div>
    </div>
  `;
}
