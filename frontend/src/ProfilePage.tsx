import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Save, UserRound } from "lucide-react";
import { Link } from "wouter";

type ProfileRecord = {
  email: string;
  name: string | null;
  education: string | null;
  degree: string | null;
  branch: string | null;
  graduation_year: number | null;
  skills: string[];
  certifications: string[];
  experience_summary: string | null;
  experience_years: number | null;
  preferred_career: string | null;
  preferred_industry: string | null;
  preferred_location: string | null;
  work_mode: string | null;
  government_private_preference: string | null;
  internship_preference: boolean;
  exam_preferences: Record<string, unknown>;
  completion_percent: number;
  updated_at: string;
};

type ProfileForm = {
  name: string;
  education: string;
  degree: string;
  branch: string;
  graduation_year: string;
  skills: string;
  certifications: string;
  experience_summary: string;
  experience_years: string;
  preferred_career: string;
  preferred_industry: string;
  preferred_location: string;
  work_mode: string;
  government_private_preference: string;
  internship_preference: boolean;
  exams: string;
};

const emptyForm: ProfileForm = {
  name: "",
  education: "",
  degree: "",
  branch: "",
  graduation_year: "",
  skills: "",
  certifications: "",
  experience_summary: "",
  experience_years: "",
  preferred_career: "",
  preferred_industry: "",
  preferred_location: "",
  work_mode: "",
  government_private_preference: "",
  internship_preference: false,
  exams: "",
};

function listToText(values: string[] | undefined): string {
  return values?.join("\n") ?? "";
}

function textToList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formFromProfile(profile: ProfileRecord): ProfileForm {
  const exams = profile.exam_preferences.exams;
  return {
    name: profile.name ?? "",
    education: profile.education ?? "",
    degree: profile.degree ?? "",
    branch: profile.branch ?? "",
    graduation_year: profile.graduation_year?.toString() ?? "",
    skills: listToText(profile.skills),
    certifications: listToText(profile.certifications),
    experience_summary: profile.experience_summary ?? "",
    experience_years: profile.experience_years?.toString() ?? "",
    preferred_career: profile.preferred_career ?? "",
    preferred_industry: profile.preferred_industry ?? "",
    preferred_location: profile.preferred_location ?? "",
    work_mode: profile.work_mode ?? "",
    government_private_preference: profile.government_private_preference ?? "",
    internship_preference: profile.internship_preference,
    exams: Array.isArray(exams)
      ? listToText(exams.filter((exam): exam is string => typeof exam === "string"))
      : "",
  };
}

async function apiRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "The profile request could not be completed.");
  }
  return payload as T;
}

async function fetchProfile(): Promise<ProfileRecord> {
  return apiRequest<ProfileRecord>("/api/v1/profile");
}

