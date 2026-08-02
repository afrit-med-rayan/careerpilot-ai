"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  resumeApi,
  ResumeResponse,
  RewriteItem,
  JobMatchItem,
  InterviewQuestionItem,
  SkillGapResponse,
} from "@/lib/api";

type Tab = "parsed" | "analysis" | "rewrite" | "matches" | "generation" | "raw";

export default function ResumeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [resume, setResume] = useState<ResumeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("parsed");
  const [analyzing, setAnalyzing] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [jobDescription, setJobDescription] = useState("");
  const [rewrites, setRewrites] = useState<RewriteItem[]>([]);
  const [jobQuery, setJobQuery] = useState("");
  const [jobLocation, setJobLocation] = useState("");
  const [jobMatches, setJobMatches] = useState<JobMatchItem[]>([]);
  const [matchingJobs, setMatchingJobs] = useState(false);

  // Generation tab states
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [coverTone, setCoverTone] = useState<"formal" | "conversational" | "enthusiastic">("formal");
  const [coverLetter, setCoverLetter] = useState<string>("");
  const [generatingCover, setGeneratingCover] = useState(false);
  const [interviewQuestions, setInterviewQuestions] = useState<InterviewQuestionItem[]>([]);
  const [generatingInterview, setGeneratingInterview] = useState(false);
  const [skillGap, setSkillGap] = useState<SkillGapResponse | null>(null);
  const [loadingSkillGap, setLoadingSkillGap] = useState(false);

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

  const handleRewrite = async () => {
    const token = localStorage.getItem("cp_token");
    if (!token) return;
    setRewriting(true);
    setError("");
    try {
      const res = await resumeApi.rewrite(id, jobDescription, token);
      setRewrites(res.rewrites);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRewriting(false);
    }
  };

  const handleMatchJobs = async () => {
    const token = localStorage.getItem("cp_token");
    if (!token) return;
    if (!jobQuery.strip && !jobQuery) return;
    setMatchingJobs(true);
    setError("");
    try {
      const res = await resumeApi.matchJobs(id, jobQuery, jobLocation, token);
      setJobMatches(res.matches);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setMatchingJobs(false);
    }
  };

  const handleGenerateCoverLetter = async () => {
    const token = localStorage.getItem("cp_token");
    if (!token) return;
    setGeneratingCover(true);
    setError("");
    try {
      const res = await resumeApi.generateCoverLetter(id, coverTone, selectedJobId || undefined, token);
      setCoverLetter(res.cover_letter);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGeneratingCover(false);
    }
  };

  const handleGenerateInterviewQuestions = async () => {
    const token = localStorage.getItem("cp_token");
    if (!token) return;
    setGeneratingInterview(true);
    setError("");
    try {
      const res = await resumeApi.generateInterviewQuestions(id, selectedJobId || undefined, token);
      setInterviewQuestions(res.questions);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGeneratingInterview(false);
    }
  };

  const handleFetchSkillGap = async () => {
    const token = localStorage.getItem("cp_token");
    if (!token) return;
    setLoadingSkillGap(true);
    setError("");
    try {
      const res = await resumeApi.getSkillGap(id, selectedJobId || undefined, token);
      setSkillGap(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingSkillGap(false);
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
          {(["parsed", "analysis", "rewrite", "matches", "generation", "raw"] as Tab[]).map((t) => (
            <button
              key={t}
              className={`tab ${activeTab === t ? "tab--active" : ""}`}
              onClick={() => setActiveTab(t)}
            >
              {t === "parsed"
                ? "Parsed View"
                : t === "analysis"
                ? "Analysis"
                : t === "rewrite"
                ? "Rewrite"
                : t === "matches"
                ? "Job Matches"
                : t === "generation"
                ? "Cover Letter & Prep"
                : "Raw Text"}
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

        {/* Generation & Intelligence (Phase 5) */}
        {activeTab === "generation" && (
          <div className="parsed-section">
            <p className="parsed-section-title">Cover Letter, Interview Coach & Skill Gap Intelligence</p>

            {/* Target Job Selection */}
            {jobMatches.length > 0 && (
              <div className="parsed-card" style={{ marginBottom: "1.5rem" }}>
                <label style={{ display: "block", marginBottom: "0.4rem", fontWeight: 600 }}>
                  Target Matched Job Context (Optional)
                </label>
                <select
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.6rem 0.8rem",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border)",
                    background: "var(--bg)",
                    color: "var(--text)",
                    fontSize: "0.9rem",
                  }}
                >
                  <option value="">-- General / No Specific Job Selected --</option>
                  {jobMatches.map((j) => (
                    <option key={j.job_id} value={j.job_id}>
                      {j.title} at {j.company} ({Math.round(j.similarity_score * 100)}% match)
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* 1. Cover Letter Generator */}
            <div className="parsed-card" style={{ marginBottom: "1.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ margin: 0, fontSize: "1.1rem" }}>✉️ Tailored Cover Letter Generator</h3>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <label style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Tone:</label>
                  <select
                    value={coverTone}
                    onChange={(e) => setCoverTone(e.target.value as any)}
                    style={{
                      padding: "0.3rem 0.6rem",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border)",
                      background: "var(--bg)",
                      color: "var(--text)",
                      fontSize: "0.85rem",
                    }}
                  >
                    <option value="formal">Formal</option>
                    <option value="conversational">Conversational</option>
                    <option value="enthusiastic">Enthusiastic</option>
                  </select>
                  <button
                    className="btn-primary"
                    onClick={handleGenerateCoverLetter}
                    disabled={generatingCover}
                    style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}
                  >
                    {generatingCover ? "Drafting..." : "Generate Cover Letter"}
                  </button>
                </div>
              </div>

              {generatingCover ? (
                <div className="empty-state">
                  <div className="spinner" style={{ margin: "0 auto" }} />
                  <p style={{ marginTop: "0.75rem" }}>Drafting tailored cover letter...</p>
                </div>
              ) : coverLetter ? (
                <div style={{ background: "var(--bg)", padding: "1rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                  <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: "0.92rem", lineHeight: 1.6, margin: 0 }}>
                    {coverLetter}
                  </pre>
                </div>
              ) : (
                <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", margin: 0 }}>
                  Select your desired tone and click "Generate Cover Letter" to produce an application letter.
                </p>
              )}
            </div>

            {/* 2. Interview Prep Coach */}
            <div className="parsed-card" style={{ marginBottom: "1.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ margin: 0, fontSize: "1.1rem" }}>🎯 Tailored Interview Preparation Coach</h3>
                <button
                  className="btn-primary"
                  onClick={handleGenerateInterviewQuestions}
                  disabled={generatingInterview}
                  style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}
                >
                  {generatingInterview ? "Generating Questions..." : "Generate Interview Q&A"}
                </button>
              </div>

              {generatingInterview ? (
                <div className="empty-state">
                  <div className="spinner" style={{ margin: "0 auto" }} />
                  <p style={{ marginTop: "0.75rem" }}>Synthesizing technical and behavioral interview scenarios...</p>
                </div>
              ) : interviewQuestions.length > 0 ? (
                <div style={{ display: "grid", gap: "1rem" }}>
                  {interviewQuestions.map((q, idx) => (
                    <div key={idx} style={{ background: "var(--bg)", padding: "0.85rem 1rem", borderRadius: "var(--radius-sm)", borderLeft: "3px solid var(--accent)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.3rem" }}>
                        <span className="pill" style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem", textTransform: "capitalize" }}>
                          {q.type}
                        </span>
                        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Question #{idx + 1}</span>
                      </div>
                      <p style={{ fontSize: "0.98rem", fontWeight: 600, margin: "0.4rem 0 0.5rem 0" }}>{q.question}</p>
                      <div style={{ fontSize: "0.88rem", color: "var(--text-muted)", background: "rgba(255, 255, 255, 0.03)", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)" }}>
                        💡 <strong>Suggested Answer Strategy:</strong> {q.suggested_answer_notes}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", margin: 0 }}>
                  Click "Generate Interview Q&A" to get customized technical and STAR behavioral interview scenarios.
                </p>
              )}
            </div>

            {/* 3. Skill Gap Analysis */}
            <div className="parsed-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ margin: 0, fontSize: "1.1rem" }}>📊 Skill Gap & Qualification Analysis</h3>
                <button
                  className="btn-primary"
                  onClick={handleFetchSkillGap}
                  disabled={loadingSkillGap}
                  style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}
                >
                  {loadingSkillGap ? "Analyzing Skills..." : "Analyze Skill Gap"}
                </button>
              </div>

              {loadingSkillGap ? (
                <div className="empty-state">
                  <div className="spinner" style={{ margin: "0 auto" }} />
                  <p style={{ marginTop: "0.75rem" }}>Comparing candidate skill vectors against target job requirements...</p>
                </div>
              ) : skillGap ? (
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.25rem" }}>
                    <div style={{ fontSize: "2rem", fontWeight: 800, color: skillGap.match_percentage >= 75 ? "var(--success)" : "var(--warning)" }}>
                      {skillGap.match_percentage}%
                    </div>
                    <div>
                      <strong style={{ display: "block" }}>Skill Coverage Score</strong>
                      <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                        {skillGap.matched_skills.length} matched · {skillGap.missing_skills.length} missing
                      </span>
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                    <div>
                      <h4 style={{ color: "var(--success)", fontSize: "0.95rem", marginBottom: "0.5rem" }}>
                        ✓ Matched Skills ({skillGap.matched_skills.length})
                      </h4>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                        {skillGap.matched_skills.map((s, idx) => (
                          <span key={idx} className="pill" style={{ background: "rgba(34, 197, 94, 0.15)", color: "#22c55e", fontSize: "0.8rem" }}>
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 style={{ color: "var(--warning)", fontSize: "0.95rem", marginBottom: "0.5rem" }}>
                        ⚠ Missing / Suggested Skills ({skillGap.missing_skills.length})
                      </h4>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                        {skillGap.missing_skills.map((s, idx) => (
                          <span key={idx} className="pill" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b", fontSize: "0.8rem" }}>
                            + {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", margin: 0 }}>
                  Click "Analyze Skill Gap" to view your matched skills vs. missing requirements.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Job Matches */}
        {activeTab === "matches" && (
          <div className="parsed-section">
            <p className="parsed-section-title">AI Vector Job Search & Match Engine</p>

            <div className="parsed-card" style={{ marginBottom: "1.5rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
                <div>
                  <label style={{ display: "block", marginBottom: "0.4rem", fontWeight: 600 }}>Job Role / Keywords *</label>
                  <input
                    type="text"
                    value={jobQuery}
                    onChange={(e) => setJobQuery(e.target.value)}
                    placeholder="e.g. Software Engineer, Full Stack, Data Scientist"
                    style={{
                      width: "100%",
                      padding: "0.6rem 0.8rem",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border)",
                      background: "var(--bg)",
                      color: "var(--text)",
                      fontSize: "0.9rem",
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", marginBottom: "0.4rem", fontWeight: 600 }}>Location (Optional)</label>
                  <input
                    type="text"
                    value={jobLocation}
                    onChange={(e) => setJobLocation(e.target.value)}
                    placeholder="e.g. Remote, San Francisco, London"
                    style={{
                      width: "100%",
                      padding: "0.6rem 0.8rem",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border)",
                      background: "var(--bg)",
                      color: "var(--text)",
                      fontSize: "0.9rem",
                    }}
                  />
                </div>
              </div>
              <button
                className="btn-primary"
                onClick={handleMatchJobs}
                disabled={matchingJobs || !jobQuery.trim()}
              >
                {matchingJobs ? "Matching Vector Embeddings..." : "Find Ranked Job Matches"}
              </button>
            </div>

            {matchingJobs ? (
              <div className="empty-state">
                <div className="spinner" style={{ margin: "0 auto" }} />
                <p style={{ marginTop: "1rem" }}>Fetching live job postings & calculating vector similarity...</p>
              </div>
            ) : jobMatches.length > 0 ? (
              <div style={{ display: "grid", gap: "1.25rem" }}>
                <h3 style={{ marginBottom: "0.5rem" }}>Ranked Opportunities ({jobMatches.length})</h3>
                {jobMatches.map((job) => {
                  const percent = Math.round(job.similarity_score * 100);
                  const badgeColor = percent >= 75 ? "var(--success)" : percent >= 50 ? "var(--warning)" : "var(--text-muted)";
                  return (
                    <div key={job.job_id} className="parsed-card">
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                        <div>
                          <h4 style={{ fontSize: "1.1rem", margin: 0 }}>{job.title}</h4>
                          <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", margin: "0.2rem 0 0 0" }}>
                            {job.company} · {job.location || "Remote"}
                          </p>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <span
                            className="pill"
                            style={{
                              background: "rgba(99, 102, 241, 0.15)",
                              color: badgeColor,
                              fontWeight: 700,
                              fontSize: "0.9rem",
                              padding: "0.25rem 0.6rem",
                            }}
                          >
                            {percent}% Match
                          </span>
                          <span style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem", textTransform: "uppercase" }}>
                            {job.source}
                          </span>
                        </div>
                      </div>

                      <p style={{ fontSize: "0.88rem", color: "var(--text-muted)", margin: "0.75rem 0 1rem 0", lineHeight: 1.5 }}>
                        {job.description}
                      </p>

                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-ghost"
                        style={{ display: "inline-block", fontSize: "0.85rem", textDecoration: "none" }}
                      >
                        View & Apply on {job.source.toUpperCase()} →
                      </a>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <p>Enter a job title or role keyword above to trigger real-time job ingestion and vector matching.</p>
              </div>
            )}
          </div>
        )}

        {/* Rewrite */}
        {activeTab === "rewrite" && (
          <div className="parsed-section">
            <p className="parsed-section-title">AI Bullet Point & Summary Rewriter</p>

            <div className="parsed-card" style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: 600 }}>
                Target Job Description (Optional)
              </label>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the target job description here to tailor bullet point rewrites directly to job keywords..."
                rows={4}
                style={{
                  width: "100%",
                  padding: "0.75rem",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border)",
                  background: "var(--bg)",
                  color: "var(--text)",
                  marginBottom: "1rem",
                  fontFamily: "inherit",
                  fontSize: "0.9rem",
                }}
              />
              <button
                className="btn-primary"
                onClick={handleRewrite}
                disabled={rewriting || !resume.parsed_json}
              >
                {rewriting ? "Generating Rewrites..." : "Generate High-Impact Rewrites"}
              </button>
            </div>

            {rewriting ? (
              <div className="empty-state">
                <div className="spinner" style={{ margin: "0 auto" }} />
                <p style={{ marginTop: "1rem" }}>Crafting STAR-format bullet point rewrites...</p>
              </div>
            ) : rewrites.length > 0 ? (
              <div style={{ display: "grid", gap: "1.5rem" }}>
                <h3 style={{ marginBottom: "0.5rem" }}>Suggested Bullet Point Improvements ({rewrites.length})</h3>
                {rewrites.map((item, idx) => (
                  <div key={idx} className="parsed-card">
                    <div style={{ marginBottom: "0.75rem" }}>
                      <span className="pill" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", marginBottom: "0.3rem", display: "inline-block" }}>
                        Original
                      </span>
                      <p style={{ fontSize: "0.95rem", color: "var(--text-muted)", textDecoration: "line-through" }}>
                        {item.original}
                      </p>
                    </div>

                    <div style={{ marginBottom: "0.75rem" }}>
                      <span className="pill" style={{ background: "rgba(34, 197, 94, 0.15)", color: "#22c55e", marginBottom: "0.3rem", display: "inline-block" }}>
                        AI Rewritten
                      </span>
                      <p style={{ fontSize: "1rem", fontWeight: 500, color: "var(--text)" }}>
                        {item.rewritten}
                      </p>
                    </div>

                    <div style={{ background: "var(--bg)", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                      💡 <strong>Why:</strong> {item.reason}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <p>Click "Generate High-Impact Rewrites" to transform weak bullets into STAR-format achievements.</p>
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
