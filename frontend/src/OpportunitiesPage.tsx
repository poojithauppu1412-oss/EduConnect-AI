import { useState } from "react";
import type { FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Search, ShieldCheck } from "lucide-react";
import { Link } from "wouter";
import {
  fetchOpportunityCategories,
  fetchOpportunityPage,
  fetchSavedOpportunityIds,
} from "./opportunities/api";
import OpportunityCard from "./opportunities/OpportunityCard";
import type { OpportunityFilters } from "./opportunities/types";

type FilterDraft = Omit<OpportunityFilters, "page" | "page_size">;
type DashboardTab = "discover" | "saved";

const emptyFilters: FilterDraft = {
  q: "",
  category: "",
  opportunity_type: "",
  government_private: "",
  location: "",
  work_mode: "",
  compensation_currency: "INR",
  min_compensation: "",
  sort: "newest",
};

const opportunityTypes = [
  ["", "All opportunity types"],
  ["GOVERNMENT_JOB", "Government jobs"],
  ["PRIVATE_JOB", "Private jobs"],
  ["INTERNSHIP", "Internships"],
  ["APPRENTICESHIP", "Apprenticeships"],
  ["SCHOLARSHIP", "Scholarships"],
  ["FELLOWSHIP", "Fellowships"],
  ["EXAM", "Exams"],
  ["ENTRANCE_EXAM", "Entrance exams"],
  ["HACKATHON", "Hackathons"],
  ["COMPETITION", "Competitions"],
  ["RESEARCH", "Research"],
  ["GOVERNMENT_SCHEME", "Government schemes"],
  ["SKILL_PROGRAM", "Skill programs"],
  ["OTHER", "Other"],
];

function DashboardBrand() {
  return (
    <Link className="brand" href="/" aria-label="EduConnect AI home">
      <span className="brand-mark" aria-hidden="true" />
      <span className="brand-name">EduConnect <span>AI</span></span>
    </Link>
  );
}

