import { ArrowUpRight, CalendarDays, MapPin } from "lucide-react";
import { Link } from "wouter";
import { formatCompensation, formatDate, displayType } from "./presentation";
import type { Opportunity } from "./types";
import SaveButton from "./SaveButton";

type OpportunityCardProps = {
  opportunity: Opportunity;
  isSaved: boolean;
  saveDisabled?: boolean;
};

export default function OpportunityCard({
  opportunity,
  isSaved,
  saveDisabled = false,
}: OpportunityCardProps) {
  return (
    <article className="opportunity-card">
      <div className="opportunity-card-top">
        <div>
          <span className="opportunity-type">{displayType(opportunity.opportunity_type)}</span>
          <p className="opportunity-organization">
            {opportunity.organization_name ?? "Organization not listed by the source"}
          </p>
        </div>
        <SaveButton
          opportunityId={opportunity.id}
          isSaved={isSaved}
          disabled={saveDisabled}
        />
      </div>
      <h2>{opportunity.title}</h2>
      <p className="opportunity-summary">{opportunity.description}</p>
      <div className="opportunity-metadata">
        <span><MapPin size={14} aria-hidden="true" />{opportunity.location ?? "Location not listed"}</span>
        <span><CalendarDays size={14} aria-hidden="true" />Closes {formatDate(opportunity.closing_date)}</span>
      </div>
      <div className="opportunity-card-bottom">
        <span className="opportunity-compensation">{formatCompensation(opportunity)}</span>
        <Link className="opportunity-details-link" href={`/opportunities/${opportunity.id}`}>
          Details <ArrowUpRight size={15} aria-hidden="true" />
        </Link>
      </div>
      {opportunity.is_stale && (
        <p className="opportunity-stale-note">
          Last verified {formatDate(opportunity.last_verified_at)}. Please recheck the official source.
        </p>
      )}
    </article>
  );
}