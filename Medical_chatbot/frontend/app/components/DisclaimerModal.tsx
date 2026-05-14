"use client";

import { useState } from "react";

export default function DisclaimerModal() {
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    return !localStorage.getItem("medinsight_disclaimer_ok");
  });

  function close() {
    localStorage.setItem("medinsight_disclaimer_ok", "1");
    setOpen(false);
  }

  if (!open) return null;

  return (
    <div className="modal-backdrop" id="disclaimerModal">
      <div className="modal">
        <div className="modal-icon">Medical</div>
        <div className="modal-title">Academic Project Notice</div>
        <div className="modal-text">
          <strong>MedInsight AI is an academic project only.</strong> It does
          not provide medical diagnosis, replace professional healthcare advice,
          or guarantee accuracy of any information.
          <br />
          <br />
          Always consult a <strong>qualified medical professional</strong> for
          health decisions. In emergencies, call <strong>112 / 911</strong>{" "}
          immediately.
        </div>
        <div className="modal-actions">
          <button className="btn btn-primary btn-lg" onClick={close}>
            I Understand - Continue
          </button>
          <button className="btn btn-ghost" onClick={close}>
            Read Full Disclaimer
          </button>
        </div>
      </div>
    </div>
  );
}
