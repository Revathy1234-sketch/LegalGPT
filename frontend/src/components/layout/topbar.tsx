"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Bell, Menu, FileText, Scale, Loader2, Moon, Sun } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useTheme } from "@/src/components/theme-provider";
import { searchApi } from "@/src/lib/api/search";
import { usersApi } from "@/src/lib/api/users";
import { useRouter } from "next/navigation";

export function Topbar() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { theme, setTheme } = useTheme();

  // Debounce the query
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data: results, isLoading } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchApi.query(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });

  const { data: currentUser } = useQuery({
    queryKey: ['user', 'me'],
    queryFn: () => usersApi.getMe(),
  });

  const initials = currentUser?.full_name
    ? currentUser.full_name
        .split(' ')
        .map((n: string) => n[0])
        .join('')
        .substring(0, 2)
        .toUpperCase()
    : 'U';

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    router.push('/login');
  };

  return (
    <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between px-4 sm:px-6 shrink-0 relative">
      <div className="flex items-center gap-4 flex-1">
        <button className="md:hidden p-2 text-slate-700/60 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-md transition-colors">
          <Menu className="h-5 w-5" />
        </button>
        <div className="relative w-full max-w-md hidden sm:block" ref={dropdownRef}>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-700/40" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="Search contracts, clauses, or analyses..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 dark:border-slate-700 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:bg-white dark:focus:bg-slate-900"
          />

          {/* Search Dropdown */}
          {isOpen && debouncedQuery.length >= 2 && (
            <div className="absolute top-full left-0 w-[500px] mt-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md shadow-lg overflow-hidden z-50">
              {isLoading ? (
                <div className="flex items-center justify-center p-4 text-slate-700/60 dark:text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  <span className="text-sm">Searching...</span>
                </div>
              ) : results && results.length > 0 ? (
                <div className="max-h-[400px] overflow-y-auto p-2">
                  {results.map((group) => (
                    <div key={group.group} className="mb-2 last:mb-0">
                      <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider px-2 py-1 bg-slate-50 dark:bg-slate-800 border-b border-slate-100 dark:border-slate-700 mb-1 rounded">
                        {group.group}
                      </div>
                      {group.items.map((result) => (
                        <div
                          key={result.id}
                          className="p-2 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer rounded-md transition-colors"
                          onClick={() => {
                            setIsOpen(false);
                            router.push(result.link || `/contracts/${result.contract_id}`);
                          }}
                        >
                          <div className="flex items-start gap-3">
                            <div className="mt-0.5 p-1.5 rounded-md bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
                              {result.type === 'contract' ? <FileText className="h-4 w-4" /> : <Scale className="h-4 w-4" />}
                            </div>
                            <div>
                              <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{result.title}</p>
                              <p className="text-xs text-slate-700/60 dark:text-slate-400 mt-0.5 truncate max-w-[400px]">{result.subtitle}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-sm text-slate-700/60 dark:text-slate-400">
                  No results found for &quot;{debouncedQuery}&quot;
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button className="relative p-2 text-slate-700/60 hover:text-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-full transition-colors hidden sm:block">
          <Search className="h-5 w-5" />
        </button>
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="relative p-2 text-slate-700/60 hover:text-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 dark:hover:text-slate-300 rounded-full transition-colors"
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100 top-2 left-2" />
          <span className="sr-only">Toggle theme</span>
        </button>
        <button className="relative p-2 text-slate-700/60 hover:text-slate-700 hover:bg-slate-50 rounded-full transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-blue-600 border-2 border-white"></span>
        </button>
        <div className="relative" ref={userMenuRef}>
          <div
            className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center text-sm font-medium shadow-sm ml-2 cursor-pointer border border-blue-700"
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
          >
            {initials}
          </div>

          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-md shadow-lg py-1 z-50">
              <div className="px-4 py-2 border-b border-slate-100">
                <p className="text-sm font-medium text-slate-900 truncate">
                  {currentUser?.full_name || 'User'}
                </p>
                <p className="text-xs text-slate-700/60 truncate">
                  {currentUser?.email || ''}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-rose-600 hover:bg-slate-50 transition-colors"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
