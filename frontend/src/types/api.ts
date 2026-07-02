/** API contracts mirrored from the backend Pydantic schemas. */

export type UserRole = "admin" | "recruiter" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  auth_provider: "local" | "google" | "github";
  avatar_url: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type SearchStatus =
  | "pending"
  | "understanding"
  | "searching"
  | "collecting"
  | "ranking"
  | "completed"
  | "failed";

export type SourceType =
  | "linkedin"
  | "github"
  | "stackoverflow"
  | "kaggle"
  | "medium"
  | "devto"
  | "behance"
  | "dribbble"
  | "portfolio"
  | "company"
  | "research"
  | "search_engine"
  | "other";

export interface ParsedRequirement {
  job_titles: string[];
  skills: string[];
  technologies: string[];
  frameworks: string[];
  programming_languages: string[];
  seniority: string | null;
  min_years_experience: number | null;
  max_years_experience: number | null;
  countries: string[];
  cities: string[];
  industries: string[];
  companies: string[];
  education: string[];
  keywords: string[];
  employment_type: string | null;
  remote: boolean | null;
}

export interface GeneratedQuery {
  query: string;
  source: SourceType;
  rationale: string | null;
}

export interface Search {
  id: string;
  raw_query: string;
  status: SearchStatus;
  parsed_requirement: Partial<ParsedRequirement>;
  generated_queries: string[] | GeneratedQuery[];
  filters: Record<string, unknown>;
  result_count: number;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ScoreBreakdown {
  overall_score: number;
  skill_match: number;
  experience_match: number;
  technology_match: number;
  location_match: number;
  portfolio_score: number;
  github_activity_score: number;
  relevance_score: number;
}

export interface Candidate {
  id: string;
  full_name: string;
  headline: string | null;
  company: string | null;
  industry: string | null;
  seniority: string;
  years_experience: number | null;
  country: string | null;
  city: string | null;
  avatar_url: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  website_url: string | null;
  technologies: string[];
  public_email?: string | null;
  social_links?: Record<string, string>;
}

export interface SkillEntry {
  name: string;
  weight: number;
}

export interface Experience {
  id: string;
  company: string | null;
  title: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  duration_months: number | null;
  description: string | null;
}

export interface CandidateSource {
  id: string;
  source_type: SourceType;
  url: string;
  title: string | null;
  snippet: string | null;
  fetched_at: string | null;
}

export interface CandidateDetail extends Candidate {
  bio: string | null;
  github_stats: {
    public_repos?: number;
    followers?: number;
    total_stars?: number;
    top_repos?: {
      name: string;
      url: string;
      stars: number;
      language: string | null;
      description: string;
    }[];
  };
  extraction_confidence: number;
  created_at: string;
  skills: SkillEntry[];
  experiences: Experience[];
  sources: CandidateSource[];
}

export interface SearchResult {
  id: string;
  rank: number;
  candidate: Candidate;
  scores: ScoreBreakdown;
  summary: string | null;
  explanation: string | null;
  matched_skills: string[];
  missing_skills: string[];
}

export interface SearchDetail extends Search {
  results: SearchResult[];
}

export interface SavedCandidate {
  id: string;
  candidate: Candidate;
  tags: string[];
  created_at: string;
}

export interface Note {
  id: string;
  candidate_id: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface HistoryEvent {
  id: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface CountPoint {
  label: string;
  value: number;
}

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

export interface AnalyticsOverview {
  total_searches: number;
  completed_searches: number;
  total_candidates: number;
  total_saved: number;
  avg_results_per_search: number;
  searches_over_time: TimeSeriesPoint[];
  top_skills: CountPoint[];
  top_countries: CountPoint[];
  top_technologies: CountPoint[];
  candidates_by_source: CountPoint[];
  score_distribution: CountPoint[];
}

export type ExportFormat = "csv" | "xlsx" | "pdf" | "json";

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> };
}
