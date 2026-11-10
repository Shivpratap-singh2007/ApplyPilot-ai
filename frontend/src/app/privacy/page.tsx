"use client";

import { Download, ShieldAlert, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { useAuth } from "@/components/providers/AuthProvider";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { api, ApiError, AuditLogRead } from "@/lib/api";

export default function PrivacyPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [logs, setLogs] = useState<AuditLogRead[]>([]);
  const [password, setPassword] = useState("");
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.privacy
      .auditLogs()
      .then(setLogs)
      .catch(() => setError("Unable to load audit logs."));
  }, []);

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    setMessage(null);
    try {
      const payload = await api.privacy.exportData();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "applypilot-data-export.json";
      a.click();
      URL.revokeObjectURL(url);
      setMessage("Your data export JSON has been downloaded.");
      setLogs(await api.privacy.auditLogs());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to export data.");
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAccount = async (event: React.FormEvent) => {
    event.preventDefault();
    setDeleting(true);
    setError(null);
    try {
      await api.privacy.deleteAccount(password, confirmPhrase);
      setUser(null);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to delete account.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <RequireAuth>
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Privacy &amp; Data Controls</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Export your complete profile, resume metadata, applications, and audit history, or permanently erase your local account.
          </p>
        </div>

        {message && <Alert tone="success">{message}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}

        <Card className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Export My Data</h2>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Downloads a machine-readable JSON archive of your account, profile, resumes, applications, and audit logs.
            </p>
          </div>
          <Button variant="secondary" onClick={handleExport} loading={exporting}>
            <Download className="h-4 w-4" />
            Download JSON Export
          </Button>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Recent Security Audit Log</h2>
          {logs.length === 0 ? (
            <p className="text-sm text-slate-500">No audit events found.</p>
          ) : (
            <div className="max-h-72 overflow-y-auto divide-y divide-slate-200 text-xs dark:divide-slate-800">
              {logs.map((item) => (
                <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <div>
                    <span className="font-semibold text-slate-900 dark:text-white">{item.event_type}</span>
                    {item.resource_type && (
                      <span className="ml-2 text-slate-500">
                        ({item.resource_type} {item.resource_id?.slice(0, 8)})
                      </span>
                    )}
                  </div>
                  <span className="text-slate-400">{new Date(item.created_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="border-red-200 dark:border-red-900 space-y-4">
          <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
            <ShieldAlert className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Danger Zone — Delete Account &amp; Local Files</h2>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300">
            This permanently deletes your user account, profile, uploaded resume files, screenshots, application records, and approval snapshots.
          </p>
          <form onSubmit={handleDeleteAccount} className="grid gap-4 sm:grid-cols-3 items-end">
            <Input
              label="Current Password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Input
              label="Type DELETE to confirm"
              required
              value={confirmPhrase}
              onChange={(e) => setConfirmPhrase(e.target.value)}
              placeholder="DELETE"
            />
            <Button type="submit" variant="danger" loading={deleting}>
              <Trash2 className="h-4 w-4" />
              Permanently Delete
            </Button>
          </form>
        </Card>
      </div>
    </RequireAuth>
  );
}

