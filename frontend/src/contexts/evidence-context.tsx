"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

export interface EvidenceItem {
  id: string;
  agent?: string;      // e.g., "Risk Analysis"
  finding?: string;    // e.g., "Termination Exposure"
  severity?: string;   // e.g., "High Risk"
  explanation?: string;// e.g., "Why this matters"
  page: string;        // e.g., "Page 8"
  section: string;     // e.g., "Section 11.1"
  sourceText: string;  // e.g., "Exact source text..."
  matchScore?: number;
  highlight?: string;
}

interface EvidenceContextType {
  evidence: EvidenceItem[];
  setEvidence: (evidence: EvidenceItem[]) => void;
  sourceType: string;
  setSourceType: (type: string) => void;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  clearEvidence: () => void;
}

export const EvidenceContext = createContext<EvidenceContextType | undefined>(undefined);

export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [sourceType, setSourceType] = useState("Agent Retrieval");
  const [isOpen, setIsOpen] = useState(false);

  const clearEvidence = () => {
    setEvidence([]);
    setIsOpen(false);
  };

  return (
    <EvidenceContext.Provider
      value={{
        evidence,
        setEvidence,
        sourceType,
        setSourceType,
        isOpen,
        setIsOpen,
        clearEvidence,
      }}
    >
      {children}
    </EvidenceContext.Provider>
  );
}

export function useEvidence() {
  const context = useContext(EvidenceContext);
  if (context === undefined) {
    throw new Error("useEvidence must be used within an EvidenceProvider");
  }
  return context;
}
