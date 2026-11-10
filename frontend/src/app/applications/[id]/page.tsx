"use client";

import { CheckCircle2, RefreshCw, XCircle } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api, ApiError, ApplicationRead } from "@/lib/api";

export default function ApplicationDetailsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const appId = params.id;

  const [app, setApp] = useState<ApplicationRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setApp(await api.applications.get(appId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load application details.");
    }
  }, [appId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRetry = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.applications.retry(appId);
      router.push(`/applications/${appId}/progress`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cannot retry this application.");
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async () => {
    setBusy(true);
    setError(null);
    try {
      setApp(await api.applications.cancel(appId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to cancel application.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <RequireAuth>
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        {error && <Alert tone="error">{error}</Alert>}

        {!app ? (
          <Card className="py-10 text-center text-sm text-slate-500">Loading details...</Card>
        ) : (
          <>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                    {app.title || "Application Details"}
                  </h1>
                  <StatusBadge status={app.status} />
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-300 break-all">{app.target_url}</p>
              </div>

              <div className="flex flex-wrap gap-2">
                {["WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT", "APPROVED"].includes(app.status) && (
                  <Link
                    href={`/applications/${app.id}/review`}
                    className="rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    Open Review
                  </Link>
                )}
                {["FAILED", "WAITING_FOR_USER_INPUT", "WAITING_FOR_REVIEW"].includes(app.status) && (
                  <Button variant="secondary" onClick={handleRetry} loading={busy}>
                    <RefreshCw className="h-4 w-4" />
                    Re-inspect Form
                  </Button>
                )}
                {!["SUBMITTED", "CANCELLED", "SUBMITTING"].includes(app.status) && (
                  <Button variant="ghost" onClick={handleCancel} loading={busy}>
                    <XCircle className="h-4 w-4 text-red-600" />
                    Cancel
                  </Button>
                )}
              </div>
            </div>

            {app.status === "SUBMITTED" && (
              <Alert tone="success" title="Submission Confirmed">
                Submitted at {app.submitted_at ? new Date(app.submitted_at).toLocaleString() : "recently"}.
                {app.confirmation_reference ? ` Confirmation Reference: ${app.confirmation_reference}` : ""}
              </Alert>
            )}

            {app.status === "UNKNOWN" && (
              <Alert tone="warning" title="Uncertain Submission Outcome (UNKNOWN)">
                {app.error_message ||
                  "Submission was attempted, but confirmation evidence was not clear. Automatic retry is disabled to prevent duplicate submissions."}
              </Alert>
            )}

            {app.status === "FAILED" && app.error_message && (
              <Alert tone="error" title="Failure Details">
                {app.error_message}
              </Alert>
            )}

            <div className="grid gap-6 md:grid-cols-2">
              <Card className="space-y-3">
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                  Confirmation &amp; Approval Evidence
                </h2>
                <dl className="space-y-2 text-sm">
                  <div>
                    <dt className="text-xs font-medium text-slate-500">Company / Organization</dt>
                    <dd className="text-slate-900 dark:text-white">{app.company_or_org || "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-slate-500">Confirmation Reference</dt>
                    <dd className="font-mono text-slate-900 dark:text-white">{app.confirmation_reference || "None"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-slate-500">Latest Approval Snapshot Hash</dt>
                    <dd className="font-mono text-xs break-all text-slate-700 dark:text-slate-300">
                      {app.latest_approval?.snapshot_hash || "Not approved yet"}
                    </dd>
                  </div>
                  {app.confirmation_evidence_json && (
                    <div>
                      <dt className="text-xs font-medium text-slate-500">Captured Evidence</dt>
                      <dd className="mt-1 rounded bg-slate-50 p-2 text-xs font-mono dark:bg-slate-950 overflow-x-auto">
                        {JSON.stringify(app.confirmation_evidence_json, null, 2)}
                      </dd>
                    </div>
                  )}
                </dl>
              </Card>

              <Card className="space-y-3">
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                  State Machine Timeline
                </h2>
                <ol className="space-y-2 text-xs">
                  {app.transitions.map((t) => (
                    <li key={t.id} className="flex items-start gap-2 border-l-2 border-blue-500 pl-3 py-1">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-600" />
                      <div>
                        <p className="font-semibold text-slate-900 dark:text-white">
                          {t.from_status ? `${t.from_status} → ${t.to_status}` : t.to_status}
                        </p>
                        <p className="text-slate-600 dark:text-slate-300">{t.reason}</p>
                        <p className="text-slate-400">{new Date(t.created_at).toLocaleString()}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </Card>
            </div>

            {(app.has_draft_screenshot || app.has_confirmation_screenshot) && (
              <div className="grid gap-6 md:grid-cols-2">
                {app.has_draft_screenshot && (
                  <Card className="space-y-2">
                    <h2 className="text-sm font-semibold">Draft Screenshot</h2>
                    <img
                      src={api.applications.screenshotUrl(app.id, "draft")}
                      alt="Draft form screenshot"
                      className="w-full rounded-lg border border-slate-200 dark:border-slate-800"
                    />
                  </Card>
                )}
                {app.has_confirmation_screenshot && (
                  <Card className="space-y-2">
                    <h2 className="text-sm font-semibold">Post-Submission Screenshot</h2>
                    <img
                      src={api.applications.screenshotUrl(app.id, "confirmation")}
                      alt="Submission confirmation screenshot"
                      className="w-full rounded-lg border border-slate-200 dark:border-slate-800"
                    />
                  </Card>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </RequireAuth>
  );
}

