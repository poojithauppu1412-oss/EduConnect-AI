import type {
  Opportunity,
  OpportunityCategoryOption,
  OpportunityFilters,
  OpportunityPageData,
} from "./types";

export async function apiRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  const payload = response.status === 204
    ? undefined
    : await response.json().catch(() => undefined);
  if (!response.ok) {
    throw new Error(
      payload?.detail ?? "The opportunity request could not be completed.",
    );
  }
  return payload as T;
}

function toSearchParams(filters: OpportunityFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (typeof value === "string" ? value.trim() : value !== undefined) {
      params.set(key, String(value));
    }
  }
  return params;
}

export function fetchOpportunityPage(
  filters: OpportunityFilters,
  saved = false,
): Promise<OpportunityPageData> {
  const path = saved ? "/api/v1/opportunities/saved" : "/api/v1/opportunities";
  return apiRequest<OpportunityPageData>(
    `${path}?${toSearchParams(filters).toString()}`,
  );
}

export function fetchSavedOpportunityIds(): Promise<string[]> {
  return apiRequest<string[]>("/api/v1/opportunities/saved/ids");
}

export function fetchOpportunityCategories(): Promise<OpportunityCategoryOption[]> {
  return apiRequest<OpportunityCategoryOption[]>("/api/v1/opportunities/categories");
}

export function fetchOpportunity(id: string): Promise<Opportunity> {
  return apiRequest<Opportunity>(`/api/v1/opportunities/${encodeURIComponent(id)}`);
}

export async function changeSavedStatus(
  id: string,
  currentlySaved: boolean,
): Promise<void> {
  await apiRequest<void>(`/api/v1/opportunities/${encodeURIComponent(id)}/save`, {
    method: currentlySaved ? "DELETE" : "POST",
  });
}