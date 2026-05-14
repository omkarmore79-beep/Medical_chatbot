"use client";

import Link from "next/link";
import { useState } from "react";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  const isHome = pathname === "/";

  function close() {
    setOpen(false);
  }

  return (
    <>
      <nav className="navbar">
        <div className="nav-inner">
          <Link className="nav-logo" href="/" onClick={close}>
            <div className="nav-logo-icon">🩺</div>
            MedInsight AI 
          </Link>

          <div className="nav-links">
            <Link className="nav-link" href={isHome ? "#features" : "/#features"}>
              Features
            </Link>
            <Link
              className="nav-link"
              href={isHome ? "#how-it-works" : "/#how-it-works"}
            >
              How It Works
            </Link>
            <Link className="nav-link" href={isHome ? "#faq" : "/#faq"}>
              FAQ
            </Link>
            <Link className="nav-link" href="/about">
              About
            </Link>
          </div>

          <Link className="nav-cta" href="/chat" onClick={close}>
            Try Chatbot →
          </Link>

          <button
            className="nav-hamburger"
            onClick={() => setOpen((v) => !v)}
            aria-label="Open menu"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
      </nav>

      {open && (
        <div className="nav-mobile" id="mobileMenu">
          <Link className="nav-link" href="/#features" onClick={close}>
            Features
          </Link>
          <Link className="nav-link" href="/#how-it-works" onClick={close}>
            How It Works
          </Link>
          <Link className="nav-link" href="/#faq" onClick={close}>
            FAQ
          </Link>
          <Link className="nav-link" href="/about" onClick={close}>
            About
          </Link>
          <Link className="nav-link" href="/upload" onClick={close}>
            Upload Prescription
          </Link>
          <Link className="nav-cta" href="/chat" onClick={close}>
            Try Chatbot →
          </Link>
        </div>
      )}
    </>
  );
}