"use client";

import type { CSSProperties } from "react";
import { useState } from "react";

const faqs = [
  {
    q: "Is MedInsight AI a substitute for a doctor?",
    a: "No. MedInsight AI is an educational medical assistant designed to provide general information, explain prescriptions, and interpret lab reports. It should not replace a qualified doctor, diagnosis, or professional medical treatment.",
  },
  {
    q: "What data sources does the AI use?",
    a: "MedInsight AI uses a curated medical knowledge base built from symptom datasets, medicine information, medical question-answer data, and Indian brand-generic medicine mappings. It combines this knowledge with RAG and FAISS vector search to return relevant responses.",
  },
  {
    q: "Is my data private and secure?",
    a: "Yes. Your uploaded files and queries are processed only for generating the response during your session and are not stored permanently. The system is designed to keep your medical information private and secure.",
  },
  {
    q: "What should I do in a medical emergency?",
    a: "If you are facing severe symptoms such as chest pain, difficulty breathing, stroke-like signs, unconsciousness, seizures, or severe bleeding, seek immediate medical help right away. Immediately call your local emergency services, such as 112 in India, and do not rely on MedInsight AI in emergencies. Time is critical, so always prioritize emergency medical services and professional care over any AI tool.",
  },
  {
    q: "What types of medical documents can I upload?",
    a: "You can upload prescription images and lab report images for analysis. The system extracts readable medical text, identifies medicines or test values, and provides simple educational explanations.",
  },
  {
    q: "Can the AI diagnose my condition?",
    a: "No. MedInsight AI does not diagnose diseases or prescribe treatment. It provides educational insights, medicine information, and lab report interpretation to help users understand medical information better.",
  },
];

export default function FAQClient() {
  const [open, setOpen] = useState(0);

  return (
    <section
      className="section section-sm"
      id="faq"
      style={{ background: "var(--bg)" } as CSSProperties}
    >
      <div className="container-sm">
        <div className="section-header">
          <div className="section-label">FAQ</div>
          <h2 className="section-title">Frequently asked questions</h2>
        </div>

        <div className="faq-list">
          {faqs.map((f, idx) => {
            const isOpen = idx === open;
            return (
              <div key={f.q} className={`faq-item ${isOpen ? "open" : ""}`}>
                <button
                  className="faq-question"
                  onClick={() => setOpen(isOpen ? -1 : idx)}
                >
                  {f.q}
                  <span className="faq-chevron">v</span>
                </button>
                <div className="faq-answer">{f.a}</div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
