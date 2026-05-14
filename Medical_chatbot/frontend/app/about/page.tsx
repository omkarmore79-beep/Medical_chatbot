import Link from "next/link";
import Navbar from "../components/Navbar";

// ─── Data ─────────────────────────────────────────────────────────────────────

const capabilities = [
  {
    icon: "🩺",
    title: "Symptom Guidance",
    desc: "Describe symptoms in plain language and receive structured educational insights about possible causes and general next steps — drawn from curated medical knowledge.",
  },
  {
    icon: "💊",
    title: "Drug Information Lookup",
    desc: "Look up medicine uses, side effects, and precautions. Supports brand-to-generic name mapping so users can understand both trade and generic medicine names.",
  },
  {
    icon: "📋",
    title: "Prescription Image Analysis",
    desc: "Upload a prescription image and the system extracts medicine names using OCR, then provides structured educational explanations for each identified medication.",
  },
  {
    icon: "🔬",
    title: "Lab Report Interpretation",
    desc: "Upload lab report images to have test names and values extracted, abnormal results flagged, and simplified educational explanations generated in plain language.",
  },
];

const steps = [
  { num: "01", title: "User Input",            desc: "The user asks a medical question or uploads a prescription or lab report image." },
  { num: "02", title: "Text Extraction",        desc: "OCR processes uploaded images to extract readable medical text and key values." },
  { num: "03", title: "Knowledge Retrieval",    desc: "RAG + FAISS vector search locates the most relevant context from curated datasets." },
  { num: "04", title: "AI Response Generation", desc: "Gemini API generates a clear, structured educational response from retrieved context." },
  { num: "05", title: "Safety Filtering",       desc: "Emergency detection, confidence checks, and safeguards are applied before the final answer." },
];

const techStack = [
  { name: "Next.js",        role: "Frontend framework",                    tag: "UI",      badge: "nextjs"  },
  { name: "FastAPI",        role: "Backend API server",                    tag: "Backend", badge: "fastapi" },
  { name: "Tesseract OCR",  role: "Prescription & lab text extraction",    tag: "OCR",     badge: "ocr"     },
  { name: "FAISS",          role: "Vector similarity search",              tag: "Search",  badge: "faiss"   },
  { name: "RAG Pipeline",   role: "Context-aware retrieval generation",    tag: "AI",      badge: "rag"     },
  { name: "Gemini API",     role: "Language & vision intelligence",        tag: "LLM",     badge: "python"  },
];

const objectives = [
  "Build an AI-powered medical information assistant for educational use",
  "Simplify symptom-based medical information retrieval for non-clinical users",
  "Explain medicine details from both text queries and prescription images",
  "Interpret lab report values in an accessible and understandable format",
  "Integrate OCR, RAG, vector search, and LLMs into one coherent system",
  "Design a safety-focused platform that discourages overclaiming and promotes professional consultation",
];

const futureItems = [
  { num: "01", title: "Multilingual Support",      desc: "Hindi, Marathi, and regional language responses to reach more users." },
  { num: "02", title: "Improved OCR Accuracy",     desc: "Better handwriting detection and noisy image handling for prescriptions." },
  { num: "03", title: "Deeper Medicine Coverage",  desc: "Expanded drug knowledge base including rare conditions and specialist data." },
  { num: "04", title: "Doctor-Side Review",        desc: "A portal where healthcare providers can audit and validate AI responses." },
  { num: "05", title: "Better Lab Report Analysis",desc: "Improved detection of test values and clearer explanations of abnormal results." },
  { num: "06", title: "Stronger Scalability",      desc: "Better deployment, monitoring, and performance support for larger real-world usage." },
];

const team = [
  { icon: "👨‍💻", name: "Tanmay Borundiya", role: "Student Developer", prn: "20220802277" },
  { icon: "👨‍💻", name: "Omkar More", role: "Student Developer", prn: "20220802279" },
  { icon: "👨‍💻", name: "Parth Biradar", role: "Student Developer", prn: "20220802234" },
  { icon: "👩‍🏫", name: "Mrs. Purva D. Thakare", role: "Project Supervisor", prn: "" },
];

const limitations = [
  "Cannot diagnose medical conditions under any circumstances",
  "Knowledge base may not include very recent medical research",
  "OCR accuracy depends on image quality and clarity",
  "May not account for individual patient-specific factors",
  "Drug interaction database is not exhaustive",
  "System is intended for educational use only, not clinical decision-making",
];

