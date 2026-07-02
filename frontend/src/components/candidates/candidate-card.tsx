"use client";

import { motion } from "framer-motion";
import {
  Bookmark,
  BookmarkCheck,
  Briefcase,
  ExternalLink,
  Github,
  Globe,
  Linkedin,
  MapPin,
} from "lucide-react";
import Link from "next/link";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useSaveCandidate, useUnsaveCandidate } from "@/hooks/use-api";
import { cn, initials, scoreTone } from "@/lib/utils";
import type { Candidate, ScoreBreakdown } from "@/types/api";

function ScoreRing({ score }: { score: number }) {
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const filled = (score / 100) * circumference;
  return (
    <div className="relative h-12 w-12 shrink-0" aria-label={`Overall score ${Math.round(score)} out of 100`}>
      <svg viewBox="0 0 48 48" className="h-12 w-12 -rotate-90">
        <circle cx="24" cy="24" r={radius} fill="none" strokeWidth="4" className="stroke-muted" />
        <circle
          cx="24"
          cy="24"
          r={radius}
          fill="none"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference - filled}`}
          className="stroke-current text-primary"
        />
      </svg>
      <span
        className={cn(
          "absolute inset-0 flex items-center justify-center text-xs font-semibold",
          scoreTone(score),
        )}
      >
        {Math.round(score)}
      </span>
    </div>
  );
}

function ProfileLink({
  href,
  label,
  children,
}: {
  href: string | null;
  label: string;
  children: React.ReactNode;
}) {
  if (!href) return null;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button asChild variant="outline" size="icon" className="h-8 w-8">
          <a href={href} target="_blank" rel="noopener noreferrer" aria-label={label}>
            {children}
          </a>
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

interface CandidateCardProps {
  candidate: Candidate;
  scores?: ScoreBreakdown;
  rank?: number;
  summary?: string | null;
  matchedSkills?: string[];
  saved?: boolean;
  index?: number;
}

export function CandidateCard({
  candidate,
  scores,
  rank,
  summary,
  matchedSkills = [],
  saved = false,
  index = 0,
}: CandidateCardProps) {
  const save = useSaveCandidate();
  const unsave = useUnsaveCandidate();
  const isSaved = saved || save.isSuccess;
  const location = [candidate.city, candidate.country].filter(Boolean).join(", ");
  const matched = new Set(matchedSkills.map((skill) => skill.toLowerCase()));

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(index * 0.04, 0.4) }}
    >
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardContent className="flex h-full flex-col gap-3 p-4">
          <div className="flex items-start gap-3">
            <Avatar className="h-11 w-11">
              <AvatarImage src={candidate.avatar_url ?? undefined} alt="" />
              <AvatarFallback>{initials(candidate.full_name)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                {rank !== undefined && (
                  <span className="text-xs font-semibold text-muted-foreground">#{rank}</span>
                )}
                <Link
                  href={`/candidates/${candidate.id}`}
                  className="truncate font-semibold hover:underline"
                >
                  {candidate.full_name}
                </Link>
              </div>
              <p className="truncate text-sm text-muted-foreground">
                {candidate.headline ?? "—"}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                {candidate.company && (
                  <span className="inline-flex items-center gap-1">
                    <Briefcase className="h-3 w-3" /> {candidate.company}
                  </span>
                )}
                {location && (
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="h-3 w-3" /> {location}
                  </span>
                )}
                {candidate.years_experience !== null && (
                  <span>{candidate.years_experience} yrs</span>
                )}
              </div>
            </div>
            {scores && <ScoreRing score={scores.overall_score} />}
          </div>

          {summary && <p className="line-clamp-2 text-sm text-muted-foreground">{summary}</p>}

          {candidate.technologies.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {candidate.technologies.slice(0, 6).map((tech) => (
                <Badge
                  key={tech}
                  variant={matched.has(tech.toLowerCase()) ? "success" : "secondary"}
                >
                  {tech}
                </Badge>
              ))}
              {candidate.technologies.length > 6 && (
                <Badge variant="outline">+{candidate.technologies.length - 6}</Badge>
              )}
            </div>
          )}

          <div className="mt-auto flex items-center gap-1.5 pt-1">
            <ProfileLink href={candidate.linkedin_url} label="LinkedIn">
              <Linkedin />
            </ProfileLink>
            <ProfileLink href={candidate.github_url} label="GitHub">
              <Github />
            </ProfileLink>
            <ProfileLink href={candidate.portfolio_url} label="Portfolio">
              <Globe />
            </ProfileLink>
            <ProfileLink href={candidate.website_url} label="Website">
              <ExternalLink />
            </ProfileLink>
            <div className="ml-auto">
              <Button
                variant={isSaved ? "secondary" : "outline"}
                size="sm"
                disabled={save.isPending || unsave.isPending}
                onClick={() =>
                  isSaved
                    ? unsave.mutate(candidate.id, { onSuccess: () => save.reset() })
                    : save.mutate({ candidate_id: candidate.id })
                }
              >
                {isSaved ? <BookmarkCheck /> : <Bookmark />}
                {isSaved ? "Saved" : "Save"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
