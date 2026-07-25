"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { resumeApi, ResumeResponse } from "@/lib/api";

type Tab = "parsed" | "raw";

export default function ResumeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [resume, setResume] = useState<ResumeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("parsed");

  useEffect(() => {
    const token = localStorage.getItem("cp_token");
    if (!token) { router.replace("/"); return; }

    resumeApi
      .get(id, token)
      .then(setResume)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
      <div className="spinner" />
    </div>
  );
  if (error) return <div className="detail-page"><p className="error-msg">{error}</p></div>;
  if (!resume) return null;

  const parsed = resume.parsed_json as Record<string, unknown> | null;

  return (
    <>
      <nav className="navbar">
        <Link href="/" className="logo" style={{ textDecoration: "none" }}>
          <span className="logo-accent">Career</span>Pilot
          <span className="logo-badge">AI</span>
        </Link>
        <Link href="/dashboard" className="btn-ghost">← Dashboard</Link>
      </nav>

      <div className="detail-page">
        <div className="detail-header">
          <h1 className="detail-filename">{resume.original_filename}</h1>
          <p className="detail-meta">
            Uploaded {new Date(resume.created_at).toLocaleString()}
            {resume.ats_score !== null && ` · ATS Score: ${resume.ats_score}/100`}
          </p>
        </div>

        {/* Tabs */}
        <div className="tabs">
          {(["parsed", "raw"] as Tab[]).map((t) => (
            <button
              key={t}
              className={`tab ${activeTab === t ? "tab--active" : ""}`}
              onClick={() => setActiveTab(t)}
            >
              {t === "parsed" ? "Parsed View" : "Raw Text"}
            </button>
          ))}
          {/* Phase 2+ tabs — disabled for now */}
          {(["Analysis", "Rewrite", "Job Matches"] as string[]).map((label) => (
            <button key={label} className="tab" disabled title="Coming in Phase 2+">
              {label}
            </button>
          ))}
        </div>

        {/* Parsed View */}
        {activeTab === "parsed" && (
          <div>
            {parsed ? (
              <>
                {/* Contact */}
                {parsed.contact && (
                  <div className="parsed-section">
                    <p className="parsed-section-title">Contact</p>
                    <div className="parsed-card">
                      {Object.entries(parsed.contact as Record<string, string>).map(([k, v]) =>
                        v ? <p key={k}><strong>{k}:</strong> {v}</p> : null
                      )}
                    </div>
                  </div>
                )}

                {/* Summary */}
                {parsed.summary && (
                  <div className="parsed-section">
                    <p className="parsed-section-title">Summary</p>
                    <div className="parsed-card"><p>{parsed.summary as string}</p></div>
                  </div>
                )}

                {/* Experience */}
                {Array.isArray(parsed.experience) && (parsed.experience as unknown[]).length > 0 && (
                  <div className="parsed-section">
                    <p className="parsed-section-title">Experience</p>
                    {(parsed.experience as Record<string, unknown>[]).map((exp, i) => (
                      <div key={i} className="parsed-card" style={{ marginBottom: "0.75rem" }}>
                        <p style={{ fontWeight: 600 }}>{exp.title as string} @ {exp.company as string}</p>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                          {exp.start_date as string} – {exp.end_date as string}
                        </p>
                        {Array.isArray(exp.bullets) && (
                          <ul style={{ marginTop: "0.5rem", paddingLeft: "1.2rem" }}>
                            {(exp.bullets as string[]).map((b, j) => <li key={j} style={{ color: "var(--text-muted)", fontSize: "0.88rem" }}>{b}</li>)}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Skills */}
                {Array.isArray(parsed.skills) && (parsed.skills as unknown[]).length > 0 && (
                  <div className="parsed-section">
                    <p className="parsed-section-title">Skills</p>
                    <div className="parsed-card">
                      <div className="feature-pills" style={{ justifyContent: "flex-start" }}>
                        {(parsed.skills as string[]).map((s) => (
                          <span key={s} className="pill">{s}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🤖</div>
                <p>LLM segmentation not yet run — available in Phase 2.</p>
              </div>
            )}
          </div>
        )}

        {/* Raw Text */}
        {activeTab === "raw" && (
          <div className="parsed-section">
            <p className="parsed-section-title">Raw extracted text</p>
            <div className="parsed-card">
              {resume.raw_text ? (
                <pre className="raw-text">{resume.raw_text}</pre>
              ) : (
                <p className="error-msg">No text extracted. This file may require OCR.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
