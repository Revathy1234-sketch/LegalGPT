"use client";

import React, { useContext } from "react";
import { FileSearch, PanelRightClose } from "lucide-react";
import { EvidenceContext } from "@/src/contexts/evidence-context";

/**
 * Global floating Evidence toggle (rules 4 & 10).
 *
 * - Click → opens the Evidence Panel showing the proof for whichever agent
 *   last populated it (the context keeps the items after closing).
 * - Click the panel's X (or this button again) → closes it.
 * - Click this button a third time → reopens the SAME agent's evidence proof.
 *
 * Renders nothing when the page has no EvidenceProvider (login, settings…).
 */
export function EvidenceToggle() {
  const ctx = useContext(EvidenceContext);
  if (!ctx) return null;

  const { isOpen, setIsOpen, evidence } = ctx;
  const count = evidence.length;

  return (
    <button
      type="button"
      onClick={() => setIsOpen(!isOpen)}
      aria-label={isOpen ? "Close evidence panel" : "Open evidence panel"}
      aria-pressed={isOpen}
      className={`fixed bottom-5 right-5 z-[60] flex items-center gap-2 px-4 py-3 rounded-full shadow-lg border transition-all duration-200 outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
        isOpen
          ? "bg-slate-900 text-white border-slate-700 hover:bg-slate-800"
          : "bg-white text-slate-700 border-slate-200 hover:border-blue-300 hover:text-blue-600"
      }`}
      title={isOpen ? "Hide evidence panel" : "Show evidence panel"}
    >
      {isOpen ? (
        <PanelRightClose className="h-5 w-5" />
      ) : (
        <FileSearch className="h-5 w-5" />
      )}
      <span className="text-sm font-semibold hidden sm:inline">
        {isOpen ? "Hide evidence" : "Evidence"}
      </span>
      {!isOpen && count > 0 && (
        <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-blue-600 text-white text-[11px] font-bold">
          {count}
        </span>
      )}
    </button>
  );
}
