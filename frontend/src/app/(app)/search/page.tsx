"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Download, Filter, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { CandidateCard } from "@/components/candidates/candidate-card";
import { SearchProgress } from "@/components/search/search-progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateSearch,
  useExport,
  useSearch,
  useSearchResults,
} from "@/hooks/use-api";
import type { ExportFormat } from "@/types/api";

const EXAMPLES = [
  "Find React developers with 5+ years experience in Germany",
  "Looking for AI Engineers with LangGraph and RAG experience",
  "Need Python freelancers experienced in FastAPI",
  "Looking for UI Designers specializing in FinTech",
];

const schema = z.object({
  query: z.string().min(10, "Describe the role in a bit more detail (10+ characters)."),
});

type FormValues = z.infer<typeof schema>;

function RequirementChips({ requirement }: { requirement: Record<string, unknown> }) {
  const chips = useMemo(() => {
    const output: { label: string; value: string }[] = [];
    const push = (label: string, value: unknown) => {
      if (Array.isArray(value) && value.length > 0) {
        output.push({ label, value: value.slice(0, 4).join(", ") });
      } else if (typeof value === "string" && value) {
        output.push({ label, value });
      } else if (typeof value === "number") {
        output.push({ label, value: String(value) });
      }
    };
    push("Titles", requirement.job_titles);
    push("Skills", requirement.skills);
    push("Frameworks", requirement.frameworks);
    push("Languages", requirement.programming_languages);
    push("Seniority", requirement.seniority);
    push("Min years", requirement.min_years_experience);
    push("Location", [
      ...((requirement.cities as string[]) ?? []),
      ...((requirement.countries as string[]) ?? []),
    ]);
    push("Industry", requirement.industries);
    return output;
  }, [requirement]);

  if (chips.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
        <Sparkles className="h-3.5 w-3.5 text-primary" /> AI understood:
      </span>
      {chips.map((chip) => (
        <Badge key={chip.label} variant="outline" className="font-normal">
          <span className="mr-1 text-muted-foreground">{chip.label}:</span> {chip.value}
        </Badge>
      ))}
    </div>
  );
}

export default function SearchPage() {
  const [activeSearchId, setActiveSearchId] = useState<string | null>(null);
  const [minScore, setMinScore] = useState<number | undefined>(undefined);

  const createSearch = useCreateSearch();
  const { data: search } = useSearch(activeSearchId);
  const completed = search?.status === "completed";
  const { data: detail, isLoading: resultsLoading } = useSearchResults(
    completed ? activeSearchId : null,
    minScore,
  );
  const exporter = useExport();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    const created = await createSearch.mutateAsync({ query: values.query, max_results: 30 });
    setMinScore(undefined);
    setActiveSearchId(created.id);
  });

  const results = detail?.results ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Find talent</h1>
        <p className="text-sm text-muted-foreground">
          Describe who you need in plain language — the AI parses it, searches public
          sources, and ranks the results.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-3 p-5">
          <form onSubmit={onSubmit} className="space-y-3">
            <Textarea
              rows={3}
              placeholder='e.g. "Find senior React developers with TypeScript and 5+ years in Berlin"'
              className="resize-none text-base"
              {...register("query")}
            />
            {errors.query && <p className="text-xs text-destructive">{errors.query.message}</p>}
            <div className="flex flex-wrap items-center gap-2">
              <Button type="submit" disabled={createSearch.isPending}>
                <Sparkles /> {createSearch.isPending ? "Starting…" : "Search candidates"}
              </Button>
              <span className="text-xs text-muted-foreground">Try:</span>
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setValue("query", example, { shouldValidate: true })}
                  className="rounded-full border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                >
                  {example}
                </button>
              ))}
            </div>
          </form>
        </CardContent>
      </Card>

      {search && !completed && <SearchProgress search={search} />}

      {search && completed && (
        <div className="space-y-4">
          <SearchProgress search={search} />
          <RequirementChips requirement={search.parsed_requirement} />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">
              {search.result_count} candidate{search.result_count === 1 ? "" : "s"} found
            </h2>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select
                value={minScore !== undefined ? String(minScore) : "all"}
                onValueChange={(value) =>
                  setMinScore(value === "all" ? undefined : Number(value))
                }
              >
                <SelectTrigger className="w-36">
                  <SelectValue placeholder="Min score" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All scores</SelectItem>
                  <SelectItem value="80">80+ excellent</SelectItem>
                  <SelectItem value="60">60+ strong</SelectItem>
                  <SelectItem value="40">40+ possible</SelectItem>
                </SelectContent>
              </Select>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" disabled={exporter.isPending}>
                    <Download /> Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Format</DropdownMenuLabel>
                  {(["csv", "xlsx", "pdf", "json"] as ExportFormat[]).map((format) => (
                    <DropdownMenuItem
                      key={format}
                      onSelect={() =>
                        exporter.mutate({ search_id: search.id, format })
                      }
                    >
                      {format.toUpperCase()}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {resultsLoading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-56 rounded-xl" />
              ))}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {results.map((result, index) => (
                <CandidateCard
                  key={result.id}
                  candidate={result.candidate}
                  scores={result.scores}
                  rank={result.rank}
                  summary={result.summary}
                  matchedSkills={result.matched_skills}
                  index={index}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
