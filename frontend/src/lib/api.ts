export interface UserRead {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  csrf_token: string;
  user: UserRead;
}

export interface OllamaHealth {
  provider: string;
  base_url: string;
  configured_model: string;
  fallback_model: string;
  status: "reachable" | "unreachable";
  model_available: boolean;
  available_models: string[];
  detail: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  app_name: string;
  environment: string;
  database: "ok" | "error";
  ollama: OllamaHealth;
}

export interface UserProfile {
  id: string;
  user_id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  college: string | null;
  degree: string | null;
  branch: string | null;
  current_semester: string | null;
  graduation_year: string | null;
  cgpa: string | null;
  school_education: Record<string, string>;
  technical_skills: string[];
  programming_languages: string[];
  projects: Array<Record<string, string>>;
  work_experience: Array<Record<string, string>>;
  internships: Array<Record<string, string>>;
  certifications: Array<Record<string, string>>;
  achievements: string[];
  github_url: string | null;
  linkedin_url: string | null;
  portfolio_url: string | null;
  preferred_roles: string[];
  preferred_locations: string[];
  work_mode_preference: string | null;
  internship_duration: string | null;
  availability: string | null;
  preferred_resume_id: string | null;
  team_name: string | null;
  team_members: string[];
  hackathon_project_idea: string | null;
  hackathon_tech_stack: string[];
  hackathon_repo_url: string | null;
  hackathon_project_description: string | null;
  verified_fields: Record<string, boolean>;
  created_at: string;
  updated_at: string;
}

export interface ResumeRead {
  id: string;
  user_id: string;
  label: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  extracted_text: string;
  extracted_data_json: Record<string, unknown>;
  is_verified: boolean;
  is_preferred: boolean;
  created_at: string;
}

export interface DetectedField {
  field_id: string;
  tag: string;
  input_type: string;
  name: string;
  element_id: string;
  label: string;
  placeholder: string;
  nearby_text: string;
  required: boolean;
  options: string[];
  selector: string;
  current_value: string;
}

export interface DraftMatch {
  field_id: string;
  suggested_profile_key: string | null;
  proposed_value: string;
  confidence_score: number;
  source: "deterministic" | "semantic" | "ollama" | "unmatched";
  reason: string;
  requires_human_review: boolean;
  missing_profile_data: boolean;
  is_ai_draft: boolean;
}

export interface ApprovalSnapshotRead {
  id: string;
  target_url: string;
  resume_id: string | null;
  resume_sha256: string | null;
  approved_values_json: Record<string, string>;
  form_structure_hash: string;
  snapshot_hash: string;
  is_consumed: boolean;
  approved_at: string;
  consumed_at: string | null;
}

export interface StateTransitionRead {
  id: string;
  from_status: string | null;
  to_status: string;
  reason: string;
  created_at: string;
}

export interface ApplicationRead {
  id: string;
  user_id: string;
  resume_id: string | null;
  target_url: string;
  application_type: string;
  title: string | null;
  company_or_org: string | null;
  status: string;
  detected_fields_json: DetectedField[];
  draft_matches_json: DraftMatch[];
  edited_values_json: Record<string, string>;
  validation_warnings_json: string[];
  missing_fields_json: string[];
  has_draft_screenshot: boolean;
  has_confirmation_screenshot: boolean;
  confirmation_reference: string | null;
  confirmation_evidence_json: Record<string, unknown> | null;
  error_message: string | null;
  ai_provider_used: string | null;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  transitions: StateTransitionRead[];
  latest_approval: ApprovalSnapshotRead | null;
}

export interface ApplicationStatsRead {
  total: number;
  drafts: number;
  awaiting_review: number;
  submitted: number;
  failed: number;
  unknown: number;
  cancelled: number;
}

export interface SettingsRead {
  preferred_ollama_model: string | null;
  default_ollama_model: string;
  fallback_ollama_model: string;
  ollama_base_url: string;
  allow_localhost_automation: boolean;
  plan_tier: string;
  usage_summary: Record<string, number>;
}

