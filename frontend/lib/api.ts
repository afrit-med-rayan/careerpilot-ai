const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
}

export interface ResumeUploadResponse {
  resume_id: string;
  original_filename: string;
  raw_text_preview: string;
  ocr_required: boolean;
  message: string;
}

export interface AnalysisIssue {
  section: string;
  type: string;
  detail: string;
  location_hint: string | null;
}

export interface ResumeAnalysis {
  ats_score: number;
  issues: AnalysisIssue[];
}

export interface RewriteItem {
  original: string;
  rewritten: string;
  reason: string;
}

export interface RewriteResponse {
  rewrites: RewriteItem[];
}

export interface JobMatchItem {
  job_id: string;
  external_id: string;
  source: string;
  title: string;
  company: string;
  description: string;
  location: string | null;
  url: string;
  similarity_score: number;
}

export interface MatchJobsResponse {
  matches: JobMatchItem[];
}

export interface CoverLetterResponse {
  cover_letter: string;
}

export interface InterviewQuestionItem {
  question: string;
  type: "technical" | "behavioral";
  suggested_answer_notes: string;
}

export interface InterviewQuestionsResponse {
  questions: InterviewQuestionItem[];
}

export interface SkillGapResponse {
  matched_skills: string[];
  missing_skills: string[];
  match_percentage: number;
}

export interface ResumeResponse {
  id: string;
  user_id: string;
  file_url: string;
  original_filename: string;
  raw_text: string | null;
  parsed_json: Record<string, unknown> | null;
  ats_score: number | null;
  analysis_report: ResumeAnalysis | null;
  created_at: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: HeadersInit = {
    ...(options.headers ?? {}),
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }

  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (email: string, password: string) =>
    request<UserResponse>("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),
};

// ── Resumes ───────────────────────────────────────────────────────────────────

export const resumeApi = {
  upload: (file: File, token: string) => {
    const form = new FormData();
    form.append("file", file);
    return request<ResumeUploadResponse>("/api/resumes/upload", {
      method: "POST",
      body: form,
    }, token);
  },

  list: (token: string) =>
    request<ResumeResponse[]>("/api/resumes/", {}, token),

  get: (id: string, token: string) =>
    request<ResumeResponse>(`/api/resumes/${id}`, {}, token),
    
  analyze: (id: string, token: string) =>
    request<ResumeAnalysis>(`/api/resumes/${id}/analyze`, {
      method: "POST",
    }, token),

  rewrite: (id: string, jobDescription: string | undefined, token: string) =>
    request<RewriteResponse>(`/api/resumes/${id}/rewrite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_description: jobDescription || null }),
    }, token),

  matchJobs: (id: string, query: string, location: string | undefined, token: string) =>
    request<MatchJobsResponse>(`/api/resumes/${id}/match-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, location: location || null }),
    }, token),

  generateCoverLetter: (id: string, tone: "formal" | "conversational" | "enthusiastic", jobId: string | undefined, token: string) => {
    const q = jobId ? `?job_id=${jobId}` : "";
    return request<CoverLetterResponse>(`/api/resumes/${id}/cover-letter${q}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tone }),
    }, token);
  },

  generateInterviewQuestions: (id: string, jobId: string | undefined, token: string) => {
    const q = jobId ? `?job_id=${jobId}` : "";
    return request<InterviewQuestionsResponse>(`/api/resumes/${id}/interview-questions${q}`, {
      method: "POST",
    }, token);
  },

  getSkillGap: (id: string, jobId: string | undefined, token: string) => {
    const q = jobId ? `?job_id=${jobId}` : "";
    return request<SkillGapResponse>(`/api/resumes/${id}/skill-gap${q}`, {}, token);
  },
};
