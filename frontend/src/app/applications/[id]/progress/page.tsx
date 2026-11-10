"use client";

import { ArrowRight, CheckCircle2, Clock, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api, ApiError, ApplicationRead } from "@/lib/api";

const ACTIVE_POLL_STATES = new Set([
  "CREATED",
  "VALIDATING_URL",
  "OPENING_PAGE",
  "ANALYZING_FORM",
  "MATCHING_PROFILE",
  "FILLING_DRAFT",
  "SUBMITTING",
  "VERIFYING",
]);

const PIPELINE_STEPS = [
  "CREATED",
  "VALIDATING_URL",
  "OPENING_PAGE",
  "ANALYZING_FORM",
  "MATCHING_PROFILE",
  "FILLING_DRAFT",
  "WAITING_FOR_REVIEW",
];

export default function AgentProgressPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const appId = params.id;
  const [app, setApp] = useState<ApplicationRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.applications.get(appId);
      setApp(data);
      if (data.status === "WAITING_FOR_REVIEW") {
        router.replace(`/applications/${appId}/review`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load application progress.");
    }
  }, [appId, router]);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (!app || !ACTIVE_POLL_STATES.has(app.status)) return;
    const timer = setInterval(() => {
      void fetchStatus();
    }, 1200);
    return () => clearInterval(timer);
  }, [app, fetchStatus]);

  const handleRetry = async () => {
    setRetrying(true);
    setError(null);
    try {
      const updated = await api.applications.retry(appId);
      setApp(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Retry failed.");
    } finally {
      setRetrying(false);
    }
  };

  return (
    <RequireAuth>
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Agent Progress</h1>
            <p className="text-sm text-slate-600 dark:text-slate-300 truncate max-w-xl">
              {app?.target_url ?? "Loading..."}
            </p>
          </div>
          {app && <StatusBadge status={app.status} />}
        </div>

        {error && <Alert tone="error">{error}</Alert>}

        {app?.status === "WAITING_FOR_USER_INPUT" && (
          <Alert tone="warning" title="Human Action or Missing Fields Required">
            {app.error_message ||
              `Missing required information: ${app.missing_fields_json.join(", ")}. You can fill missing answers on the Review screen.`}
          </Alert>
        )}

        {app?.status === "FAILED" && (
          <Alert tone="error" title="Form Inspection Failed">
            {app.error_message || "The agent encountered an error while inspecting this form."}
          </Alert>
        )}

        <Card className="space-y-4">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Pipeline Stages</h2>
          <ol className="space-y-2.5">
            {PIPELINE_STEPS.map((step) => {
              const reached = app?.transitions.some((t) => t.to_status === step) ?? false;
              const isCurrent = app?.status === step;
              return (
                <li
                  key={step}
                  className={`flex items-center justify-between rounded-lg border px-3.5 py-2.5 text-sm ${
                    isCurrent
                      ? "border-blue-500 bg-blue-50/70 text-blue-900 dark:bg-blue-950/50 dark:text-blue-200"
                      : reached
                      ? "border-emerald-200 bg-emerald-50/50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200"
                      : "border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400"
                  }`}
                >
                  <span className="font-medium">{step}</span>
                  {reached ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <Clock className="h-4 w-4 opacity-50" />
                  )}
                </li>
              );
            })}
          </ol>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex gap-2">
              {app && ["FAILED", "WAITING_FOR_USER_INPUT"].includes(app.status) && (
                <Button variant="secondary" onClick={handleRetry} loading={retrying}>
                  <RefreshCw className="h-4 w-4" />
                  Re-inspect Form
                </Button>
              )}
              <Link
                href={`/applications/${appId}`}
                className="inline-flex items-center rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                View Details
              </Link>
            </div>

            {app && ["WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT", "APPROVED"].includes(app.status) && (
              <Link
                href={`/applications/${appId}/review`}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Proceed to Review
                <ArrowRight className="h-4 w-4" />
              </Link>
            )}
          </div>
        </Card>
      </div>
    </RequireAuth>
  );
}