export interface AuditLogRead {
  id: string;
  event_type: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  details_json: Record<string, unknown>;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const API_BASE =
  process.env.NEXT_PUBLIC_USE_DIRECT_API === "true" && process.env.NEXT_PUBLIC_API_URL
    ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "")}/api/v1`
    : "/api/v1";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (first && typeof first === "object" && "msg" in first) {
      return String((first as { msg: unknown }).msg);
    }
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers);
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrf = readCookie("applypilot_csrf");
    if (csrf && !headers.has("X-CSRF-Token")) {
      headers.set("X-CSRF-Token", csrf);
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = null;
    }
  }

  if (!res.ok) {
    throw new ApiError(
      extractErrorMessage(parsed, `Request failed with status ${res.status}`),
      res.status
    );
  }
  return parsed as T;
}

async function ensureCsrfCookie(): Promise<void> {
  if (!readCookie("applypilot_csrf")) {
    await request<{ csrf_token: string }>("/auth/csrf");
  }
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  register: (payload: { email: string; full_name: string; password: string }) =>
    request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  logout: async () => {
    await ensureCsrfCookie();
    return request<{ message: string }>("/auth/logout", { method: "POST" });
  },
  me: () => request<UserRead>("/auth/me"),

  profile: {
    get: () => request<UserProfile>("/profile"),
    update: async (payload: Partial<UserProfile>) => {
      await ensureCsrfCookie();
      return request<UserProfile>("/profile", { method: "PUT", body: JSON.stringify(payload) });
    },
  },

  resumes: {
    list: () => request<ResumeRead[]>("/resumes"),
    upload: async (file: File, label?: string) => {
      await ensureCsrfCookie();
      const form = new FormData();
      form.append("file", file);
      if (label) form.append("label", label);
      return request<ResumeRead>("/resumes", { method: "POST", body: form });
    },
    prefer: async (resumeId: string) => {
      await ensureCsrfCookie();
      return request<ResumeRead>(`/resumes/${resumeId}/prefer`, { method: "POST" });
    },
    applyExtracted: async (resumeId: string, fieldsToApply: string[], markAsVerified = true) => {
      await ensureCsrfCookie();
      return request<UserProfile>(`/resumes/${resumeId}/apply-extracted`, {
        method: "POST",
        body: JSON.stringify({ fields_to_apply: fieldsToApply, mark_as_verified: markAsVerified }),
      });
    },
    remove: async (resumeId: string) => {
      await ensureCsrfCookie();
      return request<{ message: string }>(`/resumes/${resumeId}`, { method: "DELETE" });
    },
  },

  applications: {
    stats: () => request<ApplicationStatsRead>("/applications/stats"),
    list: (params?: { status?: string; search?: string }) => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set("status", params.status);
      if (params?.search) qs.set("search", params.search);
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      return request<ApplicationRead[]>(`/applications${suffix}`);
    },
    create: async (payload: {
      target_url: string;
      application_type: "internship" | "job" | "scholarship" | "hackathon";
      title?: string;
      company_or_org?: string;
      resume_id?: string | null;
      run_immediately?: boolean;
    }) => {
      await ensureCsrfCookie();
      return request<ApplicationRead>("/applications", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    get: (id: string) => request<ApplicationRead>(`/applications/${id}`),
    updateDraft: async (
      id: string,
      payload: {
        edited_values?: Record<string, string>;
        resume_id?: string | null;
        title?: string | null;
        company_or_org?: string | null;
      }
    ) => {
      await ensureCsrfCookie();
      return request<ApplicationRead>(`/applications/${id}/draft`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    approve: async (id: string) => {
      await ensureCsrfCookie();
      return request<ApprovalSnapshotRead>(`/applications/${id}/approve`, { method: "POST" });
    },
    submit: async (id: string) => {
      await ensureCsrfCookie();
      return request<ApplicationRead>(`/applications/${id}/submit`, { method: "POST" });
    },
    retry: async (id: string) => {
      await ensureCsrfCookie();
      return request<ApplicationRead>(`/applications/${id}/retry`, { method: "POST" });
    },
    cancel: async (id: string) => {
      await ensureCsrfCookie();
      return request<ApplicationRead>(`/applications/${id}/cancel`, { method: "POST" });
    },
    manualComplete: async (
      id: string,
      payload: { confirmed_manually: boolean; confirmation_reference?: string; notes?: string }
    ) => {
      await ensureCsrfCookie();
      return request<ApplicationRead>(`/applications/${id}/manual-complete`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    screenshotUrl: (id: string, kind: "draft" | "confirmation") =>
      `${API_BASE}/applications/${id}/screenshots/${kind}`,
  },

  settings: {
    get: () => request<SettingsRead>("/settings"),
    update: async (preferredOllamaModel: string | null) => {
      await ensureCsrfCookie();
      return request<SettingsRead>("/settings", {
        method: "PATCH",
        body: JSON.stringify({ preferred_ollama_model: preferredOllamaModel }),
      });
    },
  },

  privacy: {
    auditLogs: () => request<AuditLogRead[]>("/privacy/audit-logs"),
    exportData: () => request<Record<string, unknown>>("/privacy/export"),
    deleteAccount: async (password: string, confirmPhrase: string) => {
      await ensureCsrfCookie();
      return request<{ message: string }>("/privacy/delete-account", {
        method: "POST",
        body: JSON.stringify({ password, confirm_phrase: confirmPhrase }),
      });
    },
  },
};
