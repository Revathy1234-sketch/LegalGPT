"use client";

import { use } from "react";
import { ContractOverviewView } from "@/src/components/contracts/contract-overview-view";

export default function ContractOverview({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  return <ContractOverviewView contractId={resolvedParams.id} />;
}
