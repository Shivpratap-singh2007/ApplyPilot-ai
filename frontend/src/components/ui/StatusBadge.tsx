import { Badge } from "@/components/ui/Badge";

const STATUS_TONE_MAP: Record<string, "blue" | "green" | "amber" | "red" | "neutral"> = {
  CREATED: "neutral",
  VALIDATING_URL: "blue",
  OPENING_PAGE: "blue",
  ANALYZING_FORM: "blue",
  MATCHING_PROFILE: "blue",
  FILLING_DRAFT: "blue",
  WAITING_FOR_USER_INPUT: "amber",
  WAITING_FOR_REVIEW: "blue",
  APPROVED: "green",
  SUBMITTING: "blue",
  VERIFYING: "blue",
  SUBMITTED: "green",
  FAILED: "red",
  UNKNOWN: "amber",
  CANCELLED: "neutral",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE_MAP[status] ?? "neutral"}>{status}</Badge>;
}

