import { createContext, useContext } from "react";

export type ToastType = "success" | "error" | "warning" | "";

export type ToastItem = {
  id: string;
  message: string;
  type: ToastType;
};

export type ToastContextValue = {
  showToast: (message: string, type?: ToastType) => void;
};

export const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return ctx;
}