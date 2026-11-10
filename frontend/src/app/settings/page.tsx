"use client";

import { Cpu, Save } from "lucide-react";
import React, { useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { api, ApiError, HealthResponse, SettingsRead } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsRead | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [preferredModel, setPreferredModel] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.settings.get(), api.health()])
      .then(([s, h]) => {
        setSettings(s);
        setHealth(h);
        setPreferredModel(s.preferred_ollama_model ?? "");
      })
      .catch(() => setError("Unable to load settings."));
  }, []);

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.settings.update(preferredModel.trim() || null);
      setSettings(updated);
      setMessage("Local AI model preference updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <RequireAuth>
      <div className="mx-auto max-w-4xl space-y-6 px-4 py-8 sm:px-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Configure your local Ollama model preference, review runtime capabilities, and adjust display theme.
          </p>
        </div>

        {message && <Alert tone="success">{message}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}

        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Local AI Engine (Ollama)</h2>
            </div>
            <Badge tone={health?.ollama.status === "reachable" ? "green" : "amber"}>
              {health?.ollama.status ?? "Checking"}
            </Badge>
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-300">
            Endpoint: <span className="font-mono">{settings?.ollama_base_url ?? "http://localhost:11434"}</span> • Default:{" "}
            <span className="font-mono">{settings?.default_ollama_model ?? "qwen3:4b"}</span> • Low-RAM Fallback:{" "}
            <span className="font-mono">{settings?.fallback_ollama_model ?? "qwen3:1.7b"}</span>
          </p>

          {health?.ollama.available_models.length ? (
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Pulled models detected: {health.ollama.available_models.join(", ")}
            </p>
          ) : (
            <Alert tone="info">
              No running Ollama models detected right now. Install Ollama and run{" "}
              <span className="font-mono">ollama pull qwen3:4b</span> (or{" "}
              <span className="font-mono">ollama pull qwen3:1.7b</span> on low-RAM laptops).
            </Alert>
          )}

          <form onSubmit={handleSave} className="space-y-4">
            <Input
              label="Preferred Local Ollama Model Override"
              value={preferredModel}
              onChange={(e) => setPreferredModel(e.target.value)}
              placeholder="Leave blank for default (qwen3:4b) or enter qwen3:1.7b"
              hint="Zero paid cloud LLM APIs are ever used."
            />
            <Button type="submit" loading={saving}>
              <Save className="h-4 w-4" />
              Save Model Preference
            </Button>
          </form>
        </Card>

        <div className="grid gap-6 sm:grid-cols-2">
          <Card className="space-y-3">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Appearance</h2>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Toggle light or dark mode for the ApplyPilot AI workspace.
            </p>
            <ThemeToggle />
          </Card>

          <Card className="space-y-3">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Workspace Usage &amp; Plan</h2>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Tier: <Badge tone="blue">{settings?.plan_tier ?? "free_local"}</Badge>
            </p>
            <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-1">
              {Object.entries(settings?.usage_summary ?? {}).map(([k, v]) => (
                <li key={k} className="flex justify-between">
                  <span>{k}</span>
                  <span className="font-semibold">{v}</span>
                </li>
              ))}
              {Object.keys(settings?.usage_summary ?? {}).length === 0 && (
                <li>No usage events recorded yet.</li>
              )}
            </ul>
          </Card>
        </div>
      </div>
    </RequireAuth>
  );
}

