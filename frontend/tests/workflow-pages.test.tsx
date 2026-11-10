import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/providers/AuthProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import ApplicationReviewPage from "@/app/applications/[id]/review/page";
import DashboardPage from "@/app/dashboard/page";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  useParams: () => ({ id: "app-123" }),
  usePathname: () => "/applications/app-123/review",
}));

describe("ApplyPilot AI Workflow Pages", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    pushMock.mockReset();
  });

  it("renders dashboard stats and recent applications for authenticated user", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "u1",
              email: "ada@example.com",
              full_name: "Ada Lovelace",
              is_active: true,
              created_at: "2026-11-10T10:00:00Z",
            }),
            { status: 200 }
          )
        );
      }
      if (url.endsWith("/health")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              status: "ok",
              app_name: "ApplyPilot AI",
              environment: "development",
              database: "ok",
              ollama: {
                provider: "ollama",
                base_url: "http://localhost:11434",
                configured_model: "qwen3:4b",
                fallback_model: "qwen3:1.7b",
                status: "reachable",
                model_available: true,
                available_models: ["qwen3:4b"],
                detail: null,
              },
            }),
            { status: 200 }
          )
        );
      }
      if (url.endsWith("/applications/stats")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              total: 3,
              drafts: 1,
              awaiting_review: 1,
              submitted: 1,
              failed: 0,
              unknown: 0,
              cancelled: 0,
            }),
            { status: 200 }
          )
        );
      }
      if (url.endsWith("/applications")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      }
      return Promise.resolve(new Response("{}", { status: 404 }));
    });

    render(
      <ThemeProvider>
        <AuthProvider>
          <DashboardPage />
        </AuthProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/welcome, ada lovelace/i)).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });
    expect(screen.getByText("Total Applications")).toBeInTheDocument();
  });

  it("allows editing and explicit Approve and Submit on Review page", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "u1",
              email: "ada@example.com",
              full_name: "Ada Lovelace",
              is_active: true,
              created_at: "2026-11-10T10:00:00Z",
            }),
            { status: 200 }
          )
        );
      }
      if (url.endsWith("/auth/csrf")) {
        return Promise.resolve(new Response(JSON.stringify({ csrf_token: "csrf-1" }), { status: 200 }));
      }
      if (url.endsWith("/resumes")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      }
      if (url.endsWith("/applications/app-123") && method === "GET") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "app-123",
              user_id: "u1",
              resume_id: null,
              target_url: "https://careers.example.com/intern",
              application_type: "internship",
              title: "SWE Intern",
              company_or_org: "Acme Cloud",
              status: "WAITING_FOR_REVIEW",
              detected_fields_json: [
                {
                  field_id: "why_apply",
                  tag: "textarea",
                  input_type: "textarea",
                  name: "why_apply",
                  element_id: "why_apply",
                  label: "Why do you want to join?",
                  placeholder: "",
                  nearby_text: "",
                  required: true,
                  options: [],
                  selector: "#why_apply",
                  current_value: "",
                },
              ],
              draft_matches_json: [
                {
                  field_id: "why_apply",
                  suggested_profile_key: null,
                  proposed_value: "",
                  confidence_score: 0.0,
                  source: "unmatched",
                  reason: "Requires human answer.",
                  requires_human_review: true,
                  missing_profile_data: true,
                  is_ai_draft: false,
                },
              ],
              edited_values_json: {},
              validation_warnings_json: [],
              missing_fields_json: ["Why do you want to join?"],
              has_draft_screenshot: false,
              has_confirmation_screenshot: false,
              confirmation_reference: null,
              confirmation_evidence_json: null,
              error_message: null,
              ai_provider_used: "deterministic_only",
              created_at: "2026-11-10T10:00:00Z",
              updated_at: "2026-11-10T10:00:00Z",
              submitted_at: null,
              transitions: [],
              latest_approval: null,
            }),
            { status: 200 }
          )
        );
      }
      if (url.endsWith("/applications/app-123/draft") && method === "PATCH") {
        return Promise.resolve(new Response(JSON.stringify({ id: "app-123", status: "WAITING_FOR_REVIEW" }), { status: 200 }));
      }
      if (url.endsWith("/applications/app-123/approve") && method === "POST") {
        return Promise.resolve(new Response(JSON.stringify({ id: "snap-1", snapshot_hash: "abc" }), { status: 200 }));
      }
      if (url.endsWith("/applications/app-123/submit") && method === "POST") {
        return Promise.resolve(new Response(JSON.stringify({ id: "app-123", status: "SUBMITTED" }), { status: 200 }));
      }
      return Promise.resolve(new Response("{}", { status: 404 }));
    });

    render(
      <ThemeProvider>
        <AuthProvider>
          <ApplicationReviewPage />
        </AuthProvider>
      </ThemeProvider>
    );

    const textarea = await screen.findByLabelText(/why do you want to join\?/i);
    fireEvent.change(textarea, { target: { value: "I build Python automation tools." } });

    const submitBtn = screen.getByRole("button", { name: /approve and submit/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/applications/app-123");
    });

    const calledUrls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(calledUrls.some((u) => u.endsWith("/approve"))).toBe(true);
    expect(calledUrls.some((u) => u.endsWith("/submit"))).toBe(true);
  });
});
