"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useState } from "react";

import { useAuth } from "@/components/providers/AuthProvider";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { api, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.login({ email, password });
      setUser(res.user);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to sign in right now.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-14 sm:px-6">
      <Card className="space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Welcome back</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Sign in to review your profile, drafts, and application history.
          </p>
        </div>

        {error && <Alert tone="error">{error}</Alert>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email address"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="ada@example.com"
          />
          <Input
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" className="w-full" loading={submitting}>
            Sign in
          </Button>
        </form>

        <p className="text-center text-sm text-slate-600 dark:text-slate-300">
          New to ApplyPilot AI?{" "}
          <Link href="/signup" className="font-medium text-blue-600 hover:underline dark:text-blue-400">
            Create an account
          </Link>
        </p>
      </Card>
    </div>
  );
}

