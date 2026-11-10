"use client";

import { Compass, LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { useAuth } from "@/components/providers/AuthProvider";
import { Button } from "@/components/ui/Button";

const AUTH_NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/applications/new", label: "New Application" },
  { href: "/applications", label: "History" },
  { href: "/profile", label: "My Profile" },
  { href: "/resumes", label: "Resumes" },
  { href: "/settings", label: "Settings" },
  { href: "/privacy", label: "Privacy" },
];

export function Navbar() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    setMobileOpen(false);
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link
          href={user ? "/dashboard" : "/"}
          className="flex items-center gap-2.5 rounded-md text-lg font-semibold tracking-tight text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-white"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
            <Compass className="h-4 w-4" aria-hidden="true" />
          </span>
          <span>ApplyPilot AI</span>
        </Link>

        <nav aria-label="Primary navigation" className="hidden md:flex items-center gap-1">
          {!loading && user ? (
            <>
              {AUTH_NAV_LINKS.map((item) => {
                const active = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(`${item.href}/`) && item.href !== "/applications");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                      active
                        ? "bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300"
                        : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
              <div className="ml-2 flex items-center gap-2 border-l border-slate-200 pl-3 dark:border-slate-800">
                <ThemeToggle />
                <Button variant="secondary" size="sm" onClick={handleLogout}>
                  <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
                  Sign out
                </Button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <Link
                href="/login"
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center rounded-lg bg-blue-600 px-3.5 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              >
                Get started
              </Link>
            </div>
          )}
        </nav>

        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <button
            type="button"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((prev) => !prev)}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-700 dark:border-slate-700 dark:text-slate-200"
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-slate-200 bg-white px-4 py-3 space-y-1 md:hidden dark:border-slate-800 dark:bg-slate-950">
          {!loading && user ? (
            <>
              {AUTH_NAV_LINKS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {item.label}
                </Link>
              ))}
              <div className="pt-2">
                <Button variant="secondary" size="sm" className="w-full" onClick={handleLogout}>
                  <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
                  Sign out
                </Button>
              </div>
            </>
          ) : (
            <div className="flex flex-col gap-2">
              <Link
                href="/login"
                onClick={() => setMobileOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                onClick={() => setMobileOpen(false)}
                className="rounded-lg bg-blue-600 px-3 py-2 text-center text-sm font-medium text-white hover:bg-blue-700"
              >
                Get started
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