const ethics = [
  "All responses are designed for academic and educational assistance",
  "Emergency-related prompts encourage users to seek immediate professional help",
  "User data is not stored permanently after session-based processing",
  "The platform promotes doctor consultation for serious, urgent, or unclear conditions",
  "The system is built to support understanding, not replace healthcare professionals",
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function AboutPage() {
  return (
    <>
      <Navbar />

      <div style={{ paddingTop: "var(--nav-h, 68px)", background: "var(--white, #fff)", fontFamily: "var(--font, sans-serif)" }}>

        {/* ── HERO ── */}
        <section style={{
          padding: "80px 24px 72px",
          background: "linear-gradient(160deg, #f0f7ff 0%, #ffffff 50%, #f0fdfa 100%)",
          textAlign: "center",
        }}>
          <div style={{ maxWidth: 720, margin: "0 auto" }}>
            <div className="section-label" style={{ display: "inline-flex", marginBottom: 20 }}>
              🎓 Academic Project
            </div>
           <h1
              style={{
                fontFamily: "var(--font-display, 'DM Serif Display', serif)",
                fontSize: "clamp(32px, 5vw, 52px)",
                fontWeight: 400, // serif display fonts look better with normal weight
                color: "var(--gray-900, #111827)",
                lineHeight: 1.15,
                letterSpacing: "-0.01em",
                marginBottom: 20,
              }}
            >
              Making medical information{" "}
              <span
                style={{
                  fontStyle: "italic",
                  color: "var(--blue, #2563eb)",
                }}
              >
                easier to understand
              </span>{" "}
              with AI
            </h1>
            <p style={{ fontSize: 18, color: "var(--gray-500, #6b7280)", lineHeight: 1.7, marginBottom: 12 }}>
              MedInsight AI is an academic project that helps users explore symptoms, medicines, prescriptions,
              and lab reports through AI-powered medical information assistance.
            </p>
            <p style={{ fontSize: 15, color: "var(--gray-400, #9ca3af)", lineHeight: 1.7, marginBottom: 32 }}>
              Built with Next.js, FastAPI, OCR, RAG, FAISS, and Gemini API — designed to provide simple,
              structured, and educational responses from curated medical knowledge.
            </p>
            <div className="tech-badges">
              <span className="tech-badge nextjs">▲ Next.js</span>
              <span className="tech-badge fastapi">⚡ FastAPI</span>
              <span className="tech-badge rag">🔍 RAG</span>
              <span className="tech-badge faiss">📊 FAISS</span>
              <span className="tech-badge ocr">👁️ OCR</span>
              <span className="tech-badge python">✨ Gemini</span>
            </div>
          </div>
        </section>

        {/* ── WHAT IS MEDINSIGHT AI ── */}
        <section style={{ padding: "80px 24px", background: "var(--white, #fff)" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 48, alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--blue, #2563eb)", marginBottom: 12 }}>
                Overview
              </div>
              <h2 className="section-title" style={{ textAlign: "left", marginBottom: 20 }}>
                What is MedInsight AI?
              </h2>
              <p style={{ color: "var(--gray-500, #6b7280)", lineHeight: 1.75, marginBottom: 16 }}>
                MedInsight AI is an AI-powered medical information assistant created as an academic project.
                It allows users to ask symptom-related questions, look up medicine information, upload
                prescription images, and interpret lab reports in a more understandable way.
              </p>
              <p style={{ color: "var(--gray-500, #6b7280)", lineHeight: 1.75 }}>
                The system combines retrieval-based intelligence with language generation to produce
                educational medical guidance in a clear, accessible format — drawing from curated medical
                knowledge rather than unverified open-web sources.
              </p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              {[
                { label: "Symptom Q&A",       icon: "🩺" },
                { label: "Drug Information",        icon: "💊" },
                { label: "Prescription OCR",   icon: "📋" },
                { label: "Lab Reports",        icon: "🔬" },
              ].map((item) => (
                <div key={item.label} style={{
                  background: "var(--gray-50, #f9fafb)",
                  border: "1.5px solid var(--gray-200, #e5e7eb)",
                  borderRadius: "var(--radius-lg, 16px)",
                  padding: "28px 16px",
                  textAlign: "center",
                  transition: "border-color .2s, background .2s",
                  cursor: "default",
                }}>
                  <div style={{ fontSize: 36, marginBottom: 10 }}>{item.icon}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--gray-700, #374151)" }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── WHY + MISSION — dark navy ── */}
        <section style={{ padding: "80px 24px", background: "var(--gray-900, #111827)" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24 }}>
            {[
              {
                tag: "Origin",
                title: "Why this project was created",
                text: "Medical information is often difficult for everyday users to understand — especially when reading prescriptions, medicine names, or laboratory reports. Many people also struggle to find reliable basic health information quickly. MedInsight AI was created to simplify this by offering a user-friendly platform that turns complex medical data into structured, easy-to-read educational insights.",
              },
              {
                tag: "Mission",
                title: "Our mission",
                text: "To make essential medical information more accessible, understandable, and organized through AI. We aim to support users with educational guidance while maintaining clear safety boundaries — and always encouraging consultation with qualified healthcare professionals whenever a real clinical decision is involved.",
              },
            ].map((card) => (
              <div key={card.tag} style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "var(--radius-lg, 16px)",
                padding: 36,
              }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#22d3ee", marginBottom: 12 }}>
                  {card.tag}
                </div>
                <h2 style={{ fontSize: 22, fontWeight: 700, color: "#fff", marginBottom: 16, lineHeight: 1.35 }}>
                  {card.title}
                </h2>
                <p style={{ color: "var(--gray-400, #9ca3af)", lineHeight: 1.75, fontSize: 15 }}>
                  {card.text}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── HOW IT WORKS ── */}
        <section style={{ padding: "80px 24px", background: "var(--bg, #ffffff)" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto" }}>
            <div className="section-header" style={{ marginBottom: 52 }}>
              <div className="section-label">🔄 Process</div>
              <h2 className="section-title">How MedInsight AI works</h2>
              <p className="section-subtitle" style={{ margin: "0 auto" }}>
                A five-stage pipeline from user input to a safe, educational AI response.
              </p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 24 }}>
              {steps.map((step) => (
                <div key={step.num} style={{ textAlign: "center" }}>
                  <div style={{
                    width: 64, height: 64, borderRadius: "50%",
                    background: "var(--white, #fff)",
                    border: "2px solid #bfdbfe",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    margin: "0 auto 20px",
                    boxShadow: "0 2px 12px rgba(37,99,235,.1)",
                  }}>
                    <span style={{ fontSize: 15, fontWeight: 700, color: "var(--blue, #2563eb)" }}>{step.num}</span>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "var(--gray-900, #111827)", marginBottom: 8 }}>
                    {step.title}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--gray-500, #6b7280)", lineHeight: 1.6 }}>
                    {step.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── TECH STACK ── */}
        <section style={{ padding: "80px 24px", background: "var(--white, #fff)" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto" }}>
            <div className="section-header" style={{ marginBottom: 52 }}>
              <div className="section-label">🛠️ Stack</div>
              <h2 className="section-title">Technology stack</h2>
              <p className="section-subtitle" style={{ margin: "0 auto" }}>
                Each layer is chosen for its specific role in the medical information pipeline.
              </p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
              {techStack.map((tech) => (
                <div key={tech.name} style={{
                  display: "flex", alignItems: "flex-start", gap: 16,
                  border: "1.5px solid var(--gray-200, #e5e7eb)",
                  borderRadius: "var(--radius-lg, 16px)",
                  padding: "20px 22px",
                  background: "var(--white, #fff)",
                  transition: "border-color .2s",
                }}>
                  <span className={`tech-badge ${tech.badge}`} style={{ flexShrink: 0, marginTop: 2 }}>
                    {tech.tag}
                  </span>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "var(--gray-900, #111827)" }}>{tech.name}</div>
                    <div style={{ fontSize: 12, color: "var(--gray-500, #6b7280)", marginTop: 3 }}>{tech.role}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── OBJECTIVES — dark navy ── */}
        <section style={{ padding: "80px 24px", background: "var(--gray-900, #111827)" }}>
          <div style={{ maxWidth: 960, margin: "0 auto" }}>
            <div className="section-header" style={{ marginBottom: 48 }}>
              <div className="section-label" style={{ background: "rgba(34,211,238,0.15)", color: "#22d3ee" }}>🎯 Goals</div>
              <h2 className="section-title" style={{ color: "#fff" }}>Project objectives</h2>
              <p className="section-subtitle" style={{ margin: "0 auto", color: "var(--gray-400, #9ca3af)" }}>
                The goals that shaped every design and engineering decision in this project.
              </p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
              {objectives.map((obj, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "flex-start", gap: 12,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 12,
                  padding: "14px 18px",
                }}>
                  <span style={{ color: "#22d3ee", fontSize: 16, flexShrink: 0, marginTop: 2 }}>✓</span>
                  <span style={{ fontSize: 14, color: "#cbd5e1", lineHeight: 1.6 }}>{obj}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── SYSTEM FLOW ── */}
        <section style={{ padding: "80px 24px", background: "var(--bg, #f7f9fc)" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto" }}>
            <div className="section-header" style={{ marginBottom: 40 }}>
              <div className="section-label">🔄 Architecture</div>
              <h2 className="section-title">System flow</h2>
            </div>
            <div className="flow-diagram">
             <div className="flow-steps">
                {[
                  ["💬", "User Input"],
                  ["🧠", "Query or Image Processing"],
                  ["📄", "OCR Text Extraction"],
                  ["🔍", "Medical Context Retrieval"],
                  ["🤖", "LLM Generation"],
                  ["✅", "Final Analysis"],
                ].map(([icon, label], i, arr) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                    
                    {/* BOX */}
                    <div className="flow-step-box">
                      <div className="flow-step-icon">{icon}</div>
                      <div className="flow-step-name">{label}</div>
                    </div>

                    {/* ARROW */}
                    {i !== arr.length - 1 && (
                      <div className="flow-arrow">→</div>
                    )}

                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── ETHICS & LIMITATIONS ── */}
        <section style={{ padding: "80px 24px", background: "var(--white, #fff)" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto" }}>
            <div className="section-header" style={{ marginBottom: 48 }}>
              <div className="section-label">⚖️ Ethics & Limitations</div>
              <h2 className="section-title">Responsible AI in Healthcare</h2>
            </div>
            <div className="ethics-grid">
              <div className="ethics-card limitation">
                <div className="ethics-card-title">⚠️ Known Limitations</div>
                <ul className="ethics-list">
                  {limitations.map((l) => <li key={l}>{l}</li>)}
                </ul>
              </div>
              <div className="ethics-card ethics">
                <div className="ethics-card-title">🛡️ Ethical Commitments</div>
                <ul className="ethics-list">
                  {ethics.map((e) => <li key={e}>{e}</li>)}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ── SAFETY DISCLAIMER ── */}
        <section style={{ padding: "0 24px 80px", background: "var(--white, #fff)" }}>
          <div style={{ maxWidth: 900, margin: "0 auto" }}>
            <div style={{
              border: "1.5px solid #fde68a",
              background: "#fffbeb",
              borderRadius: "var(--radius-lg, 16px)",
              padding: "36px 40px",
            }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 20 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: "#fef3c7", color: "#d97706",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 20, flexShrink: 0,
                }}>⚠️</div>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#d97706", marginBottom: 6 }}>
                    Important Disclaimer
                  </div>
                  <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--gray-900, #111827)", lineHeight: 1.3 }}>
                    Safety, Limitations & Medical Disclaimer
                  </h2>
                </div>
              </div>
              <div style={{ fontSize: 14, color: "var(--gray-600, #4b5563)", lineHeight: 1.8 }}>
                <p style={{ marginBottom: 12 }}>
                  <strong style={{ color: "var(--gray-800, #1f2937)" }}>MedInsight AI is designed for academic and educational purposes only.</strong>{" "}
                  It does not provide medical diagnosis, treatment recommendations, prescriptions, or emergency medical care.
                </p>
                <p style={{ marginBottom: 12 }}>
                  While the system includes emergency keyword detection and confidence-aware response filtering,
                  it should never be used as a substitute for a qualified doctor or licensed healthcare professional.
                </p>
                <p>
                  In any serious, urgent, or unclear medical situation, please{" "}
                  <strong style={{ color: "var(--gray-800, #1f2937)" }}>immediately call 112 or contact emergency services and seek in-person professional medical help.</strong>
                </p>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 24, paddingTop: 20, borderTop: "1px solid #fde68a" }}>
                {["Not for clinical diagnosis", "Not for treatment decisions", "Emergency? Call 112", "Always consult a doctor"].map((tag) => (
                  <span key={tag} style={{
                    padding: "5px 14px", borderRadius: 999,
                    background: "#fef3c7", color: "#92400e",
                    fontSize: 12, fontWeight: 600,
                  }}>{tag}</span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── FUTURE SCOPE ── */}
        <section style={{ padding: "80px 24px", background: "var(--bg, #f7f9fc)" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto" }}>
            <div className="section-header" style={{ marginBottom: 52 }}>
              <div className="section-label">🚀 Roadmap</div>
              <h2 className="section-title">Future scope</h2>
              <p className="section-subtitle" style={{ margin: "0 auto" }}>
                Areas we plan to improve as the project grows beyond its academic phase.
              </p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 20 }}>
              {futureItems.map((item) => (
                <div key={item.title} style={{
                  background: "var(--white, #fff)",
                  border: "1.5px solid var(--gray-200, #e5e7eb)",
                  borderRadius: "var(--radius-lg, 16px)",
                  padding: 24,
                  transition: "border-color .2s, box-shadow .2s",
                }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: 8,
                    background: "var(--blue, #2563eb)", color: "#fff",
                    fontSize: 11, fontWeight: 700,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    marginBottom: 16,
                  }}>{item.num}</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "var(--gray-900, #111827)", marginBottom: 8 }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--gray-500, #6b7280)", lineHeight: 1.65 }}>
                    {item.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── TEAM ── */}
        <section style={{ padding: "80px 24px", background: "var(--white, #fff)" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto" }}>
            <div className="section-header" style={{ marginBottom: 52 }}>
              <div className="section-label">👥 Project Team</div>
              <h2 className="section-title">Built by students, for learning</h2>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 20 }}>
              {team.map((member) => (
                <div key={member.name} style={{
                  textAlign: "center",
                  padding: 28,
                  background: "var(--white, #fff)",
                  border: "1.5px solid var(--gray-200, #e5e7eb)",
                  borderRadius: "var(--radius-lg, 16px)",
                }}>
                  <div style={{ fontSize: 40, marginBottom: 14 }}>{member.icon}</div>
                  <div style={{ fontWeight: 700, color: "var(--gray-800, #1f2937)", fontSize: 15 }}>{member.name}</div>
                  <div style={{ fontSize: 13, color: "var(--gray-500, #6b7280)", marginTop: 4 }}>{member.role}</div>
                  {member.prn && (
                    <div style={{
                      display: "inline-block", marginTop: 10,
                      padding: "3px 12px", borderRadius: 999,
                      background: "var(--blue-pale, #eff6ff)", color: "var(--blue, #2563eb)",
                      fontSize: 11, fontWeight: 600,
                    }}>{member.prn}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CTA ── */}
        <section style={{ padding: "80px 24px", background: "var(--gray-900, #111827)", textAlign: "center" }}>
          <div style={{ maxWidth: 640, margin: "0 auto" }}>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              padding: "6px 16px", borderRadius: 999,
              background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)",
              color: "#22d3ee", fontSize: 11, fontWeight: 700,
              letterSpacing: "0.08em", textTransform: "uppercase",
              marginBottom: 24,
            }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#22d3ee" }} />
              Live Demo
            </div>
            <h2 style={{
              fontFamily: "var(--font-display, Georgia, serif)",
              fontSize: "clamp(26px, 4vw, 38px)",
              fontWeight: 700, color: "#fff",
              lineHeight: 1.2, marginBottom: 18,
            }}>
              Explore MedInsight AI in action
            </h2>
            <p style={{ fontSize: 16, color: "var(--gray-400, #9ca3af)", lineHeight: 1.7, marginBottom: 36 }}>
              Try the chatbot to explore symptoms, medicines, prescriptions, and lab reports through
              a simple AI-powered interface built for educational medical assistance.
            </p>
            <Link href="/chat" className="btn btn-primary btn-lg">
              💬 Try Chatbot →
            </Link>
            <p style={{ marginTop: 16, fontSize: 12, color: "var(--gray-500, #6b7280)" }}>
              Academic project · Educational use only · No data stored
            </p>
          </div>
        </section>

      </div>
    </>
  );
}
