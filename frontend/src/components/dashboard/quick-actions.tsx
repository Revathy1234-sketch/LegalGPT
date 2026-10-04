import Link from "next/link";
import { Upload, Bot, Scale, GitCompare } from "lucide-react";

const ACTIONS = [
  { href: "/contracts/upload", label: "Upload Contract", icon: Upload },
  { href: "/workspace", label: "Ask LegalGPT", icon: Bot },
  { href: "/overview", label: "Analyze Contract", icon: Scale },
  { href: "/agents", label: "Compare Contracts", icon: GitCompare },
];

export function QuickActions() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {ACTIONS.map((action) => (
        <Link
          key={action.label}
          href={action.href}
          className="flex flex-col items-center justify-center p-5 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all group outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <div className="p-3 bg-blue-50/80 text-blue-600 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors mb-3">
            <action.icon className="h-6 w-6" />
          </div>
          <span className="font-medium text-slate-900 text-sm sm:text-base">{action.label}</span>
        </Link>
      ))}
    </div>
  );
}
