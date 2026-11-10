"use client";

import { Play, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { api, ApiError, ResumeRead } from "@/lib/api";

export default function NewApplicationPage() {
  const router = useRouter();
  const [targetUrl, setTargetUrl] = useState("");
  const [appType, setAppType] = useState<"internship" | "job" | "scholarship" | "hackathon">("internship");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [resumeId, setResumeId] = useState<string>("");
  const [resumes, setResumes] = useState<ResumeRead[]>([]);
  const [allowLocalhost, setAllowLocalhost] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.resumes.list(), api.settings.get()])
      .then(([resList, cfg]) => {
        setResumes(resList);
        const preferred = resList.find((r) => r.is_preferred) ?? resList[0];
        if (preferred) setResumeId(preferred.id);
        setAllowLocalhost(cfg.allow_localhost_automation);
      })
      .catch(() => undefined);
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.applications.create({
        target_url: targetUrl.trim(),
        application_type: appType,
        title: title.trim() || undefined,
        company_or_org: company.trim() || undefined,
        resume_id: resumeId || null,
      });
      router.push(`/applications/${created.id}/progress`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start application inspection.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RequireAuth>
      <div className="mx-auto max-w-2xl space-y-6 px-4 py-8 sm:px-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">New Application</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Paste an internship, job, scholarship, or hackathon URL. ApplyPilot AI will inspect and draft-fill it without submitting.
          </p>
        </div>

        <Alert tone="info" title="Safety &amp; SSRF Protection">
          {allowLocalhost
            ? "Localhost controlled testing mode is enabled in backend configuration. Private LAN/metadata targets remain blocked."
            : "Localhost and private-network URLs are blocked by default. Only public HTTPS/HTTP application URLs are permitted unless ALLOW_LOCALHOST_AUTOMATION=true is configured for local test forms."}
        </Alert>

        {error && <Alert tone="error">{error}</Alert>}

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Application URL *"
              type="url"
              required
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://careers.example.com/internships/swe-2027"
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label htmlFor="app-type" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                  Category
                </label>
                <select
                  id="app-type"
                  value={appType}
                  onChange={(e) =>
                    setAppType(e.target.value as "internship" | "job" | "scholarship" | "hackathon")
                  }
                  className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                >
                  <option value="internship">Internship</option>
                  <option value="job">Job</option>
                  <option value="scholarship">Scholarship</option>
                  <option value="hackathon">Hackathon</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="app-resume" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                  Resume to Attach
                </label>
                <select
                  id="app-resume"
                  value={resumeId}
                  onChange={(e) => setResumeId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                >
                  <option value="">No resume selected</option>
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.label} ({r.original_filename})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Role / Title (optional)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Software Engineering Intern"
              />
              <Input
                label="Company / Organization (optional)"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Acme Cloud"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                <ShieldCheck className="h-4 w-4 text-blue-600" />
                Never submits automatically
              </span>
              <Button type="submit" loading={submitting}>
                <Play className="h-4 w-4" />
                Inspect &amp; Draft Form
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </RequireAuth>
  );
}

