"use client";

import Link from "next/link";

export default function Footer() {
  return (
    <footer>
      <div className="footer-inner">
        <div className="footer-top">
          <div>
            <div className="footer-logo">
              <div className="nav-logo-icon" style={{ width: 32, height: 32 }}>
                🩺
              </div>
              MedInsight AI 
            </div>
            <p className="footer-desc">
              An academic project exploring AI-powered medical information assistance.  
              Built with Next.js, FastAPI, OCR, RAG, and FAISS.  
              For educational use only, not for clinical decision-making.
            </p>
          </div>

          <div>
            <div className="footer-col-title">Navigate</div>
            <ul className="footer-links">
              <li>
                <Link href="/">Home</Link>
              </li>
              <li>
                <Link href="/#features">Features</Link>
              </li>
              <li>
                <Link href="/#how-it-works">How It Works</Link>
              </li>
              <li>
                <Link href="/#faq">FAQ</Link>
              </li>
            </ul>
          </div>

          <div>
            <div className="footer-col-title">App</div>
            <ul className="footer-links">
              <li>
                <Link href="/chat">Medical Chatbot</Link>
              </li>
              <li>
                <Link href="/upload">Upload Medical Documents</Link>
              </li>
              <li>
                <Link href="/about">About MedInsight AI</Link>
              </li>
            </ul>
          </div>

        </div>

        <div className="footer-bottom">
          <div className="footer-disclaimer">
            ⚠️ <strong>Medical Disclaimer:</strong> MedInsight AI is for academic and educational purposes only. It does not provide medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional for any medical concern
          </div>
          <div className="footer-copy">© 2026 MedInsight AI  · Academic Project</div>
        </div>
      </div>
    </footer>
  );
}