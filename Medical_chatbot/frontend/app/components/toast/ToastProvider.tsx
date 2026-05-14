"use client";

import { ReactNode, useCallback, useMemo, useState } from "react";
import { ToastContext, ToastItem, ToastType } from "./useToast";

export default function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, type: ToastType = "") => {
    const id = crypto.randomUUID();
    setToasts((t) => [...t, { id, message, type }]);

    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 3500);
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-container" id="toastContainer">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            {(t.type === "success"
              ? "✅ "
              : t.type === "error"
              ? "❌ "
              : t.type === "warning"
              ? "⚠️ "
              : "ℹ️ ") + t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}