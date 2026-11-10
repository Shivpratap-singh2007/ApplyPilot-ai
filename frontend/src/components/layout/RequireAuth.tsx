"use client";

import { useRouter } from "next/navigation";
import React, { useEffect } from "react";

import { useAuth } from "@/components/providers/AuthProvider";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-14 text-sm text-slate-600 dark:text-slate-300">
        Verifying your session...
      </div>
    );
  }

  return <>{children}</>;
}

