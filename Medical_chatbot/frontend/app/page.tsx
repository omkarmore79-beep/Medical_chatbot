import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import DisclaimerModal from "./components/DisclaimerModal";

export default function HomePage() {
  return (
    <>
      <Navbar />
      <DisclaimerModal />

      {/* Hero */}
      <section className="hero" id="hero">
        <div className="hero-inner">
          <div className="hero-content">
            <div className="hero-badge">
              <span className="hero-badge-dot"></span>
              Academic Research Project · 2026
            </div>

            <h1 className="hero-title">
              AI-Powered Medical 
              <br />
              <span>Research</span>{" "}
              Assistant
            </h1>

            <p className="hero-subtitle">
              Analyze symptoms, medications, prescriptions, and lab & radiology reports with AI — built for academic research and learning, not clinical diagnosis or emergency use.
            </p>

            <div className="hero-actions">
              <a className="btn btn-primary btn-lg" href="/chat">
                💬 Start Chat
              </a>
              <a className="btn btn-secondary btn-lg" href="/upload">
                📄 Upload Medical Documents
              </a>
            </div>

          </div>

          {/* Right chat preview */}
          <div className="hero-visual">
            <div className="chat-preview">
              <div className="chat-preview-header">
                <div className="chat-preview-avatar">🩺</div>
                <div className="chat-preview-info">
                  <div className="chat-preview-name">MedInsight AI </div>
                  <div className="chat-preview-status">
                    <span className="status-dot"></span> Online · Academic Mode
                  </div>
                </div>
              </div>

              <div className="chat-preview-body">
                <div className="msg user">
                  <div className="msg-bubble">
                    I have a mild headache and fatigue for 2 days. What could it
                    be?
                  </div>
                </div>

                <div className="msg ai">
                  <div className="msg-avatar">🤖</div>
                  <div>
                    <div className="msg-bubble">
                      Common causes of headache + fatigue include dehydration,
                      tension, poor sleep, or mild viral illness. For persistent
                      symptoms, please consult a doctor.
                    </div>
                    <div
                      style={{
                        marginTop: 6,
                        display: "flex",
                        gap: 4,
                        flexWrap: "wrap",
                      }}
                    >
                      <span className="source-chip" style={{ fontSize: 11 }}>
                        MedlinePlus
                      </span>
                      <span className="source-chip" style={{ fontSize: 11 }}>
                        WebMD
                      </span>
                    </div>
                  </div>
                </div>

                <div className="msg ai">
                  <div className="msg-avatar">🤖</div>
                  <div className="typing-indicator">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                  </div>
                </div>
              </div>

              <div className="chat-preview-input">
                <input
                  className="chat-preview-input-field"
                  placeholder="Ask about symptoms, drugs…"
                  readOnly
                />
                <button className="chat-send-btn">➤</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Row */}
      <div className="trust-row">
        <div className="trust-row-inner">
          <div className="trust-item">
            <span className="trust-item-icon">🎓</span> Academic Research Project
          </div>
          <div className="trust-div"></div>
          <div className="trust-item">
            <span className="trust-item-icon">🚫</span> Not for Medical
            Emergencies
          </div>
          <div className="trust-div"></div>
          <div className="trust-item">
            <span className="trust-item-icon">🩺</span> No Clinical Diagnosis
          </div>
          <div className="trust-div"></div>
          <div className="trust-item">
            <span className="trust-item-icon">🔒</span> Privacy-Aware Design
          </div>
          <div className="trust-div"></div>
          <div className="trust-item">
            <span className="trust-item-icon">📚</span> RAG-Powered Responses
          </div>
        </div>
      </div>

      {/* Features */}
      <section className="section" id="features">
        <div className="container">
          <div className="section-header">
            <div className="section-label">✨ Features</div>
            <h2 className="section-title">
              Everything you need to explore 
              <br />
              medical information easily
            </h2>
            <p className="section-subtitle">
              Built with RAG, FAISS vector search, and OCR to provide fast, educational medical assistance.
            </p>
          </div>

          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon blue">🩺</div>
              <div className="feature-title">Symptom Guidance</div>
              <div className="feature-desc">
                Describe your symptoms and get simple, educational insights about possible causes — based on trusted medical sources.
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-icon teal">💊</div>
              <div className="feature-title">Drug Information</div>
              <div className="feature-desc">
                Search any medicine and understand its uses, how it works, common side effects, and basic precautions in clear language.
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-icon amber">📑</div>
              <div className="feature-title">Lab Report Interpretation</div>
              <div className="feature-desc">
                Upload a lab report and get detected test values, abnormal results, and simple educational explanations.
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-icon green">📋</div>
              <div className="feature-title">Prescription Analysis</div>
              <div className="feature-desc">
                Upload a prescription image and the system will extract medicine names and explain them in a structured way.
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-icon blue">⚡</div>
              <div className="feature-title">Fast RAG Responses</div>
              <div className="feature-desc">
                Get quick and relevant answers using retrieval-augmented generation built on trusted medical datasets.
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-icon purple">🔒</div>
              <div className="feature-title">Safety-Focused Design</div>
              <div className="feature-desc">
                Includes emergency detection, confidence checks, and educational-only responses for safer guidance.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="section hiw-section" id="how-it-works">
        <div className="container">
          <div className="section-header">
            <div className="section-label">🔍 How It Works</div>
            <h2 className="hiw-main-title">
              From your question to
              <br />
              informed guidance
            </h2>
          </div>

          <div className="hiw-steps">
            <div className="hiw-step">
              <div className="hiw-step-num">💬</div>
              <div className="hiw-step-title">Ask Your Question</div>
              <div className="hiw-step-desc">
                Type symptoms, medicine names, or upload a prescription or lab report in simple language.
              </div>
            </div>

            <div className="hiw-step">
              <div className="hiw-step-num">🔍</div>
              <div className="hiw-step-title">AI Retrieves Info</div>
              <div className="hiw-step-desc">
               RAG + FAISS searches the medical knowledge base and finds the most relevant context for your query..
              </div>
            </div>

            <div className="hiw-step">
              <div className="hiw-step-num">🛡️</div>
              <div className="hiw-step-title">Safety Guidance</div>
              <div className="hiw-step-desc">
                Safety-Focused Response
                The system applies emergency detection, confidence checks, and educational safeguards before returning an answer.
              </div>
            </div>

            <div className="hiw-step">
              <div className="hiw-step-num">👨‍⚕️</div>
              <div className="hiw-step-title">Consult a Doctor</div>
              <div className="hiw-step-desc">
                For any serious symptoms, abnormal reports, or treatment decisions, professional medical advice is always recommended.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="section" id="testimonials">
        <div className="container">
          <div className="section-header">
            <div className="section-label">💬 Testimonials</div>
            <h2 className="section-title">What students & researchers say</h2>
          </div>

          <div className="testimonials-grid">
            <div className="testimonial-card">
              <div className="testimonial-stars">★★★★★</div>
              <div className="testimonial-text">
                &quot;Very easy to use. It helped me quickly understand medicine
                details and saved me time during study.&quot;
              </div>
              <div className="testimonial-author">
                <div
                  className="author-avatar"
                  style={{
                    background: "linear-gradient(135deg, #667eea, #764ba2)",
                  }}
                >
                  R
                </div>
                <div>
                  <div className="author-name">Rohit Yadav</div>
                  <div className="author-role">Student</div>
                </div>
              </div>
            </div>

            <div className="testimonial-card">
              <div className="testimonial-stars">★★★★★</div>
              <div className="testimonial-text">
                &quot;The platform is clear and helpful. I liked how fast it showed
                useful medical information in one place.&quot;
              </div>
              <div className="testimonial-author">
                <div
                  className="author-avatar"
                  style={{
                    background: "linear-gradient(135deg, #f093fb, #f5576c)",
                  }}
                >
                  S
                </div>
                <div>
                  <div className="author-name">Sumant Panchanahally</div>
                  <div className="author-role">Student</div>
                </div>
              </div>
            </div>

            <div className="testimonial-card">
              <div className="testimonial-stars">★★★★☆</div>
              <div className="testimonial-text">
                &quot;Simple, clean, and easy to understand. It made finding the
                right information much easier for me.&quot;
              </div>
              <div className="testimonial-author">
                <div
                  className="author-avatar"
                  style={{
                    background: "linear-gradient(135deg, #4facfe, #00f2fe)",
                  }}
                >
                  P
                </div>
                <div>
                  <div className="author-name">Mrs.Purva D. Thakare</div>
                  <div className="author-role">Project Supervisor</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ (accordion) */}
      <FAQSection />

      <Footer />
    </>
  );
}

function FAQSection() {
  // small client-like behavior without "use client" by using details tags
  // But to keep EXACT open/close behavior, we should do client state.
  // We'll do that with a nested client component:
  return <FAQClient />;
}

import FAQClient from "./parts/FAQClient";
