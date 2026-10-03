"use client";

import Link from "next/link";
import { LayoutDashboard, FileText, Bot, History, Settings, HelpCircle, User } from "lucide-react";
import { usePathname } from "next/navigation";

export function Sidebar() {
  const pathname = usePathname() || '';

  const getLinkClass = (path: string, exact: boolean = false) => {
    const isActive = exact ? pathname === path : pathname.startsWith(path);
    return `flex items-center gap-3 px-3 py-2.5 rounded-md font-medium text-sm transition-colors ${
      isActive
        ? "bg-blue-50 text-blue-700"
        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
    }`;
  };

  return (
    <aside className="w-64 border-r border-slate-200 bg-white flex-col hidden md:flex h-full shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-slate-200 shrink-0">
        <Bot className="h-6 w-6 text-blue-600 mr-2" />
        <span className="font-bold text-lg text-slate-900 tracking-tight">LegalGPT</span>
      </div>

      <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-1 px-3">
        <Link href="/" className={getLinkClass("/", true)}>
          <LayoutDashboard className="h-4 w-4" />
          Dashboard
        </Link>
        <Link href="/contracts" className={getLinkClass("/contracts")}>
          <FileText className="h-4 w-4" />
          Contracts
        </Link>
        <Link href="/workspace" className={getLinkClass("/workspace")}>
          <Bot className="h-4 w-4" />
          AI Workspace
        </Link>

        <div className="my-2 border-t border-slate-100" />

        <Link href="/history" className={getLinkClass("/history")}>
          <History className="h-4 w-4" />
          Analysis History
        </Link>

        <div className="my-2 border-t border-slate-100" />

        <Link href="/settings" className={getLinkClass("/settings")}>
          <Settings className="h-4 w-4" />
          Settings
        </Link>
      </div>

      <div className="p-4 border-t border-slate-200 flex flex-col gap-1 shrink-0">
        <button className="flex items-center gap-3 px-3 py-2.5 rounded-md text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium text-sm w-full text-left transition-colors">
          <HelpCircle className="h-4 w-4" />
          Help
        </button>
        <button className="flex items-center gap-3 px-3 py-2.5 rounded-md text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium text-sm w-full text-left transition-colors">
          <User className="h-4 w-4" />
          User Profile
        </button>
      </div>
    </aside>
  );
}