function ProfileBrand() {
  return (
    <Link className="brand" href="/" aria-label="EduConnect AI home">
      <span className="brand-mark" aria-hidden="true" />
      <span className="brand-name">
        EduConnect <span>AI</span>
      </span>
    </Link>
  );
}

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: fetchProfile,
  });
  const [form, setForm] = useState<ProfileForm>(emptyForm);

  useEffect(() => {
    if (profile.data) {
      setForm(formFromProfile(profile.data));
    }
  }, [profile.data]);

  const saveProfile = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiRequest<ProfileRecord>("/api/v1/profile", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: (savedProfile) => {
      queryClient.setQueryData(["profile"], savedProfile);
    },
  });

  function setField<K extends keyof ProfileForm>(field: K, value: ProfileForm[K]) {
    saveProfile.reset();
    setForm((current) => ({ ...current, [field]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const graduationYear = form.graduation_year.trim();
    const experienceYears = form.experience_years.trim();
    saveProfile.mutate({
      name: form.name,
      education: form.education,
      degree: form.degree,
      branch: form.branch,
      graduation_year: graduationYear ? Number(graduationYear) : null,
      skills: textToList(form.skills),
      certifications: textToList(form.certifications),
      experience_summary: form.experience_summary,
      experience_years: experienceYears ? Number(experienceYears) : null,
      preferred_career: form.preferred_career,
      preferred_industry: form.preferred_industry,
      preferred_location: form.preferred_location,
      work_mode: form.work_mode,
      government_private_preference: form.government_private_preference || null,
      internship_preference: form.internship_preference,
      exam_preferences: { exams: textToList(form.exams) },
    });
  }

  if (profile.isLoading) {
    return (
      <main className="profile-state-screen" role="status" aria-live="polite">
        <p>Loading your saved profile…</p>
      </main>
    );
  }

  if (profile.isError || !profile.data) {
    return (
      <main className="profile-state-screen">
        <section className="profile-error-card" role="alert">
          <h1>Your profile could not be loaded.</h1>
          <p>{profile.error instanceof Error ? profile.error.message : "Try again in a moment."}</p>
          <button className="primary-link profile-action-button" type="button" onClick={() => profile.refetch()}>
            Try again
          </button>
          <Link className="text-link profile-back-link" href="/account">
            <ArrowLeft size={15} aria-hidden="true" /> Back to account
          </Link>
        </section>
      </main>
    );
  }

  return (
    <div className="page-shell profile-shell">
      <header className="site-header">
        <ProfileBrand />
        <Link className="text-link" href="/account">Account</Link>
      </header>
      <main className="profile-main">
        <p className="eyebrow">Your profile</p>
        <h1>Make the next step yours.</h1>
        <p className="profile-intro">
          Add accurate details about your education, skills, experience, and
          goals. You can change them whenever your plans change.
        </p>

        <section className="profile-progress-card" aria-labelledby="profile-progress-title">
          <div className="profile-progress-heading">
            <span className="readiness-symbol" aria-hidden="true"><UserRound /></span>
            <div>
              <h2 id="profile-progress-title">Profile completeness</h2>
              <p>{profile.data.email}</p>
            </div>
            <strong>{profile.data.completion_percent}%</strong>
          </div>
          <div
            className="profile-progress-track"
            role="progressbar"
            aria-label="Profile completeness"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={profile.data.completion_percent}
          >
            <span style={{ width: `${profile.data.completion_percent}%` }} />
          </div>
          <p className="profile-progress-note">
            Completion is based on the information used to personalize future
            opportunity matching. Nothing is inferred from missing details.
          </p>
        </section>

        <form className="profile-form" onSubmit={handleSubmit}>
          <section className="profile-section" aria-labelledby="education-heading">
            <div className="profile-section-heading">
              <span>01</span>
              <div>
                <h2 id="education-heading">Education</h2>
                <p>Share your current or most recent qualification.</p>
              </div>
            </div>
            <div className="profile-field-grid">
              <label className="profile-field">
                <span>Full name</span>
                <input autoComplete="name" maxLength={200} value={form.name} onChange={(event) => setField("name", event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Education level</span>
                <input maxLength={200} placeholder="For example, undergraduate" value={form.education} onChange={(event) => setField("education", event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Degree or qualification</span>
                <input maxLength={200} placeholder="For example, B.Tech" value={form.degree} onChange={(event) => setField("degree", event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Branch or subject</span>
                <input maxLength={200} placeholder="For example, Computer Science" value={form.branch} onChange={(event) => setField("branch", event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Graduation year</span>
                <input inputMode="numeric" max="2100" min="1950" placeholder="YYYY" type="number" value={form.graduation_year} onChange={(event) => setField("graduation_year", event.target.value)} />
              </label>
              <label className="profile-field profile-field-full">
                <span>Skills</span>
                <textarea
                  maxLength={10000}
                  placeholder={"Add one skill per line, for example:\nPython\nData analysis"}
                  rows={4}
                  value={form.skills}
                  onChange={(event) => setField("skills", event.target.value)}
                />
                <small>Enter skills you actually have, one per line.</small>
              </label>
              <label className="profile-field profile-field-full">
                <span>Certifications</span>
                <textarea
                  maxLength={6000}
                  placeholder={"One certification per line"}
                  rows={3}
                  value={form.certifications}
                  onChange={(event) => setField("certifications", event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="profile-section" aria-labelledby="experience-heading">
            <div className="profile-section-heading">
              <span>02</span>
              <div>
                <h2 id="experience-heading">Experience</h2>
                <p>Include work, internships, projects, or other relevant experience.</p>
              </div>
            </div>
            <div className="profile-field-grid">
              <label className="profile-field">
                <span>Years of experience</span>
                <input inputMode="decimal" max="80" min="0" step="0.5" type="number" value={form.experience_years} onChange={(event) => setField("experience_years", event.target.value)} />
              </label>
              <label className="profile-field profile-field-full">
                <span>Experience summary</span>
                <textarea
                  maxLength={5000}
                  placeholder="Describe experience you want considered. You can leave this blank if you have none."
                  rows={5}
                  value={form.experience_summary}
                  onChange={(event) => setField("experience_summary", event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="profile-section" aria-labelledby="preferences-heading">
            <div className="profile-section-heading">
              <span>03</span>
              <div>
                <h2 id="preferences-heading">Career preferences</h2>
                <p>These settings help narrow future searches; they do not guarantee eligibility.</p>
              </div>
            </div>
            <div className="profile-field-grid">
              <label className="profile-field">
                <span>Preferred career</span>
                <input maxLength={200} placeholder="For example, software engineering" value={form.preferred_career} onChange={(event) => setField("preferred_career", event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Preferred industry</span>
                <input maxLength={200} value={form.preferred_industry} onChange={(event) => setField("preferred_industry", event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Preferred location</span>
                <input autoComplete="address-level2" maxLength={200} placeholder="City, state, or region" value={form.preferred_location} onChange={(event) => setField("preferred_location", event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Work mode</span>
                <input maxLength={40} placeholder="On-site, hybrid, remote, or flexible" value={form.work_mode} onChange={(event) => setField("work_mode", event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Sector preference</span>
                <select value={form.government_private_preference} onChange={(event) => setField("government_private_preference", event.target.value)}>
                  <option value="">Choose a preference</option>
                  <option value="government">Government</option>
                  <option value="private">Private</option>
                  <option value="both">Both</option>
                </select>
              </label>
              <label className="profile-field profile-field-full">
                <span>Exams you are preparing for</span>
                <textarea
                  maxLength={4000}
                  placeholder={"Add one exam per line"}
                  rows={3}
                  value={form.exams}
                  onChange={(event) => setField("exams", event.target.value)}
                />
              </label>
              <label className="profile-checkbox">
                <input checked={form.internship_preference} type="checkbox" onChange={(event) => setField("internship_preference", event.target.checked)} />
                <span>Include internships in my future opportunity preferences</span>
              </label>
            </div>
          </section>

          <div className="profile-form-footer">
            <div className="profile-save-status" role="status" aria-live="polite">
              {saveProfile.isSuccess && <><Check size={16} aria-hidden="true" /> Profile saved to your account.</>}
              {saveProfile.isError && (saveProfile.error instanceof Error ? saveProfile.error.message : "The profile could not be saved.")}
            </div>
            <button className="primary-link profile-action-button" type="submit" disabled={saveProfile.isPending}>
              <Save size={16} aria-hidden="true" />
              {saveProfile.isPending ? "Saving…" : "Save profile"}
            </button>
          </div>
          <p className="profile-last-saved">
            Last saved {new Date(profile.data.updated_at).toLocaleString()}
          </p>
        </form>
        <Link className="text-link profile-back-link" href="/account">
          <ArrowLeft size={15} aria-hidden="true" /> Back to account
        </Link>
      </main>
    </div>
  );
}