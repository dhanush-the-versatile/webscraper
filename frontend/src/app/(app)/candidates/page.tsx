"use client";

import { Filter, Search as SearchIcon, X } from "lucide-react";
import { useMemo, useState } from "react";

import { CandidateCard } from "@/components/candidates/candidate-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useCandidates, type CandidateFilters } from "@/hooks/use-api";

function useDebounced<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);
  useMemo(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export default function CandidatesPage() {
  const [keyword, setKeyword] = useState("");
  const [skillInput, setSkillInput] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [country, setCountry] = useState("");
  const [minYears, setMinYears] = useState("");
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  const debouncedKeyword = useDebounced(keyword);

  const filters: CandidateFilters = useMemo(
    () => ({
      q: debouncedKeyword || undefined,
      skills: skills.length ? skills : undefined,
      countries: country ? [country] : undefined,
      min_years_experience: minYears ? Number(minYears) : undefined,
    }),
    [debouncedKeyword, skills, country, minYears],
  );

  const { data, isLoading } = useCandidates(filters, page);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  const addSkill = () => {
    const value = skillInput.trim().toLowerCase();
    if (value && !skills.includes(value)) setSkills((current) => [...current, value]);
    setSkillInput("");
    setPage(1);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Candidate pool</h1>
        <p className="text-sm text-muted-foreground">
          Everyone collected across your searches — filter and browse.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={keyword}
                onChange={(event) => {
                  setKeyword(event.target.value);
                  setPage(1);
                }}
                placeholder="Search by name, headline, company, bio…"
                className="pl-9"
              />
            </div>
            <Button
              variant={showFilters ? "secondary" : "outline"}
              onClick={() => setShowFilters((current) => !current)}
            >
              <Filter /> Filters
            </Button>
          </div>

          {showFilters && (
            <div className="grid gap-4 border-t pt-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label>Skills (press Enter)</Label>
                <Input
                  value={skillInput}
                  onChange={(event) => setSkillInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      addSkill();
                    }
                  }}
                  placeholder="react, python…"
                />
                {skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {skills.map((skill) => (
                      <Badge key={skill} variant="secondary" className="gap-1">
                        {skill}
                        <button
                          aria-label={`Remove ${skill}`}
                          onClick={() => {
                            setSkills((current) => current.filter((item) => item !== skill));
                            setPage(1);
                          }}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <div className="space-y-1.5">
                <Label>Country</Label>
                <Input
                  value={country}
                  onChange={(event) => {
                    setCountry(event.target.value);
                    setPage(1);
                  }}
                  placeholder="Germany"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Min years of experience</Label>
                <Input
                  type="number"
                  min={0}
                  max={60}
                  value={minYears}
                  onChange={(event) => {
                    setMinYears(event.target.value);
                    setPage(1);
                  }}
                  placeholder="5"
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-52 rounded-xl" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.items.map((candidate, index) => (
              <CandidateCard key={candidate.id} candidate={candidate} index={index} />
            ))}
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {data.total} candidate{data.total === 1 ? "" : "s"} · page {data.page} of{" "}
              {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((current) => current - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No candidates match these filters yet. Run a search to grow the pool.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
