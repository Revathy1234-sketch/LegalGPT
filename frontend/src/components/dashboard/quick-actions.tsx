import { Upload, Bot, Scale, GitCompare } from "lucide-react";

export function QuickActions() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <button className="flex flex-col items-center justify-center p-6 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all group outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        <div className="p-3 bg-blue-50/80 text-blue-600 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors mb-3">
          <Upload className="h-6 w-6" />
        </div>
        <span className="font-medium text-slate-900 text-sm sm:text-base">Upload Contract</span>
      </button>
      <button className="flex flex-col items-center justify-center p-6 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all group outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        <div className="p-3 bg-blue-50/80 text-blue-600 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors mb-3">
          <Bot className="h-6 w-6" />
        </div>
        <span className="font-medium text-slate-900 text-sm sm:text-base">Ask LegalGPT</span>
      </button>
      <button className="flex flex-col items-center justify-center p-6 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all group outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        <div className="p-3 bg-blue-50/80 text-blue-600 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors mb-3">
          <Scale className="h-6 w-6" />
        </div>
        <span className="font-medium text-slate-900 text-sm sm:text-base">Analyze Contract</span>
      </button>
      <button className="flex flex-col items-center justify-center p-6 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all group outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        <div className="p-3 bg-blue-50/80 text-blue-600 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors mb-3">
          <GitCompare className="h-6 w-6" />
        </div>
        <span className="font-medium text-slate-900 text-sm sm:text-base">Compare Contracts</span>
      </button>
    </div>
  );
}
