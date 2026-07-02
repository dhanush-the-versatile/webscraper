import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CandidateCard } from "@/components/candidates/candidate-card";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { Candidate, ScoreBreakdown } from "@/types/api";

const candidate: Candidate = {
  id: "c1",
  full_name: "Ada Lovelace",
  headline: "Senior React Engineer",
  company: "Analytical Engines",
  industry: null,
  seniority: "senior",
  years_experience: 7,
  country: "United Kingdom",
  city: "London",
  avatar_url: null,
  linkedin_url: "https://linkedin.com/in/ada",
  github_url: "https://github.com/ada",
  portfolio_url: null,
  website_url: null,
  technologies: ["react", "typescript", "graphql"],
};

const scores: ScoreBreakdown = {
  overall_score: 87.5,
  skill_match: 100,
  experience_match: 90,
  technology_match: 80,
  location_match: 100,
  portfolio_score: 40,
  github_activity_score: 70,
  relevance_score: 88,
};

function renderCard(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>{ui}</TooltipProvider>
    </QueryClientProvider>,
  );
}

describe("CandidateCard", () => {
  it("renders identity, score, skills, and profile links", () => {
    renderCard(
      <CandidateCard candidate={candidate} scores={scores} rank={1} matchedSkills={["react"]} />,
    );

    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("Senior React Engineer")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByLabelText(/Overall score 88/)).toBeInTheDocument();
    expect(screen.getByText("react")).toBeInTheDocument();
    expect(screen.getByLabelText("LinkedIn")).toHaveAttribute(
      "href",
      "https://linkedin.com/in/ada",
    );
    expect(screen.getByLabelText("GitHub")).toHaveAttribute("href", "https://github.com/ada");
    expect(screen.queryByLabelText("Portfolio")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ada Lovelace" })).toHaveAttribute(
      "href",
      "/candidates/c1",
    );
  });

  it("shows saved state when saved", () => {
    renderCard(<CandidateCard candidate={candidate} saved />);
    expect(screen.getByRole("button", { name: /saved/i })).toBeInTheDocument();
  });
});
