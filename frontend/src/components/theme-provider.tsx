"use client";

import * as React from "react";

/**
 * Whole-project theme provider (rules 1 & 3).
 *
 * Replaces `next-themes`: that library renders an inline <script> inside the
 * React tree, which React 19 rejects with "Encountered a script tag while
 * rendering React component". This implementation seeds the theme with a tiny
 * inline script placed directly in the root layout (outside the React render
 * of this provider) and reads the value through useSyncExternalStore — no
 * setState-in-effect, no hydration mismatch, no flash of the wrong theme.
 *
 * Theme lives in a `.dark` class on <html>; src/styles/theme.css defines the
 * palettes + remaps that make every page follow it.
 */

export type Theme = "light" | "dark";

const STORAGE_KEY = "legalgpt-theme";

type ThemeContextValue = {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
};
const ThemeContext = React.createContext<ThemeContextValue | undefined>(undefined);

/** Runs in <head>/early body via app/layout.tsx — keeps theme before paint. */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("${STORAGE_KEY}");if(t!=="dark"&&t!=="light"){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}if(t==="dark"){document.documentElement.classList.add("dark");}document.documentElement.style.colorScheme=t;}catch(e){}})();`;

function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

function applyThemeToDom(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
}

// External-store plumbing: localStorage-backed, notifies React subscribers.
const listeners = new Set<() => void>();
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
function emitChange() {
  listeners.forEach((l) => l());
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = React.useSyncExternalStore(subscribe, readStoredTheme, () => "light" as Theme);

  // Keep the DOM in sync with the store (external system update — allowed in effects).
  React.useEffect(() => {
    applyThemeToDom(theme);
  }, [theme]);

  const setTheme = React.useCallback((next: Theme) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* storage may be unavailable */
    }
    applyThemeToDom(next);
    emitChange();
  }, []);

  const toggleTheme = React.useCallback(() => {
    setTheme(readStoredTheme() === "dark" ? "light" : "dark");
  }, [setTheme]);

  const value = React.useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) {
    // Graceful fallback so components outside the provider still work.
    return { theme: "light" as Theme, setTheme: () => {}, toggleTheme: () => {} };
  }
  return ctx;
}
