"use client";

import { Activity, Database, FilePlus2, FileText, FolderKanban, RefreshCw, ShieldCheck, UserCheck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { useAuth } from "@/components/providers/AuthProvider";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api, ApplicationRead, ApplicationStatsRead, HealthResponse } from "@/lib/api";

export default function DashboardPage() {
  const { user } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<ApplicationStatsRead | null>(null);
  const [recentApps, setRecentApps] = useState<ApplicationRead[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const [h, s, apps] = await Promise.all([
        api.health(),
        api.applications.stats(),
        api.applications.list(),
      ]);
      setHealth(h);
      setStats(s);
      setRecentApps(apps.slice(0, 5));
    } catch {
      setError("Unable to load dashboard status from the backend.");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      void loadDashboard();
    }
  }, [user, loadDashboard]);

  const metricCards = [
    { label: "Total Applications", value: stats?.total ?? 0, tone: "text-slate-900 dark:text-white" },
    { label: "Drafts / In Progress", value: stats?.drafts ?? 0, tone: "text-blue-600 dark:text-blue-400" },
    { label: "Awaiting Review", value: stats?.awaiting_review ?? 0, tone: "text-amber-600 dark:text-amber-400" },
    { label: "Submitted", value: stats?.submitted ?? 0, tone: "text-emerald-600 dark:text-emerald-400" },
    { label: "Failed", value: stats?.failed ?? 0, tone: "text-red-600 dark:text-red-400" },
    { label: "Unknown Outcome", value: stats?.unknown ?? 0, tone: "text-amber-700 dark:text-amber-300" },
  ];

  return (
    <RequireAuth>
      <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              Welcome, {user?.full_name}
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Manage your verified profile, inspect application forms locally, and approve every submission.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" size="sm" onClick={loadDashboard} loading={refreshing}>
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Refresh
            </Button>
            <Link
              href="/applications/new"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 transition-colors"
            >
              <FilePlus2 className="h-4 w-4" aria-hidden="true" />
              New Application
            </Link>
          </div>
        </div>

        {error && <Alert tone="error">{error}</Alert>}

        <section aria-labelledby="metrics-heading" className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <h2 id="metrics-heading" className="sr-only">Application metrics</h2>
          {metricCards.map((item) => (
            <Card key={item.label} className="p-4">
              <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{item.label}</p>
              <p className={`mt-2 text-2xl font-bold ${item.tone}`}>{item.value}</p>
            </Card>
          ))}
        </section>

        <section aria-labelledby="system-status-heading" className="grid gap-4 md:grid-cols-3">
          <h2 id="system-status-heading" className="sr-only">System health</h2>
          <Card className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                <Database className="h-4 w-4 text-blue-600" aria-hidden="true" />
                Database
              </span>
              <Badge tone={health?.database === "ok" ? "green" : "amber"}>
                {health ? health.database.toUpperCase() : "Checking"}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              SQLite local MVP with PostgreSQL-compatible Alembic schema.
            </p>
          </Card>

          <Card className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                <Activity className="h-4 w-4 text-blue-600" aria-hidden="true" />
                Local AI (Ollama)
              </span>
              <Badge tone={health?.ollama.status === "reachable" ? "green" : "amber"}>
                {health ? health.ollama.status : "Checking"}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {health?.ollama.detail || `Model: ${health?.ollama.configured_model ?? "qwen3:4b"}`}
            </p>
          </Card>

          <Card className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                <ShieldCheck className="h-4 w-4 text-blue-600" aria-hidden="true" />
                Human Approval Gate
              </span>
              <Badge tone="blue">Enforced</Badge>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Immutable snapshot verification required before any submission.
            </p>
          </Card>
        </section>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Recent Applications
              </h2>
              <Link href="/applications" className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400">
                View all history
              </Link>
            </div>

            {recentApps.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center space-y-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                  <FolderKanban className="h-6 w-6" aria-hidden="true" />
                </div>
                <p className="font-medium text-slate-900 dark:text-white">No applications tracked yet</p>
                <p className="max-w-md text-sm text-slate-600 dark:text-slate-300">
                  Complete your profile, upload a resume, and paste an internship, job, scholarship, or hackathon URL to start.
                </p>
                <Link
                  href="/applications/new"
                  className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Start first application
                </Link>
              </div>
            ) : (
              <ul className="divide-y divide-slate-200 dark:divide-slate-800">
                {recentApps.map((item) => {
                  const actionHref =
                    item.status === "WAITING_FOR_REVIEW" || item.status === "WAITING_FOR_USER_INPUT" || item.status === "APPROVED"
                      ? `/applications/${item.id}/review`
                      : ["CREATED", "VALIDATING_URL", "OPENING_PAGE", "ANALYZING_FORM", "MATCHING_PROFILE", "FILLING_DRAFT", "SUBMITTING", "VERIFYING"].includes(item.status)
                      ? `/applications/${item.id}/progress`
                      : `/applications/${item.id}`;

                  return (
                    <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-slate-900 dark:text-white">
                          {item.title || item.target_url}
                        </p>
                        <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                          {item.company_or_org ? `${item.company_or_org} • ` : ""}
                          {item.application_type} • {new Date(item.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={item.status} />
                        <Link
                          href={actionHref}
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                        >
                          Open
                        </Link>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>

          <Card className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Quick Actions</h2>
            <div className="space-y-2.5">
              <Link
                href="/profile"
                className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-200 dark:hover:bg-slate-800/70"
              >
                <UserCheck className="h-4 w-4 text-blue-600" aria-hidden="true" />
                Edit &amp; Verify Profile
              </Link>
              <Link
                href="/resumes"
                className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-200 dark:hover:bg-slate-800/70"
              >
                <FileText className="h-4 w-4 text-blue-600" aria-hidden="true" />
                Upload &amp; Parse Resumes
              </Link>
              <Link
                href="/applications/new"
                className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-200 dark:hover:bg-slate-800/70"
              >
                <FilePlus2 className="h-4 w-4 text-blue-600" aria-hidden="true" />
                Inspect New Form URL
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </RequireAuth>
  );
}
