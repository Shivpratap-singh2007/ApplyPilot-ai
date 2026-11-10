import { ArrowRight, CheckCircle2, Cpu, Lock, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

const HIGHLIGHTS = [
  {
    icon: Cpu,
    title: "100% Local AI Inference",
    description:
      "Powered locally by Ollama (Qwen3 4B quantized) and deterministic Python rules. Zero paid cloud LLM APIs.",
  },
  {
    icon: ShieldCheck,
    title: "Human Approval Gate",
    description:
      "Every form field, generated answer, and uploaded document is locked to an immutable snapshot you explicitly approve before submission.",
  },
  {
    icon: Lock,
    title: "Privacy & Security First",
    description:
      "Per-user isolated storage, Argon2id authentication, strict URL/SSRF protections, and zero fabricated credentials.",
  },
];

const WORKFLOW_STEPS = [
  "Create your verified profile and upload resumes",
  "Paste an internship, job, scholarship, or hackathon URL",
  "Inspect & auto-fill fields with deterministic rules + local Qwen3",
  "Review, edit, and explicitly approve before submission",
];

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-20 space-y-16">
      <section className="mx-auto max-w-3xl text-center space-y-6">
        <Badge tone="blue">Local-First AI • Ollama Qwen3 4B • Human-in-the-Loop</Badge>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl dark:text-white">
          Apply faster without giving up accuracy or control.
        </h1>
        <p className="text-lg text-slate-600 dark:text-slate-300">
          ApplyPilot AI helps students, freshers, and professionals fill internship, job,
          scholarship, and hackathon forms using verified profile facts—never fabricating
          qualifications and never submitting without your explicit approval.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
          >
            Create local account
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-800 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
          >
            Sign in
          </Link>
        </div>
      </section>

      <section aria-labelledby="pillars-heading" className="grid gap-6 md:grid-cols-3">
        <h2 id="pillars-heading" className="sr-only">
          Core principles
        </h2>
        {HIGHLIGHTS.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.title} className="space-y-3">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{item.title}</h3>
              <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                {item.description}
              </p>
            </Card>
          );
        })}
      </section>

      <section aria-labelledby="workflow-heading">
        <Card className="bg-gradient-to-br from-blue-50/70 to-white dark:from-slate-900 dark:to-slate-900/60">
          <div className="grid gap-8 md:grid-cols-2 md:items-center">
            <div className="space-y-3">
              <Badge tone="neutral">Controlled Workflow</Badge>
              <h2 id="workflow-heading" className="text-2xl font-bold text-slate-900 dark:text-white">
                Built for strict human oversight
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Deterministic matching handles standard fields first; local Qwen3 4B only assists
                with ambiguous labels and open-ended drafts.
              </p>
            </div>
            <ul className="space-y-3">
              {WORKFLOW_STEPS.map((step) => (
                <li key={step} className="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-200">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-blue-600 dark:text-blue-400" aria-hidden="true" />
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </section>
    </div>
  );
}

