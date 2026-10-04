import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Providers from "@/src/components/providers";
import { ThemeProvider, THEME_INIT_SCRIPT } from "@/src/components/theme-provider";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LegalGPT",
  description: "Explainable multi-agent contract intelligence",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {/* Seed the light/dark theme before first paint (no flash, no React script node). */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <ThemeProvider>
          <Providers>{children}</Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
