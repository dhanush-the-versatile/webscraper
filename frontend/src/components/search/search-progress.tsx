"use client";

import { motion } from "framer-motion";
import { Brain, CheckCircle2, Globe2, ListOrdered, Search, XCircle } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { Search as SearchType, SearchStatus } from "@/types/api";

const STAGES: { key: SearchStatus; label: string; icon: React.ElementType }[] = [
  { key: "understanding", label: "Understanding requirement", icon: Brain },
  { key: "searching", label: "Generating search queries", icon: Search },
  { key: "collecting", label: "Collecting public profiles", icon: Globe2 },
  { key: "ranking", label: "Ranking candidates", icon: ListOrdered },
];

const ORDER: SearchStatus[] = [
  "pending",
  "understanding",
  "searching",
  "collecting",
  "ranking",
  "completed",
];

export function SearchProgress({ search }: { search: SearchType }) {
  const position = ORDER.indexOf(search.status);
  const failed = search.status === "failed";
  const done = search.status === "completed";
  const percent = failed ? 100 : Math.max(6, (position / (ORDER.length - 1)) * 100);

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="truncate text-sm font-medium">“{search.raw_query}”</p>
          {done && <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />}
          {failed && <XCircle className="h-5 w-5 shrink-0 text-destructive" />}
        </div>
        <Progress
          value={percent}
          indicatorClassName={cn(failed && "bg-destructive", done && "bg-emerald-500")}
        />
        <ol className="grid gap-2 sm:grid-cols-4">
          {STAGES.map(({ key, label, icon: Icon }, index) => {
            const stagePosition = ORDER.indexOf(key);
            const isActive = search.status === key;
            const isDone = done || position > stagePosition;
            return (
              <li
                key={key}
                className={cn(
                  "flex items-center gap-2 rounded-md border px-3 py-2 text-xs",
                  isDone && "border-emerald-500/30 text-emerald-600 dark:text-emerald-400",
                  isActive && "border-primary/40 text-primary",
                  !isDone && !isActive && "text-muted-foreground",
                )}
              >
                {isActive ? (
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1.4, ease: "linear" }}
                    className="inline-flex"
                  >
                    <Icon className="h-3.5 w-3.5" />
                  </motion.span>
                ) : (
                  <Icon className="h-3.5 w-3.5" />
                )}
                <span className="leading-tight">
                  {index + 1}. {label}
                </span>
              </li>
            );
          })}
        </ol>
        {failed && (
          <p className="text-sm text-destructive">
            {search.error ?? "The search failed. Please try again."}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
