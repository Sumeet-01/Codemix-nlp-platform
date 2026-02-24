import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "@/styles/globals.css";
import { Providers } from "@/components/providers";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "CodeMix NLP - Sarcasm & Misinformation Detection",
    template: "%s | CodeMix NLP",
  },
  description:
    "Production-grade NLP platform for detecting misinformation and sarcasm in Indian code-mixed text (Hinglish, Tanglish) using XLM-RoBERTa.",
  keywords: [
    "NLP",
    "sarcasm detection",
    "misinformation",
    "Hinglish",
    "code-mixed",
    "XLM-RoBERTa",
    "machine learning",
  ],
  authors: [{ name: "CodeMix NLP Team" }],
  creator: "CodeMix NLP",
  openGraph: {
    type: "website",
    locale: "en_US",
    title: "CodeMix NLP Platform",
    description: "Detect sarcasm and misinformation in Indian code-mixed text",
    siteName: "CodeMix NLP",
  },
  twitter: {
    card: "summary_large_image",
    title: "CodeMix NLP Platform",
    description: "Detect sarcasm and misinformation in Indian code-mixed text",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  themeColor: "#000000",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head />
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
