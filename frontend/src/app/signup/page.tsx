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

export default function SignupPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.register({ full_name: fullName, email, password });
      setUser(res.user);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create account right now.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-14 sm:px-6">
      <Card className="space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Create your account</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Your profile and applications stay isolated to your local workspace account.
          </p>
        </div>

        {error && <Alert tone="error">{error}</Alert>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Full name"
            name="full_name"
            type="text"
            autoComplete="name"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Ada Lovelace"
          />
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
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            hint="Minimum 8 characters with at least one letter and one number or symbol."
          />
          <Button type="submit" className="w-full" loading={submitting}>
            Create account
          </Button>
        </form>

        <p className="text-center text-sm text-slate-600 dark:text-slate-300">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-blue-600 hover:underline dark:text-blue-400">
            Log in
          </Link>
        </p>
      </Card>
    </div>
  );
}

