"use client";

import { CheckCircle2, Plus, Save, Trash2 } from "lucide-react";
import React, { useEffect, useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { api, ApiError, ResumeRead, UserProfile } from "@/lib/api";

function csvToList(text: string): string[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function listToCsv(items: string[] | undefined): string {
  return (items ?? []).join(", ");
}

function VerificationTag({
  value,
  verified,
}: {
  value: unknown;
  verified?: boolean;
}) {
  const hasVal = Array.isArray(value) ? value.length > 0 : Boolean(value && String(value).trim());
  if (!hasVal) return <Badge tone="neutral">Missing</Badge>;
  if (verified) return <Badge tone="green">Verified</Badge>;
  return <Badge tone="amber">Unverified</Badge>;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [resumes, setResumes] = useState<ResumeRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [skillsText, setSkillsText] = useState("");
  const [langsText, setLangsText] = useState("");
  const [achievementsText, setAchievementsText] = useState("");
  const [rolesText, setRolesText] = useState("");
  const [locationsText, setLocationsText] = useState("");
  const [teamMembersText, setTeamMembersText] = useState("");
  const [hackStackText, setHackStackText] = useState("");

  useEffect(() => {
    Promise.all([api.profile.get(), api.resumes.list()])
      .then(([prof, resList]) => {
        setProfile(prof);
        setResumes(resList);
        setSkillsText(listToCsv(prof.technical_skills));
        setLangsText(listToCsv(prof.programming_languages));
        setAchievementsText(listToCsv(prof.achievements));
        setRolesText(listToCsv(prof.preferred_roles));
        setLocationsText(listToCsv(prof.preferred_locations));
        setTeamMembersText(listToCsv(prof.team_members));
        setHackStackText(listToCsv(prof.hackathon_tech_stack));
      })
      .catch(() => setError("Unable to load profile."))
      .finally(() => setLoading(false));
  }, []);

  const updateField = <K extends keyof UserProfile>(key: K, value: UserProfile[K]) => {
    setProfile((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const addStructuredItem = (
    key: "projects" | "work_experience" | "internships" | "certifications",
    template: Record<string, string>
  ) => {
    if (!profile) return;
    updateField(key, [...(profile[key] ?? []), template]);
  };

  const removeStructuredItem = (
    key: "projects" | "work_experience" | "internships" | "certifications",
    idx: number
  ) => {
    if (!profile) return;
    updateField(
      key,
      (profile[key] ?? []).filter((_, i) => i !== idx)
    );
  };

  const updateStructuredField = (
    key: "projects" | "work_experience" | "internships" | "certifications",
    idx: number,
    field: string,
    val: string
  ) => {
    if (!profile) return;
    const copy = [...(profile[key] ?? [])];
    copy[idx] = { ...copy[idx], [field]: val };
    updateField(key, copy);
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.profile.update({
        full_name: profile.full_name,
        email: profile.email,
        phone: profile.phone,
        address: profile.address,
        city: profile.city,
        state: profile.state,
        country: profile.country,
        postal_code: profile.postal_code,
        college: profile.college,
        degree: profile.degree,
        branch: profile.branch,
        current_semester: profile.current_semester,
        graduation_year: profile.graduation_year,
        cgpa: profile.cgpa,
        school_education: profile.school_education,
        technical_skills: csvToList(skillsText),
        programming_languages: csvToList(langsText),
        projects: profile.projects,
        work_experience: profile.work_experience,
        internships: profile.internships,
        certifications: profile.certifications,
        achievements: csvToList(achievementsText),
        github_url: profile.github_url,
        linkedin_url: profile.linkedin_url,
        portfolio_url: profile.portfolio_url,
        preferred_roles: csvToList(rolesText),
        preferred_locations: csvToList(locationsText),
        work_mode_preference: profile.work_mode_preference,
        internship_duration: profile.internship_duration,
        availability: profile.availability,
        preferred_resume_id: profile.preferred_resume_id,
        team_name: profile.team_name,
        team_members: csvToList(teamMembersText),
        hackathon_project_idea: profile.hackathon_project_idea,
        hackathon_tech_stack: csvToList(hackStackText),
        hackathon_repo_url: profile.hackathon_repo_url,
        hackathon_project_description: profile.hackathon_project_description,
      });
      setProfile(updated);
      setMessage("Profile saved and verified.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <RequireAuth>
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">My Profile</h1>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Verified facts here power deterministic form filling. Empty fields stay blank and are never fabricated.
            </p>
          </div>
          {profile && (
            <Badge tone="blue">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {Object.values(profile.verified_fields ?? {}).filter(Boolean).length} verified fields
            </Badge>
          )}
        </div>

        {message && <Alert tone="success">{message}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}

        {loading || !profile ? (
          <Card>Loading profile...</Card>
        ) : (
          <form onSubmit={handleSave} className="space-y-6">
            <Card className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Personal Information</h2>
                <VerificationTag value={profile.phone} verified={profile.verified_fields?.phone} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Full Name" value={profile.full_name ?? ""} onChange={(e) => updateField("full_name", e.target.value)} />
                <Input label="Email" type="email" value={profile.email ?? ""} onChange={(e) => updateField("email", e.target.value)} />
                <Input label="Phone Number" value={profile.phone ?? ""} onChange={(e) => updateField("phone", e.target.value)} />
                <Input label="Street Address" value={profile.address ?? ""} onChange={(e) => updateField("address", e.target.value)} />
                <Input label="City" value={profile.city ?? ""} onChange={(e) => updateField("city", e.target.value)} />
                <Input label="State / Province" value={profile.state ?? ""} onChange={(e) => updateField("state", e.target.value)} />
                <Input label="Country" value={profile.country ?? ""} onChange={(e) => updateField("country", e.target.value)} />
                <Input label="Postal Code" value={profile.postal_code ?? ""} onChange={(e) => updateField("postal_code", e.target.value)} />
              </div>
            </Card>

            <Card className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Education</h2>
                <VerificationTag value={profile.college} verified={profile.verified_fields?.college} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="College / University" value={profile.college ?? ""} onChange={(e) => updateField("college", e.target.value)} />
                <Input label="Degree" placeholder="B.Tech, B.Sc, M.Tech..." value={profile.degree ?? ""} onChange={(e) => updateField("degree", e.target.value)} />
                <Input label="Branch / Specialization" value={profile.branch ?? ""} onChange={(e) => updateField("branch", e.target.value)} />
                <Input label="Current Semester" value={profile.current_semester ?? ""} onChange={(e) => updateField("current_semester", e.target.value)} />
                <Input label="Graduation Year" value={profile.graduation_year ?? ""} onChange={(e) => updateField("graduation_year", e.target.value)} />
                <Input label="CGPA / Percentage" value={profile.cgpa ?? ""} onChange={(e) => updateField("cgpa", e.target.value)} />
                <Input
                  label="High School / 12th Board & Score"
                  value={profile.school_education?.high_school ?? ""}
                  onChange={(e) =>
                    updateField("school_education", { ...(profile.school_education ?? {}), high_school: e.target.value })
                  }
                />
                <Input
                  label="Secondary / 10th Board & Score"
                  value={profile.school_education?.secondary_school ?? ""}
                  onChange={(e) =>
                    updateField("school_education", { ...(profile.school_education ?? {}), secondary_school: e.target.value })
                  }
                />
              </div>
            </Card>

            <Card className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Professional Links &amp; Skills</h2>
                <VerificationTag value={profile.github_url} verified={profile.verified_fields?.github_url} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Technical Skills (comma-separated)" value={skillsText} onChange={(e) => setSkillsText(e.target.value)} placeholder="FastAPI, Next.js, Docker" />
                <Input label="Programming Languages (comma-separated)" value={langsText} onChange={(e) => setLangsText(e.target.value)} placeholder="Python, TypeScript, SQL" />
                <Input label="GitHub Profile URL" type="url" value={profile.github_url ?? ""} onChange={(e) => updateField("github_url", e.target.value)} />
                <Input label="LinkedIn Profile URL" type="url" value={profile.linkedin_url ?? ""} onChange={(e) => updateField("linkedin_url", e.target.value)} />
                <Input label="Portfolio Website" type="url" value={profile.portfolio_url ?? ""} onChange={(e) => updateField("portfolio_url", e.target.value)} />
                <Input label="Achievements (comma-separated)" value={achievementsText} onChange={(e) => setAchievementsText(e.target.value)} />
              </div>

              {(
                [
                  { key: "projects", label: "Projects", fields: ["title", "summary", "link"] },
                  { key: "internships", label: "Internships", fields: ["company", "role", "duration"] },
                  { key: "work_experience", label: "Work Experience", fields: ["company", "role", "duration"] },
                  { key: "certifications", label: "Certifications", fields: ["name", "issuer", "year"] },
                ] as const
              ).map((section) => (
                <div key={section.key} className="space-y-2 border-t border-slate-200 pt-4 dark:border-slate-800">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{section.label}</h3>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        addStructuredItem(section.key, {
                          [section.fields[0]]: "",
                          [section.fields[1]]: "",
                          [section.fields[2]]: "",
                        })
                      }
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Add
                    </Button>
                  </div>
                  {(profile[section.key] ?? []).map((item, idx) => (
                    <div key={idx} className="grid gap-2 sm:grid-cols-4 items-end">
                      {section.fields.map((f) => (
                        <Input
                          key={f}
                          label={f.charAt(0).toUpperCase() + f.slice(1)}
                          value={item[f] ?? ""}
                          onChange={(e) => updateStructuredField(section.key, idx, f, e.target.value)}
                        />
                      ))}
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label={`Remove ${section.label} item ${idx + 1}`}
                        onClick={() => removeStructuredItem(section.key, idx)}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    </div>
                  ))}
                </div>
              ))}
            </Card>

            <Card className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Application Preferences</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Preferred Roles (comma-separated)" value={rolesText} onChange={(e) => setRolesText(e.target.value)} />
                <Input label="Preferred Locations (comma-separated)" value={locationsText} onChange={(e) => setLocationsText(e.target.value)} />
                <div className="space-y-1.5">
                  <label htmlFor="work_mode" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                    Remote or Onsite Preference
                  </label>
                  <select
                    id="work_mode"
                    value={profile.work_mode_preference ?? ""}
                    onChange={(e) => updateField("work_mode_preference", e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                  >
                    <option value="">Unspecified</option>
                    <option value="remote">Remote</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="onsite">Onsite</option>
                    <option value="any">Any</option>
                  </select>
                </div>
                <Input label="Internship Duration" value={profile.internship_duration ?? ""} onChange={(e) => updateField("internship_duration", e.target.value)} placeholder="2-6 months" />
                <Input label="Availability" value={profile.availability ?? ""} onChange={(e) => updateField("availability", e.target.value)} placeholder="Immediate / May 2027" />
                <div className="space-y-1.5">
                  <label htmlFor="preferred_resume" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                    Preferred Resume
                  </label>
                  <select
                    id="preferred_resume"
                    value={profile.preferred_resume_id ?? ""}
                    onChange={(e) => updateField("preferred_resume_id", e.target.value || null)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                  >
                    <option value="">None selected</option>
                    {resumes.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.label} ({r.original_filename})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </Card>

            <Card className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Hackathon Information</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Team Name" value={profile.team_name ?? ""} onChange={(e) => updateField("team_name", e.target.value)} />
                <Input label="Team Members (comma-separated)" value={teamMembersText} onChange={(e) => setTeamMembersText(e.target.value)} />
                <Input label="Technology Stack (comma-separated)" value={hackStackText} onChange={(e) => setHackStackText(e.target.value)} />
                <Input label="GitHub Repository URL" type="url" value={profile.hackathon_repo_url ?? ""} onChange={(e) => updateField("hackathon_repo_url", e.target.value)} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor="hack_idea" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                    Project Idea
                  </label>
                  <textarea
                    id="hack_idea"
                    rows={3}
                    value={profile.hackathon_project_idea ?? ""}
                    onChange={(e) => updateField("hackathon_project_idea", e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                  />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="hack_desc" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                    Project Description
                  </label>
                  <textarea
                    id="hack_desc"
                    rows={3}
                    value={profile.hackathon_project_description ?? ""}
                    onChange={(e) => updateField("hackathon_project_description", e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                  />
                </div>
              </div>
            </Card>

            <div className="flex justify-end">
              <Button type="submit" size="lg" loading={saving}>
                <Save className="h-4 w-4" />
                Save Verified Profile
              </Button>
            </div>
          </form>
        )}
      </div>
    </RequireAuth>
  );
}

