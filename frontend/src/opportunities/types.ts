export type OpportunitySkill = {
  name: string;
  is_required: boolean;
};

export type Opportunity = {
  id: string;
  title: string;
  description: string;
  organization_name: string | null;
  organization_website_url: string | null;
  category_name: string;
  category_slug: string;
  opportunity_type: string;
  qualification: string | null;
  branch: string | null;
  experience_required: string | null;
  age_limit: string | null;
  location: string | null;
  work_mode: string | null;
  salary_min: string | number | null;
  salary_max: string | number | null;
  stipend_amount: string | number | null;
  compensation_currency: string;
  application_fee: string | number | null;
  opening_date: string | null;
  closing_date: string | null;
  exam_date: string | null;
  result_date: string | null;
  eligibility: Record<string, unknown>;
  skills: OpportunitySkill[];
  documents_required: unknown[];
  selection_process: unknown[];
  application_steps: unknown[];
  official_url: string | null;
  source_url: string | null;
  source_name: string | null;
  source_type: string | null;
  status: string;
  published_at: string | null;
  last_verified_at: string | null;
  expires_at: string | null;
  is_stale: boolean;
};

export type OpportunityPageData = {
  items: Opportunity[];
  total: number;
  page: number;
  page_size: number;
  page_count: number;
};

export type OpportunityCategoryOption = {
  name: string;
  slug: string;
};

export type OpportunityFilters = {
  q: string;
  category: string;
  opportunity_type: string;
  government_private: string;
  location: string;
  work_mode: string;
  compensation_currency: string;
  min_compensation: string;
  sort: string;
  page: number;
  page_size: number;
};