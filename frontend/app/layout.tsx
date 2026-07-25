import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CareerPilot AI — AI-Powered Resume & Job Application Platform",
  description:
    "Upload your resume, get an ATS score, AI-rewritten bullets, job matches, tailored cover letters, interview prep, and skill-gap analysis — all in one place.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
