"use client";

import { AlertTriangle, CheckCircle2, Copy, ExternalLink, RefreshCw, Save, Send, ShieldCheck, XCircle } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api, ApiError, ApplicationRead, DraftMatch, ResumeRead } from "@/lib/api";

export default function ApplicationReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const appId = params.id;

  const [app, setApp] = useState<ApplicationRead | null>(null);
  const [resumes, setResumes] = useState<ResumeRead[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [selectedResumeId, setSelectedResumeId] = useState<string>("");
  const [title, setTitle] = useState<string>("");
  const [company, setCompany] = useState<string>("");

  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [hasUnsavedEdits, setHasUnsavedEdits] = useState(false);
  const [manualRef, setManualRef] = useState("");
  const [manualNotes, setManualNotes] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hydrateState = useCallback((data: ApplicationRead) => {
    setApp(data);
    setSelectedResumeId(data.resume_id ?? "");
    setTitle(data.title ?? "");
    setCompany(data.company_or_org ?? "");
    const initial: Record<string, string> = {};
    for (const m of data.draft_matches_json ?? []) {
      initial[m.field_id] = m.proposed_value ?? "";
    }
    for (const [k, v] of Object.entries(data.edited_values_json ?? {})) {
      initial[k] = v ?? "";
    }
    setValues(initial);
    setHasUnsavedEdits(false);
  }, []);

  useEffect(() => {
    Promise.all([api.applications.get(appId), api.resumes.list()])
      .then(([appData, resumeList]) => {
        hydrateState(appData);
        setResumes(resumeList);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Failed to load application review.");
      })
      .finally(() => setLoading(false));
  }, [appId, hydrateState]);

  const handleSaveDraft = async () => {
    setBusyAction("save");
    setError(null);
    setMessage(null);
    try {
      const updated = await api.applications.updateDraft(appId, {
        edited_values: values,
        resume_id: selectedResumeId || null,
        title: title || null,
        company_or_org: company || null,
      });
      hydrateState(updated);
      setMessage("Draft changes saved. Review snapshot remains unapproved until you approve.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save edits.");
    } finally {
      setBusyAction(null);
    }
  };

  const handleApproveAndSubmit = async () => {
    setBusyAction("submit");
    setError(null);
    setMessage(null);
    try {
      // Persist latest edits first, then create immutable approval snapshot, then submit!
      await api.applications.updateDraft(appId, {
        edited_values: values,
        resume_id: selectedResumeId || null,
        title: title || null,
        company_or_org: company || null,
      });
      await api.applications.approve(appId);
      await api.applications.submit(appId);
      router.push(`/applications/${appId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Approval or submission failed.");
      try {
        const latest = await api.applications.get(appId);
        hydrateState(latest);
      } catch {
        // ignore refresh error
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleCancel = async () => {
    setBusyAction("cancel");
    setError(null);
    try {
      await api.applications.cancel(appId);
      router.push(`/applications/${appId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to cancel application.");
    } finally {
      setBusyAction(null);
    }
  };

  const handleReturnToForm = async () => {
    setBusyAction("retry");
    setError(null);
    try {
      await api.applications.retry(appId);
      router.push(`/applications/${appId}/progress`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to re-open form inspection.");
    } finally {
      setBusyAction(null);
    }
  };

  const handleCopy = async (fieldId: string, text: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(fieldId);
      setTimeout(() => setCopiedId((prev) => (prev === fieldId ? null : prev)), 1500);
    } catch {
      // ignore clipboard errors in restricted environments
    }
  };

  const handleManualComplete = async () => {
    setBusyAction("manual");
    setError(null);
    try {
      await api.applications.manualComplete(appId, {
        confirmed_manually: true,
        confirmation_reference: manualRef.trim() || undefined,
        notes: manualNotes.trim() || undefined,
      });
      router.push(`/applications/${appId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to record manual submission.");
    } finally {
      setBusyAction(null);
    }
  };

  if (loading) {
    return (
      <RequireAuth>
        <div className="mx-auto max-w-6xl px-4 py-10 text-sm text-slate-600 dark:text-slate-300">
          Loading application review...
        </div>
      </RequireAuth>
    );
  }

  if (!app) {
    return (
      <RequireAuth>
        <div className="mx-auto max-w-4xl px-4 py-10">
          <Alert tone="error">{error || "Application not found."}</Alert>
        </div>
      </RequireAuth>
    );
  }

  const matchByFieldId = new Map<string, DraftMatch>(
    (app.draft_matches_json ?? []).map((m) => [m.field_id, m])
  );
  const canApproveAndSubmit = ["WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT", "APPROVED"].includes(app.status);

  return (
    <RequireAuth>
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                Review &amp; Approve Application
              </h1>
              <StatusBadge status={app.status} />
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300 break-all">
              Destination: {app.target_url}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={app.target_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open Target Form
            </a>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleReturnToForm}
              loading={busyAction === "retry"}
              disabled={!["WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT", "FAILED"].includes(app.status)}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Return &amp; Re-inspect Form
            </Button>
            <Link
              href="/applications"
              className="rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Back to History
            </Link>
          </div>
        </div>

        {message && <Alert tone="success">{message}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}

        {hasUnsavedEdits && (
          <Alert tone="info" title="Unsaved Changes">
            You modified reviewed values or documents. Saving or approving will require a fresh immutable approval snapshot before submission.
          </Alert>
        )}

        {app.missing_fields_json.length > 0 && (
          <Alert tone="warning" title="Missing Required Information">
            Please provide values for: {app.missing_fields_json.join(", ")}.
          </Alert>
        )}

        {app.validation_warnings_json.length > 0 && (
          <Alert tone="warning" title="Validation &amp; AI Warnings">
            <ul className="list-disc pl-4 space-y-0.5">
              {app.validation_warnings_json.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </Alert>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Card className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Application Metadata &amp; Attached Resume
              </h2>
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Role / Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Company / Org</label>
                  <input
                    type="text"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Resume Document</label>
                  <select
                    value={selectedResumeId}
                    onChange={(e) => {
                      setSelectedResumeId(e.target.value);
                      setHasUnsavedEdits(true);
                    }}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option value="">None attached</option>
                    {resumes.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.label} ({r.original_filename})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </Card>

            <Card className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                  Detected Form Fields ({app.detected_fields_json.length})
                </h2>
                <span className="text-xs text-slate-500">
                  AI Provider: {app.ai_provider_used || "deterministic_only"}
                </span>
              </div>

              {app.detected_fields_json.length === 0 ? (
                <p className="text-sm text-slate-500">No form fields detected yet.</p>
              ) : (
                <div className="space-y-4">
                  {app.detected_fields_json.map((field) => {
                    const match = matchByFieldId.get(field.field_id);
                    const val = values[field.field_id] ?? "";
                    const isLowConfidence = match && match.confidence_score < 0.75;
                    const isMissing = field.required && field.input_type !== "file" && !val.trim();

                    return (
                      <div
                        key={field.field_id}
                        className="rounded-lg border border-slate-200 p-4 space-y-2 dark:border-slate-800"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <label
                            htmlFor={`review-${field.field_id}`}
                            className="text-sm font-semibold text-slate-900 dark:text-white"
                          >
                            {field.label || field.name || field.field_id}
                            {field.required && <span className="ml-1 text-red-600">*</span>}
                          </label>
                          <div className="flex flex-wrap items-center gap-1.5">
                            {match?.source === "deterministic" && !match.missing_profile_data && (
                              <Badge tone="green">
                                <CheckCircle2 className="h-3 w-3" />
                                Verified Profile
                              </Badge>
                            )}
                            {match?.source === "semantic" && (
                              <Badge tone="blue">Semantic Match (Review)</Badge>
                            )}
                            {match?.source === "ollama" && (
                              <Badge tone="blue">AI Draft (Review)</Badge>
                            )}
                            {(isMissing || match?.missing_profile_data) && (
                              <Badge tone="amber">
                                <AlertTriangle className="h-3 w-3" />
                                Missing Info
                              </Badge>
                            )}
                            {isLowConfidence && (
                              <Badge tone="amber">
                                Heuristic {(match.confidence_score * 100).toFixed(0)}%
                              </Badge>
                            )}
                            {val && field.input_type !== "file" && (
                              <button
                                type="button"
                                onClick={() => handleCopy(field.field_id, val)}
                                className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                              >
                                <Copy className="h-3 w-3" />
                                {copiedId === field.field_id ? "Copied" : "Copy"}
                              </button>
                            )}
                          </div>
                        </div>

                        {field.input_type === "file" ? (
                          <p className="text-xs text-slate-600 dark:text-slate-300">
                            File upload field — uses selected Resume Document above (
                            {resumes.find((r) => r.id === selectedResumeId)?.original_filename ||
                              "none selected"}
                            ).
                          </p>
                        ) : field.tag === "checkbox" ? (
                          <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                            <input
                              id={`review-${field.field_id}`}
                              type="checkbox"
                              checked={val.toLowerCase() === "true" || val.toLowerCase() === "yes"}
                              onChange={(e) => {
                                setValues((prev) => ({
                                  ...prev,
                                  [field.field_id]: e.target.checked ? "true" : "false",
                                }));
                                setHasUnsavedEdits(true);
                              }}
                              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span>Checked</span>
                          </label>
                        ) : field.tag === "textarea" ? (
                          <textarea
                            id={`review-${field.field_id}`}
                            rows={3}
                            value={val}
                            onChange={(e) => {
                              setValues((prev) => ({ ...prev, [field.field_id]: e.target.value }));
                              setHasUnsavedEdits(true);
                            }}
                            placeholder="Write or refine your response..."
                            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                          />
                        ) : field.tag === "select" || field.tag === "radio_group" ? (
                          <select
                            id={`review-${field.field_id}`}
                            value={val}
                            onChange={(e) => {
                              setValues((prev) => ({ ...prev, [field.field_id]: e.target.value }));
                              setHasUnsavedEdits(true);
                            }}
                            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                          >
                            <option value="">Select an option</option>
                            {field.options.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            id={`review-${field.field_id}`}
                            type="text"
                            value={val}
                            onChange={(e) => {
                              setValues((prev) => ({ ...prev, [field.field_id]: e.target.value }));
                              setHasUnsavedEdits(true);
                            }}
                            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                          />
                        )}

                        {match?.reason && (
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {match.reason}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="space-y-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-blue-600" />
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                  Approval Gate
                </h2>
              </div>
              <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                Clicking <strong>Approve and Submit</strong> creates a cryptographic snapshot of
                your edited values, resume SHA-256, form structure, and target URL, then submits
                only if nothing changed.
              </p>

              <div className="space-y-2.5">
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={handleSaveDraft}
                  loading={busyAction === "save"}
                  disabled={!canApproveAndSubmit}
                >
                  <Save className="h-4 w-4" />
                  Save Edits
                </Button>

                <Button
                  variant="primary"
                  className="w-full"
                  onClick={handleApproveAndSubmit}
                  loading={busyAction === "submit"}
                  disabled={!canApproveAndSubmit}
                >
                  <Send className="h-4 w-4" />
                  Approve and Submit
                </Button>

                <Button
                  variant="ghost"
                  className="w-full text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30"
                  onClick={handleCancel}
                  loading={busyAction === "cancel"}
                  disabled={app.status === "SUBMITTED" || app.status === "CANCELLED"}
                >
                  <XCircle className="h-4 w-4" />
                  Cancel Application
                </Button>
              </div>
            </Card>

            <Card className="space-y-3">
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                Manual-Assisted Fallback
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-300">
                If the site uses CAPTCHA, 2FA, or blocks automation, use <strong>Copy</strong> above to complete it in your browser, then record confirmation here.
              </p>
              <input
                type="text"
                value={manualRef}
                onChange={(e) => setManualRef(e.target.value)}
                placeholder="Confirmation reference (optional)"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-900"
              />
              <textarea
                rows={2}
                value={manualNotes}
                onChange={(e) => setManualNotes(e.target.value)}
                placeholder="Manual completion notes (optional)"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-900"
              />
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={handleManualComplete}
                loading={busyAction === "manual"}
                disabled={["SUBMITTED", "CANCELLED", "SUBMITTING", "VERIFYING"].includes(app.status)}
              >
                Mark Submitted Manually
              </Button>
            </Card>

            {app.has_draft_screenshot && (
              <Card className="space-y-3">
                <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Draft Form Preview
                </h2>
                <img
                  src={api.applications.screenshotUrl(app.id, "draft")}
                  alt="Captured Playwright draft form screenshot"
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-800"
                />
              </Card>
            )}
          </div>
        </div>
      </div>
    </RequireAuth>
  );
}
