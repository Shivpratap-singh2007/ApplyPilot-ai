"use client";

import { CheckCircle2, FileText, Star, Trash2, Upload } from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { api, ApiError, ResumeRead } from "@/lib/api";

export default function ResumesPage() {
  const [resumes, setResumes] = useState<ResumeRead[]>([]);
  const [label, setLabel] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedHints, setSelectedHints] = useState<Record<string, Record<string, boolean>>>({});
  const [verifyOnApply, setVerifyOnApply] = useState<Record<string, boolean>>({});
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadResumes = useCallback(async () => {
    try {
      const items = await api.resumes.list();
      setResumes(items);
      const nextHints: Record<string, Record<string, boolean>> = {};
      const nextVerify: Record<string, boolean> = {};
      for (const item of items) {
        const keys = Object.keys(item.extracted_data_json ?? {});
        nextHints[item.id] = Object.fromEntries(keys.map((k) => [k, true]));
        nextVerify[item.id] = true;
      }
      setSelectedHints(nextHints);
      setVerifyOnApply(nextVerify);
    } catch {
      setError("Failed to load resumes.");
    }
  }, []);

  useEffect(() => {
    void loadResumes();
  }, [loadResumes]);

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setError("Select a PDF or DOCX resume file first.");
      return;
    }
    setUploading(true);
    setError(null);
    setMessage(null);
    try {
      await api.resumes.upload(selectedFile, label || undefined);
      setLabel("");
      setSelectedFile(null);
      setMessage("Resume uploaded and extracted. Review extracted hints below before verifying.");
      await loadResumes();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload resume.");
    } finally {
      setUploading(false);
    }
  };

  const handlePrefer = async (id: string) => {
    setError(null);
    try {
      await api.resumes.prefer(id);
      await loadResumes();
      setMessage("Preferred resume updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update preferred resume.");
    }
  };

  const handleApplyExtracted = async (resume: ResumeRead) => {
    setError(null);
    const chosenMap = selectedHints[resume.id] ?? {};
    const chosenKeys = Object.entries(chosenMap)
      .filter(([, checked]) => checked)
      .map(([k]) => k);
    if (chosenKeys.length === 0) {
      setError("Select at least one extracted field to apply.");
      return;
    }
    const markVerified = verifyOnApply[resume.id] ?? true;
    try {
      await api.resumes.applyExtracted(resume.id, chosenKeys, markVerified);
      await loadResumes();
      setMessage(
        `Applied ${chosenKeys.length} extracted field(s) to My Profile (${
          markVerified ? "marked verified" : "left unverified for review"
        }).`
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to apply extracted fields.");
    }
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      await api.resumes.remove(id);
      await loadResumes();
      setMessage("Resume deleted.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete resume.");
    }
  };

  return (
    <RequireAuth>
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Resume Manager</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Maintain multiple resumes (.pdf or .docx), inspect encrypted extracted data, and choose which fields to verify into your profile.
          </p>
        </div>

        {message && <Alert tone="success">{message}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}

        <Card>
          <form onSubmit={handleUpload} className="grid gap-4 sm:grid-cols-3 items-end">
            <Input
              label="Resume Label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Backend SWE Intern v2"
            />
            <div className="space-y-1.5">
              <label htmlFor="resume-file" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                Resume File (PDF or DOCX)
              </label>
              <input
                id="resume-file"
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
            </div>
            <Button type="submit" loading={uploading}>
              <Upload className="h-4 w-4" />
              Upload &amp; Extract
            </Button>
          </form>
        </Card>

        {resumes.length === 0 ? (
          <Card className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">
            No resumes uploaded yet. Upload your first PDF or DOCX resume above.
          </Card>
        ) : (
          <div className="space-y-4">
            {resumes.map((r) => {
              const extractedKeys = Object.entries(r.extracted_data_json ?? {});
              const hintChecks = selectedHints[r.id] ?? {};
              return (
                <Card key={r.id} className="space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <FileText className="h-4 w-4 text-blue-600" />
                        <h2 className="font-semibold text-slate-900 dark:text-white">{r.label}</h2>
                        {r.is_preferred && <Badge tone="blue">Preferred</Badge>}
                        <Badge tone={r.is_verified ? "green" : "amber"}>
                          {r.is_verified ? "Verified" : "Needs Verification"}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {r.original_filename} • {(r.file_size_bytes / 1024).toFixed(1)} KB • SHA-256: {r.sha256_hash.slice(0, 12)}...
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {!r.is_preferred && (
                        <Button variant="secondary" size="sm" onClick={() => handlePrefer(r.id)}>
                          <Star className="h-3.5 w-3.5" />
                          Set Preferred
                        </Button>
                      )}
                      {extractedKeys.length > 0 && (
                        <Button variant="primary" size="sm" onClick={() => handleApplyExtracted(r)}>
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Verify &amp; Apply Selected
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id)}>
                        <Trash2 className="h-4 w-4 text-red-600" />
                        Delete
                      </Button>
                    </div>
                  </div>

                  {extractedKeys.length > 0 && (
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-3 dark:border-slate-800 dark:bg-slate-950/60">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Extracted Resume Hints (Unverified until applied)
                        </p>
                        <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 dark:text-slate-300">
                          <input
                            type="checkbox"
                            checked={verifyOnApply[r.id] ?? true}
                            onChange={(e) =>
                              setVerifyOnApply((prev) => ({ ...prev, [r.id]: e.target.checked }))
                            }
                          />
                          Mark applied fields as verified
                        </label>
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2 text-xs">
                        {extractedKeys.map(([k, v]) => (
                          <label key={k} className="flex items-start gap-2 rounded border border-slate-200 bg-white p-2 dark:border-slate-800 dark:bg-slate-900">
                            <input
                              type="checkbox"
                              checked={hintChecks[k] ?? true}
                              onChange={(e) =>
                                setSelectedHints((prev) => ({
                                  ...prev,
                                  [r.id]: { ...(prev[r.id] ?? {}), [k]: e.target.checked },
                                }))
                              }
                              className="mt-0.5"
                            />
                            <div>
                              <span className="font-semibold text-slate-800 dark:text-slate-200">{k}: </span>
                              <span className="text-slate-600 dark:text-slate-400">
                                {Array.isArray(v) ? v.join(", ") : String(v)}
                              </span>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </RequireAuth>
  );
}
