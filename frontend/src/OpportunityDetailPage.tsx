import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  ExternalLink,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import { Link, useParams } from "wouter";
import {
  fetchOpportunity,
  fetchSavedOpportunityIds,
} from "./opportunities/api";
import SaveButton from "./opportunities/SaveButton";
import {
  displayType,
  displayValue,
  formatCompensation,
  formatDate,
} from "./opportunities/presentation";

function DetailBrand() {
  return (
    <Link className="brand" href="/" aria-label="EduConnect AI home">
      <span className="brand-mark" aria-hidden="true" />
      <span className="brand-name">EduConnect <span>AI</span></span>
    </Link>
  );
}

function listDisplayValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") return displayValue(value);
  return String(value);
}

export default function OpportunityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const opportunity = useQuery({
    queryKey: ["opportunity", id],
    queryFn: () => fetchOpportunity(id),
    enabled: Boolean(id),
  });
  const savedIds = useQuery({
    queryKey: ["saved-opportunity-ids"],
    queryFn: fetchSavedOpportunityIds,
    staleTime: 30_000,
  });

  if (opportunity.isLoading) {
    return (
      <main className="opportunity-detail-state" role="status" aria-live="polite">
        Loading the verified listing…
      </main>
    );
  }

  if (opportunity.isError || !opportunity.data) {
    return (
      <main className="opportunity-detail-state">
        <section className="opportunity-detail-error" role="alert">
          <p className="eyebrow">Opportunity details</p>
          <h1>This listing is unavailable.</h1>
          <p>
            {opportunity.error instanceof Error
              ? opportunity.error.message
              : "It may have expired or been removed from public listings."}
          </p>
          <Link className="primary-link" href="/dashboard">
            <ArrowLeft size={15} aria-hidden="true" /> Back to opportunities
          </Link>
        </section>
      </main>
    );
  }

  const item = opportunity.data;
  const facts = [
    ["Qualification", item.qualification],
    ["Branch or subject", item.branch],
    ["Experience", item.experience_required],
    ["Age limit", item.age_limit],
    ["Work mode", item.work_mode],
    ["Application fee", item.application_fee === null
      ? null
      : `${item.compensation_currency} ${item.application_fee}`],
    ["Opening date", item.opening_date ? formatDate(item.opening_date) : null],
    ["Closing date", item.closing_date ? formatDate(item.closing_date) : null],
    ["Exam date", item.exam_date ? formatDate(item.exam_date) : null],
    ["Result date", item.result_date ? formatDate(item.result_date) : null],
  ].filter((fact): fact is [string, string] => Boolean(fact[1]));

  return (
    <div className="page-shell opportunity-detail-shell">
      <header className="site-header">
        <DetailBrand />
        <nav className="dashboard-nav" aria-label="Account navigation">
          <Link className="text-link" href="/dashboard">Opportunities</Link>
          <Link className="text-link" href="/profile">Profile</Link>
        </nav>
      </header>
      <main className="opportunity-detail-main">
        <Link className="dashboard-back-link" href="/dashboard">
          <ArrowLeft size={15} aria-hidden="true" /> Back to opportunities
        </Link>

        {item.is_stale && (
          <div className="opportunity-verification-alert" role="status">
            <ShieldCheck size={18} aria-hidden="true" />
            <p>
              Information may be outdated. Last verified {formatDate(item.last_verified_at)}.
              Recheck the official source before acting.
            </p>
          </div>
        )}

        <section className="opportunity-detail-hero">
          <div className="opportunity-detail-title">
            <div className="opportunity-detail-tags">
              <span className="opportunity-type">{displayType(item.opportunity_type)}</span>
              <span className="opportunity-category">{item.category_name}</span>
            </div>
            <h1>{item.title}</h1>
            <p className="opportunity-detail-organization">
              {item.organization_name ?? "Organization not listed by the source"}
            </p>
            <div className="opportunity-detail-meta">
              <span><MapPin size={15} aria-hidden="true" />{item.location ?? "Location not listed"}</span>
              <span><CalendarDays size={15} aria-hidden="true" />Closes {formatDate(item.closing_date)}</span>
              <span>{formatCompensation(item)}</span>
            </div>
          </div>
          <div className="opportunity-detail-actions">
            <SaveButton
              opportunityId={item.id}
              isSaved={(savedIds.data ?? []).includes(item.id)}
              disabled={savedIds.isLoading || savedIds.isError}
            />
            {item.official_url && (
              <a
                className="primary-link opportunity-apply-link"
                href={item.official_url}
                target="_blank"
                rel="noreferrer"
              >
                Official application <ArrowUpRight size={16} aria-hidden="true" />
              </a>
            )}
            {savedIds.isError && (
              <p className="dashboard-inline-error" role="status">
                Saved status could not be checked.
              </p>
            )}
          </div>
        </section>

        <div className="opportunity-detail-columns">
          <div className="opportunity-detail-primary">
            <section className="opportunity-detail-section">
              <h2>About this opportunity</h2>
              <p className="opportunity-detail-description">{item.description}</p>
            </section>
            {facts.length > 0 && (
              <section className="opportunity-detail-section">
                <h2>Key details</h2>
                <dl className="opportunity-facts">
                  {facts.map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}
            {Object.keys(item.eligibility).length > 0 && (
              <section className="opportunity-detail-section">
                <h2>Eligibility information</h2>
                <dl className="opportunity-facts">
                  {Object.entries(item.eligibility).map(([label, value]) => (
                    <div key={label}>
                      <dt>{label.replaceAll("_", " ")}</dt>
                      <dd>{displayValue(value)}</dd>
                    </div>
                  ))}
                </dl>
                <p className="opportunity-caveat">
                  This listing summarizes source information; it does not guarantee eligibility.
                  Confirm the requirements with the official source.
                </p>
              </section>
            )}
            {item.skills.length > 0 && (
              <section className="opportunity-detail-section">
                <h2>Skills listed by the source</h2>
                <div className="opportunity-skill-list">
                  {item.skills.map((skill) => (
                    <span key={skill.name}>
                      {skill.name}{skill.is_required ? " · required" : ""}
                    </span>
                  ))}
                </div>
              </section>
            )}
            {item.documents_required.length > 0 && (
              <section className="opportunity-detail-section">
                <h2>Documents required</h2>
                <ul className="opportunity-detail-list">
                  {item.documents_required.map((document, index) => (
                    <li key={`${index}-${String(document)}`}>{listDisplayValue(document)}</li>
                  ))}
                </ul>
              </section>
            )}
            {item.selection_process.length > 0 && (
              <section className="opportunity-detail-section">
                <h2>Selection process</h2>
                <ol className="opportunity-detail-list">
                  {item.selection_process.map((step, index) => (
                    <li key={`${index}-${String(step)}`}>{listDisplayValue(step)}</li>
                  ))}
                </ol>
              </section>
            )}
            {item.application_steps.length > 0 && (
              <section className="opportunity-detail-section">
                <h2>Application steps</h2>
                <ol className="opportunity-detail-list">
                  {item.application_steps.map((step, index) => (
                    <li key={`${index}-${String(step)}`}>{listDisplayValue(step)}</li>
                  ))}
                </ol>
              </section>
            )}
          </div>

          <aside className="opportunity-source-card">
            <span className="eyebrow">Source record</span>
            <h2>Check the official notice</h2>
            <p>
              Use the source page to confirm dates, requirements, and any changes
              before you apply.
            </p>
            <dl>
              <div>
                <dt>Last verified</dt>
                <dd>{formatDate(item.last_verified_at)}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>{item.source_name ?? "Official source"}</dd>
              </div>
            </dl>
            {item.source_url && (
              <a
                className="source-link"
                href={item.source_url}
                target="_blank"
                rel="noreferrer"
              >
                Open source page <ExternalLink size={14} aria-hidden="true" />
              </a>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}