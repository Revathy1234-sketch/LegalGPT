"use client";

import Link from "next/link";
import { LayoutDashboard, FileText, Bot, History, Settings, HelpCircle, User, Gauge, Sparkles } from "lucide-react";
import { usePathname } from "next/navigation";

export function Sidebar() {
  const pathname = usePathname() || '';

  const getLinkClass = (path: string, exact: boolean = false) => {
    const isActive = exact ? pathname === path : pathname.startsWith(path);
    return `flex items-center gap-3 px-3 py-2.5 rounded-md font-medium text-sm transition-colors ${
      isActive
        ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600/90 dark:text-blue-400"
        : "text-slate-700/80 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100"
    }`;
  };

  return (
    <aside className="w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex-col hidden md:flex h-full shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-slate-200 dark:border-slate-800 shrink-0">
        <Bot className="h-6 w-6 text-blue-600 mr-2" />
        <span className="font-bold text-lg text-slate-900 dark:text-white tracking-tight">LegalGPT</span>
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
        <Link href="/overview" className={getLinkClass("/overview")}>
          <Gauge className="h-4 w-4" />
          Contract Overview
        </Link>
        <Link href="/agents" className={getLinkClass("/agents")}>
          <Sparkles className="h-4 w-4" />
          Agent Workspace
        </Link>
        <Link href="/workspace" className={getLinkClass("/workspace")}>
          <Bot className="h-4 w-4" />
          AI Workspace
        </Link>

        <div className="my-2 border-t border-slate-100 dark:border-slate-800" />

        <Link href="/history" className={getLinkClass("/history")}>
          <History className="h-4 w-4" />
          Analysis History
        </Link>

        <div className="my-2 border-t border-slate-100 dark:border-slate-800" />

        <Link href="/settings" className={getLinkClass("/settings")}>
          <Settings className="h-4 w-4" />
          Settings
        </Link>
      </div>

      <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-1 shrink-0">
        <button className="flex items-center gap-3 px-3 py-2.5 rounded-md text-slate-700/80 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100 font-medium text-sm w-full text-left transition-colors">
          <HelpCircle className="h-4 w-4" />
          Help
        </button>
        <button className="flex items-center gap-3 px-3 py-2.5 rounded-md text-slate-700/80 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100 font-medium text-sm w-full text-left transition-colors">
          <User className="h-4 w-4" />
          User Profile
        </button>
      </div>
    </aside>
  );
}
