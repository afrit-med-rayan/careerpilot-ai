"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { authApi, resumeApi } from "@/lib/api";

// ── Auth Modal ────────────────────────────────────────────────────────────────
function AuthModal({
  onSuccess,
  onClose,
}: {
  onSuccess: (token: string) => void;
  onClose: () => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await authApi.register(email, password);
      }
      const { access_token } = await authApi.login(email, password);
      localStorage.setItem("cp_token", access_token);
      onSuccess(access_token);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">
          {mode === "login" ? "Welcome back" : "Create account"}
        </h2>
        <form onSubmit={submit} className="auth-form">
          <input
            className="input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <p className="error-msg">{error}</p>}
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Please wait…" : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>
        <p className="auth-switch">
          {mode === "login" ? "No account? " : "Already have one? "}
          <button
            className="link-btn"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
          >
            {mode === "login" ? "Register" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}

// ── Upload Zone ───────────────────────────────────────────────────────────────
function UploadZone({
  token,
  onUploaded,
}: {
  token: string;
  onUploaded: (id: string) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const handleFile = useCallback(
    async (file: File) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!["pdf", "docx", "doc"].includes(ext ?? "")) {
        setUploadError("Only PDF and DOCX files are supported.");
        return;
      }
      setUploading(true);
      setUploadError("");
      try {
        const result = await resumeApi.upload(file, token);
        onUploaded(result.resume_id);
      } catch (err: unknown) {
        setUploadError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [token, onUploaded]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div
      className={`upload-zone ${dragging ? "upload-zone--drag" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      {uploading ? (
        <div className="upload-state">
          <div className="spinner" />
          <p>Parsing your resume…</p>
        </div>
      ) : (
        <div className="upload-state">
          <div className="upload-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.338-2.32 5.75 5.75 0 0 1 1.18 11.095H6.75Z" />
            </svg>
          </div>
          <p className="upload-label">Drop your resume here</p>
          <p className="upload-sub">PDF or DOCX · up to 10 MB</p>
          <label className="btn-secondary" htmlFor="file-input">
            Browse files
          </label>
          <input
            id="file-input"
            type="file"
            accept=".pdf,.docx,.doc"
            className="hidden"
            onChange={onInputChange}
          />
        </div>
      )}
      {uploadError && <p className="error-msg mt-4">{uploadError}</p>}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function Home() {
  const router = useRouter();
  const [showAuth, setShowAuth] = useState(false);
  const [token, setToken] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem("cp_token") : null
  );

  const handleAuthSuccess = (t: string) => {
    setToken(t);
    setShowAuth(false);
  };

  const handleUploaded = (id: string) => {
    router.push(`/resume/${id}`);
  };

  return (
    <main className="page">
      {/* ── Navbar ── */}
      <nav className="navbar">
        <span className="logo">
          <span className="logo-accent">Career</span>Pilot
          <span className="logo-badge">AI</span>
        </span>
        {token ? (
          <div className="nav-actions">
            <button className="btn-ghost" onClick={() => router.push("/dashboard")}>
              Dashboard
            </button>
            <button
              className="btn-ghost"
              onClick={() => {
                localStorage.removeItem("cp_token");
                setToken(null);
              }}
            >
              Sign Out
            </button>
          </div>
        ) : (
          <button className="btn-ghost" onClick={() => setShowAuth(true)}>
            Sign In
          </button>
        )}
      </nav>

      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-glow hero-glow--left" />
        <div className="hero-glow hero-glow--right" />

        <div className="hero-content">
          <div className="badge">✦ AI-Powered Resume Intelligence</div>
          <h1 className="hero-title">
            Land your dream job<br />
            <span className="gradient-text">10× faster</span>
          </h1>
          <p className="hero-sub">
            Upload your resume. Get an instant ATS score, rewritten bullets,
            matched job postings, tailored cover letters, and a full interview
            prep — all in one place.
          </p>

          {/* Feature pills */}
          <div className="feature-pills">
            {[
              "ATS Scoring",
              "Bullet Rewrites",
              "Job Matching",
              "Cover Letters",
              "Interview Prep",
              "Skill Gap Analysis",
            ].map((f) => (
              <span key={f} className="pill">
                {f}
              </span>
            ))}
          </div>

          {/* Upload or CTA */}
          {token ? (
            <UploadZone token={token} onUploaded={handleUploaded} />
          ) : (
            <div className="cta-group">
              <button className="btn-primary btn-lg" onClick={() => setShowAuth(true)}>
                Get Started — It&apos;s Free
              </button>
              <p className="cta-hint">No credit card required</p>
            </div>
          )}
        </div>
      </section>

      {/* ── Stats ── */}
      <section className="stats-row">
        {[
          { label: "Resumes Analyzed", value: "12,000+" },
          { label: "ATS Pass Rate", value: "94%" },
          { label: "Job Matches / Resume", value: "50+" },
          { label: "Avg. Time Saved", value: "4 hrs" },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <p className="stat-value">{s.value}</p>
            <p className="stat-label">{s.label}</p>
          </div>
        ))}
      </section>

      {/* ── How it works ── */}
      <section className="steps">
        <h2 className="section-title">How it works</h2>
        <div className="steps-grid">
          {[
            { n: "01", title: "Upload", desc: "Drop your PDF or DOCX resume — we parse it instantly." },
            { n: "02", title: "Analyze", desc: "Get an ATS score and a detailed list of issues to fix." },
            { n: "03", title: "Rewrite", desc: "Let AI sharpen every weak bullet with measurable impact." },
            { n: "04", title: "Match & Apply", desc: "See ranked job matches and generate a cover letter in seconds." },
          ].map((step) => (
            <div key={step.n} className="step-card">
              <span className="step-number">{step.n}</span>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-desc">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="footer">
        <p>© 2026 CareerPilot AI · Built with ♥ and Claude</p>
      </footer>

      {/* ── Auth Modal ── */}
      {showAuth && (
        <AuthModal onSuccess={handleAuthSuccess} onClose={() => setShowAuth(false)} />
      )}
    </main>
  );
}
