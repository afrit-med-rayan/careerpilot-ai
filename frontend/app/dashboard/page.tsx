"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { resumeApi, ResumeResponse } from "@/lib/api";

function atsBadgeClass(score: number | null) {
  if (score === null) return "ats-badge ats-badge--none";
  if (score >= 75) return "ats-badge ats-badge--high";
  if (score >= 50) return "ats-badge ats-badge--medium";
  return "ats-badge ats-badge--low";
}

export default function DashboardPage() {
  const router = useRouter();
  const [resumes, setResumes] = useState<ResumeResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("cp_token");
    if (!token) { router.replace("/"); return; }

    resumeApi
      .list(token)
      .then(setResumes)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <>
      {/* Reuse navbar */}
      <nav className="navbar">
        <Link href="/" className="logo" style={{ textDecoration: "none" }}>
          <span className="logo-accent">Career</span>Pilot
          <span className="logo-badge">AI</span>
        </Link>
        <div className="nav-actions">
          <Link href="/" className="btn-ghost">Upload New</Link>
          <button
            className="btn-ghost"
            onClick={() => { localStorage.removeItem("cp_token"); router.push("/"); }}
          >
            Sign Out
          </button>
        </div>
      </nav>

      <div className="dashboard-page">
        <div className="dashboard-header">
          <h1 className="dashboard-title">My Resumes</h1>
        </div>

        {loading && <div className="empty-state"><div className="spinner" style={{ margin: "0 auto" }} /></div>}
        {error && <p className="error-msg">{error}</p>}

        {!loading && !error && resumes.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">📄</div>
            <p>No resumes yet.</p>
            <Link href="/" className="btn-primary" style={{ marginTop: "1rem", display: "inline-flex" }}>
              Upload your first resume
            </Link>
          </div>
        )}

        <div className="resume-grid">
          {resumes.map((r) => (
            <Link key={r.id} href={`/resume/${r.id}`} className="resume-card">
              <div className="resume-card-info">
                <span className="resume-card-name">{r.original_filename}</span>
                <span className="resume-card-date">
                  {new Date(r.created_at).toLocaleDateString()}
                </span>
              </div>
              <span className={atsBadgeClass(r.ats_score)}>
                {r.ats_score !== null ? `ATS ${r.ats_score}` : "Not analyzed"}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
