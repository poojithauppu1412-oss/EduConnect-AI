import type { Opportunity } from "./types";

export function formatDate(value: string | null): string {
  if (!value) return "Not listed by the source";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatAmount(value: string | number, currency: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "Amount not listed";
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${new Intl.NumberFormat("en-IN", {
      maximumFractionDigits: 0,
    }).format(amount)}`;
  }
}

export function formatCompensation(opportunity: Opportunity): string {
  if (opportunity.stipend_amount !== null) {
    return `${formatAmount(opportunity.stipend_amount, opportunity.compensation_currency)} stipend`;
  }
  if (opportunity.salary_min !== null && opportunity.salary_max !== null) {
    return `${formatAmount(opportunity.salary_min, opportunity.compensation_currency)}–${formatAmount(opportunity.salary_max, opportunity.compensation_currency)} salary`;
  }
  if (opportunity.salary_min !== null || opportunity.salary_max !== null) {
    return `${formatAmount(opportunity.salary_min ?? opportunity.salary_max!, opportunity.compensation_currency)} salary`;
  }
  return "Compensation not listed by the source";
}

export function displayType(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function displayValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map(displayValue).join(", ");
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, child]) => `${key}: ${displayValue(child)}`)
      .join("; ");
  }
  return "Not listed by the source";
}