import type { Metadata } from "next";
import React from "react";

import { Navbar } from "@/components/layout/Navbar";
import { AuthProvider } from "@/components/providers/AuthProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "ApplyPilot AI — Local-First Application Assistant",
  description:
    "Complete internship, job, scholarship, and hackathon applications securely using local AI and explicit human approval.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen flex flex-col">
        <ThemeProvider>
          <AuthProvider>
            <Navbar />
            <main className="flex-1">{children}</main>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