export default function OpportunitiesPage() {
  const [tab, setTab] = useState<DashboardTab>("discover");
  const [draft, setDraft] = useState<FilterDraft>(emptyFilters);
  const [filters, setFilters] = useState<FilterDraft>(emptyFilters);
  const [page, setPage] = useState(1);
  const pageFilters: OpportunityFilters = {
    ...filters,
    page,
    page_size: 12,
  };

  const opportunities = useQuery({
    queryKey: ["opportunities", tab, pageFilters],
    queryFn: () => fetchOpportunityPage(pageFilters, tab === "saved"),
  });
  const savedIds = useQuery({
    queryKey: ["saved-opportunity-ids"],
    queryFn: fetchSavedOpportunityIds,
    staleTime: 30_000,
  });
  const categories = useQuery({
    queryKey: ["opportunity-categories"],
    queryFn: fetchOpportunityCategories,
    staleTime: 60_000,
  });

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters({
      ...draft,
      q: draft.q.trim(),
      category: draft.category.trim(),
      location: draft.location.trim(),
      work_mode: draft.work_mode.trim(),
    });
    setPage(1);
  }

  function selectTab(nextTab: DashboardTab) {
    setTab(nextTab);
    setPage(1);
  }

  const currentItems = opportunities.data?.items ?? [];
  const savedIdSet = new Set(savedIds.data ?? []);
  const queryIsEmpty = Object.entries(filters).every(
    ([key, value]) => key === "sort" || key === "compensation_currency" || value === "",
  );

  return (
    <div className="page-shell opportunities-shell">
      <header className="site-header">
        <DashboardBrand />
        <nav className="dashboard-nav" aria-label="Account navigation">
          <Link className="text-link" href="/profile">Profile</Link>
          <Link className="text-link" href="/account">Account</Link>
        </nav>
      </header>

      <main className="opportunities-main">
        <div className="dashboard-heading">
          <div>
            <p className="eyebrow">EduConnect opportunity board</p>
            <h1>Find a verified next step.</h1>
            <p className="dashboard-intro">
              Search current listings and check their official sources before
              applying. Listings without a source link and verification date
              are not shown here.
            </p>
          </div>
          <Link className="dashboard-back-link" href="/account">
            <ArrowLeft size={15} aria-hidden="true" /> Account
          </Link>
        </div>

        <section className="opportunity-trust-note" aria-label="Listing verification">
          <span className="readiness-symbol" aria-hidden="true"><ShieldCheck /></span>
          <p>
            Every public listing includes its official page, source, and last
            verification time. Older checks are marked so you can recheck before
            acting.
          </p>
        </section>

        <div className="opportunity-tabs" role="tablist" aria-label="Opportunity views">
          <button
            className="opportunity-tab"
            type="button"
            role="tab"
            aria-selected={tab === "discover"}
            onClick={() => selectTab("discover")}
          >
            Discover
          </button>
          <button
            className="opportunity-tab"
            type="button"
            role="tab"
            aria-selected={tab === "saved"}
            onClick={() => selectTab("saved")}
          >
            Saved{savedIds.data ? ` (${savedIds.data.length})` : ""}
          </button>
        </div>

        <form className="opportunity-search-form" onSubmit={submitSearch}>
          <label className="opportunity-search-field">
            <span>Search listings</span>
            <span className="opportunity-search-input">
              <Search size={17} aria-hidden="true" />
              <input
                autoComplete="off"
                maxLength={200}
                placeholder="Role, qualification, skill, or organization"
                value={draft.q}
                onChange={(event) => setDraft((current) => ({ ...current, q: event.target.value }))}
              />
            </span>
          </label>
          <label className="opportunity-search-field">
            <span>Type</span>
            <select
              value={draft.opportunity_type}
              onChange={(event) => setDraft((current) => ({ ...current, opportunity_type: event.target.value }))}
            >
              {opportunityTypes.map(([value, label]) => (
                <option key={value || "all"} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label className="opportunity-search-field">
            <span>Category</span>
            <select
              value={draft.category}
              onChange={(event) => setDraft((current) => ({ ...current, category: event.target.value }))}
              disabled={categories.isLoading || categories.isError}
            >
              <option value="">All verified categories</option>
              {(categories.data ?? []).map((category) => (
                <option key={category.slug} value={category.slug}>{category.name}</option>
              ))}
            </select>
          </label>
          <label className="opportunity-search-field">
            <span>Sector</span>
            <select
              value={draft.government_private}
              onChange={(event) => setDraft((current) => ({ ...current, government_private: event.target.value }))}
            >
              <option value="">All sectors</option>
              <option value="government">Government</option>
              <option value="private">Private</option>
              <option value="both">Both</option>
            </select>
          </label>
          <label className="opportunity-search-field">
            <span>Location</span>
            <input
              maxLength={200}
              placeholder="City or region"
              value={draft.location}
              onChange={(event) => setDraft((current) => ({ ...current, location: event.target.value }))}
            />
          </label>
          <label className="opportunity-search-field">
            <span>Work mode</span>
            <select
              value={draft.work_mode}
              onChange={(event) => setDraft((current) => ({ ...current, work_mode: event.target.value }))}
            >
              <option value="">Any work mode</option>
              <option value="onsite">On-site</option>
              <option value="hybrid">Hybrid</option>
              <option value="remote">Remote</option>
            </select>
          </label>
          <label className="opportunity-search-field">
            <span>Minimum compensation</span>
            <input
              inputMode="decimal"
              min="0"
              placeholder="Listed amount"
              type="number"
              value={draft.min_compensation}
              onChange={(event) => setDraft((current) => ({ ...current, min_compensation: event.target.value }))}
            />
          </label>
          <label className="opportunity-search-field">
            <span>Compensation currency</span>
            <select
              value={draft.compensation_currency}
              onChange={(event) => setDraft((current) => ({ ...current, compensation_currency: event.target.value }))}
            >
              <option value="INR">INR · Indian rupee</option>
              <option value="USD">USD · US dollar</option>
              <option value="EUR">EUR · euro</option>
              <option value="GBP">GBP · pound sterling</option>
            </select>
          </label>
          <label className="opportunity-search-field">
            <span>Sort by</span>
            <select
              value={draft.sort}
              onChange={(event) => setDraft((current) => ({ ...current, sort: event.target.value }))}
            >
              <option value="newest">Newest</option>
              <option value="deadline">Closing date</option>
              <option value="salary">Salary or stipend</option>
              <option value="relevance">Relevance</option>
            </select>
          </label>
          <button className="primary-link opportunity-search-submit" type="submit">
            Apply filters <ArrowRight size={16} aria-hidden="true" />
          </button>
        </form>

        {savedIds.isError && (
          <p className="dashboard-inline-error" role="alert">
            Saved status could not be checked. Reload before changing saved listings.
          </p>
        )}

        <section className="opportunity-results" aria-live="polite">
          <div className="opportunity-results-heading">
            <div>
              <p className="eyebrow">{tab === "saved" ? "Your collection" : "Verified listings"}</p>
              <h2>
                {opportunities.isLoading
                  ? "Loading opportunities…"
                  : `${opportunities.data?.total ?? 0} ${opportunities.data?.total === 1 ? "listing" : "listings"}`}
              </h2>
            </div>
            {tab === "saved" && (
              <p className="opportunity-results-note">
                Saved listings stay here while their source record is available.
              </p>
            )}
          </div>

          {opportunities.isLoading && (
            <div className="opportunity-state" role="status">Loading current listings…</div>
          )}

          {opportunities.isError && (
            <div className="opportunity-state opportunity-state-error" role="alert">
              <h3>Listings could not be loaded.</h3>
              <p>{opportunities.error instanceof Error ? opportunities.error.message : "The opportunity service is unavailable."}</p>
              <button className="secondary-link" type="button" onClick={() => opportunities.refetch()}>
                Try again
              </button>
            </div>
          )}

          {!opportunities.isLoading && !opportunities.isError && currentItems.length === 0 && (
            <div className="opportunity-state opportunity-empty-state">
              <span className="readiness-symbol" aria-hidden="true"><Search /></span>
              <h3>
                {tab === "saved"
                  ? "No saved listings match these filters."
                  : queryIsEmpty
                    ? "No verified opportunities are available yet."
                    : "No listings match these filters."}
              </h3>
              <p>
                {tab === "saved"
                  ? "Save a listing from Discover to keep it here."
                  : "Listings appear only after their source and official application page have been reviewed. No sample listings are used."}
              </p>
              {tab === "discover" && !queryIsEmpty && (
                <button
                  className="secondary-link"
                  type="button"
                  onClick={() => {
                    setDraft(emptyFilters);
                    setFilters(emptyFilters);
                    setPage(1);
                  }}
                >
                  Clear filters
                </button>
              )}
            </div>
          )}

          {!opportunities.isLoading && !opportunities.isError && currentItems.length > 0 && (
            <div className="opportunity-card-grid">
              {currentItems.map((opportunity) => (
                <OpportunityCard
                  key={opportunity.id}
                  opportunity={opportunity}
                  isSaved={savedIdSet.has(opportunity.id)}
                  saveDisabled={savedIds.isLoading || savedIds.isError}
                />
              ))}
            </div>
          )}

          {(opportunities.data?.page_count ?? 0) > 1 && (
            <nav className="opportunity-pagination" aria-label="Opportunity pages">
              <button
                className="secondary-link"
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                <ArrowLeft size={15} aria-hidden="true" /> Previous
              </button>
              <span>Page {page} of {opportunities.data?.page_count}</span>
              <button
                className="secondary-link"
                type="button"
                disabled={page >= (opportunities.data?.page_count ?? 1)}
                onClick={() => setPage((current) => current + 1)}
              >
                Next <ArrowRight size={15} aria-hidden="true" />
              </button>
            </nav>
          )}
        </section>
      </main>
    </div>
  );
}