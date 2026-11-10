"use client";

import { FilePlus2, Search } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Alert } from "@/components/ui/Alert";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api, ApplicationRead } from "@/lib/api";

const STATUS_OPTIONS = [
  "",
  "WAITING_FOR_REVIEW",
  "WAITING_FOR_USER_INPUT",
  "APPROVED",
  "SUBMITTED",
  "FAILED",
  "UNKNOWN",
  "CANCELLED",
];

export default function ApplicationHistoryPage() {
  const [apps, setApps] = useState<ApplicationRead[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.applications.list({
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setApps(data);
    } catch {
      setError("Failed to fetch application history.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  return (
    <RequireAuth>
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Application History</h1>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Track drafts, awaiting approvals, confirmed submissions, failures, and uncertain outcomes.
            </p>
          </div>
          <Link
            href="/applications/new"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <FilePlus2 className="h-4 w-4" />
            New Application
          </Link>
        </div>

        {error && <Alert tone="error">{error}</Alert>}

        <Card className="grid gap-3 sm:grid-cols-3">
          <div className="sm:col-span-2 relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="search"
              aria-label="Search applications"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, company, URL, or confirmation ref..."
              className="w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            />
          </div>
          <select
            aria-label="Filter by status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.filter(Boolean).map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </Card>

        {loading ? (
          <Card className="py-10 text-center text-sm text-slate-500">Loading applications...</Card>
        ) : apps.length === 0 ? (
          <Card className="py-12 text-center space-y-2">
            <p className="font-medium text-slate-900 dark:text-white">No matching applications</p>
            <p className="text-sm text-slate-500">Try clearing filters or start a new application.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {apps.map((item) => (
              <Card key={item.id} className="flex flex-wrap items-center justify-between gap-4 p-4">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold text-slate-900 dark:text-white truncate">
                      {item.title || item.target_url}
                    </h2>
                    <StatusBadge status={item.status} />
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-2xl">
                    {item.company_or_org ? `${item.company_or_org} • ` : ""}
                    {item.application_type} • Created {new Date(item.created_at).toLocaleString()}
                    {item.confirmation_reference ? ` • Ref: ${item.confirmation_reference}` : ""}
                  </p>
                  {item.error_message && (
                    <p className="text-xs text-red-600 dark:text-red-400 truncate max-w-2xl">
                      {item.error_message}
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {["WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT", "APPROVED"].includes(item.status) && (
                    <Link
                      href={`/applications/${item.id}/review`}
                      className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                    >
                      Review &amp; Approve
                    </Link>
                  )}
                  <Link
                    href={`/applications/${item.id}`}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Details
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </RequireAuth>
  );
}

