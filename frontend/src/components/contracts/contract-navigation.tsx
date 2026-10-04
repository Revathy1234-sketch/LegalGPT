"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  List,
  AlertTriangle,
  ShieldCheck,
  Scale,
  GitCompare,
  Network
} from "lucide-react";

interface ContractNavigationProps {
  contractId: string;
}

export function ContractNavigation({ contractId }: ContractNavigationProps) {
  const pathname = usePathname();
  const baseUrl = `/contracts/${contractId}`;

  const navItems = [
    { name: "Overview", href: baseUrl, icon: LayoutDashboard, exact: true },
    { name: "AI Chat", href: `${baseUrl}/chat`, icon: MessageSquare },
    { name: "Summary", href: `${baseUrl}/summary`, icon: FileText },
    { name: "Clauses", href: `${baseUrl}/clauses`, icon: List },
    { name: "Risk Analysis", href: `${baseUrl}/risk`, icon: AlertTriangle },
    { name: "Compliance", href: `${baseUrl}/compliance`, icon: ShieldCheck },
    { name: "Negotiation", href: `${baseUrl}/negotiation`, icon: Scale },
    { name: "Compare", href: `${baseUrl}/compare`, icon: GitCompare },
    { name: "Knowledge Graph", href: `${baseUrl}/knowledge-graph`, icon: Network },
  ];

  return (
    <nav className="p-3 space-y-1">
      <div className="px-3 mb-2">
        <h3 className="text-xs font-semibold text-slate-700/40 uppercase tracking-wider">Analysis Tools</h3>
      </div>
      {navItems.map((item) => {
        const isActive = item.exact ? pathname === item.href : pathname.startsWith(item.href);
        return (
          <Link
            key={item.name}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              isActive
                ? "bg-white text-blue-600 shadow-sm border border-slate-200"
                : "text-slate-700/80 hover:bg-slate-200/50 hover:text-slate-900 border border-transparent"
            }`}
          >
            <item.icon className={`h-4 w-4 ${isActive ? "text-blue-600" : "text-slate-700/40"}`} />
            {item.name}
          </Link>
        );
      })}
    </nav>
  );
}
