import React from "react";

type AlertTone = "info" | "success" | "warning" | "error";

const ALERT_CLASSES: Record<AlertTone, string> = {
  info: "border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-200",
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200",
  warning:
    "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200",
  error:
    "border-red-200 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/50 dark:text-red-200",
};

export function Alert({
  tone = "info",
  title,
  children,
}: {
  tone?: AlertTone;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      role={tone === "error" || tone === "warning" ? "alert" : "status"}
      className={`rounded-lg border px-4 py-3 text-sm ${ALERT_CLASSES[tone]}`}
    >
      {title && <p className="font-semibold mb-0.5">{title}</p>}
      <div>{children}</div>
    </div>
  );
}

