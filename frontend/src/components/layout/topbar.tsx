import { Search, Bell, Menu } from "lucide-react";

export function Topbar() {
  return (
    <header className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-4 sm:px-6 shrink-0">
      <div className="flex items-center gap-4 flex-1">
        <button className="md:hidden p-2 text-slate-500 hover:bg-slate-50 rounded-md transition-colors">
          <Menu className="h-5 w-5" />
        </button>
        <div className="relative w-full max-w-md hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search contracts, clauses, or analyses..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-slate-50 focus:bg-white"
          />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button className="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-full transition-colors hidden sm:block">
          <Search className="h-5 w-5" />
        </button>
        <button className="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-full transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-blue-600 border-2 border-white"></span>
        </button>
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center text-sm font-medium shadow-sm ml-2 cursor-pointer border border-blue-700">
          JD
        </div>
      </div>
    </header>
  );
}
