"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { resumeApi, ResumeResponse } from "@/lib/api";

type Tab = "parsed" | "raw" | "analysis";

export default function ResumeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [resume, setResume] = useState<ResumeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("parsed");
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("cp_token");
    if (!token) { router.replace("/"); return; }

    resumeApi
      .get(id, token)
      .then(setResume)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, router]);

  const handleAnalyze = async () => {
    const token = localStorage.getItem("cp_token");
    if (!token) return;
    setAnalyzing(true);
    setError("");
    try {
      const report = await resumeApi.analyze(id, token);
      setResume((prev) => prev ? { ...prev, ats_score: report.ats_score, analysis_report: report } : null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  };

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
          {(["parsed", "analysis", "raw"] as Tab[]).map((t) => (
            <button
              key={t}
              className={`tab ${activeTab === t ? "tab--active" : ""}`}
              onClick={() => setActiveTab(t)}
            >
              {t === "parsed" ? "Parsed View" : t === "analysis" ? "Analysis" : "Raw Text"}
            </button>
          ))}
          {/* Phase 3+ tabs — disabled for now */}
          {(["Rewrite", "Job Matches"] as string[]).map((label) => (
            <button key={label} className="tab" disabled title="Coming in Phase 3+">
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

        {/* Analysis */}
        {activeTab === "analysis" && (
          <div className="parsed-section">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <p className="parsed-section-title" style={{ marginBottom: 0 }}>Resume Analysis</p>
              {!resume.analysis_report && resume.parsed_json && (
                <button className="btn-primary" onClick={handleAnalyze} disabled={analyzing}>
                  {analyzing ? "Analyzing..." : "Run Analysis"}
                </button>
              )}
            </div>
            
            {!resume.parsed_json ? (
              <div className="empty-state">
                <p>Please wait for parsing to complete before analyzing.</p>
              </div>
            ) : !resume.analysis_report && !analyzing ? (
              <div className="empty-state">
                <p>Run analysis to get your ATS score and actionable feedback.</p>
              </div>
            ) : analyzing ? (
              <div className="empty-state">
                <div className="spinner" style={{ margin: "0 auto" }} />
                <p style={{ marginTop: "1rem" }}>Analyzing your resume...</p>
              </div>
            ) : resume.analysis_report ? (
              <>
                <div className="parsed-card" style={{ marginBottom: "2rem", textAlign: "center" }}>
                  <h3 style={{ fontSize: "1.2rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>ATS Score</h3>
                  <div style={{ fontSize: "3rem", fontWeight: "800", color: resume.ats_score! >= 75 ? "var(--success)" : resume.ats_score! >= 50 ? "var(--warning)" : "var(--error)" }}>
                    {resume.ats_score} <span style={{ fontSize: "1.2rem", color: "var(--text-muted)" }}>/ 100</span>
                  </div>
                </div>
                
                <h3 style={{ marginBottom: "1rem" }}>Issues Identified ({resume.analysis_report.issues.length})</h3>
                <div style={{ display: "grid", gap: "1rem" }}>
                  {resume.analysis_report.issues.map((issue, idx) => (
                    <div key={idx} className="parsed-card" style={{ borderLeft: "4px solid var(--warning)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                        <strong style={{ color: "var(--text)", textTransform: "capitalize" }}>{issue.section}</strong>
                        <span className="pill" style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }}>{issue.type.replace("_", " ")}</span>
                      </div>
                      <p style={{ fontSize: "0.95rem", marginBottom: issue.location_hint ? "0.75rem" : "0" }}>{issue.detail}</p>
                      {issue.location_hint && (
                        <div style={{ background: "var(--bg)", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", fontSize: "0.85rem", color: "var(--text-muted)", fontStyle: "italic", borderLeft: "2px solid var(--border)" }}>
                          "{issue.location_hint}"
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : null}
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
