"use client";

import { ArrowRight, Bookmark, Search as SearchIcon, Users, Zap } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAnalytics, useSearches } from "@/hooks/use-api";
import { formatDateTime } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import type { SearchStatus } from "@/types/api";

const STATUS_BADGE: Record<SearchStatus, "success" | "warning" | "secondary" | "destructive"> = {
  completed: "success",
  failed: "destructive",
  pending: "secondary",
  understanding: "warning",
  searching: "warning",
  collecting: "warning",
  ranking: "warning",
};

function StatCard({
  title,
  value,
  icon: Icon,
  hint,
}: {
  title: string;
  value: number | string | undefined;
  icon: React.ElementType;
  hint?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{title}</p>
          {value === undefined ? (
            <Skeleton className="mt-1 h-7 w-16" />
          ) : (
            <p className="text-2xl font-semibold tabular-nums">{value}</p>
          )}
          {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const { data: analytics } = useAnalytics();
  const { data: recentSearches, isLoading: searchesLoading } = useSearches(1, 6);

  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Hi {firstName} 👋</h1>
          <p className="text-sm text-muted-foreground">
            Here&apos;s what&apos;s happening across your talent searches.
          </p>
        </div>
        <Button asChild>
          <Link href="/search">
            <SearchIcon /> New search
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total searches" value={analytics?.total_searches} icon={SearchIcon} />
        <StatCard
          title="Completed"
          value={analytics?.completed_searches}
          icon={Zap}
          hint={
            analytics ? `${analytics.avg_results_per_search} avg results / search` : undefined
          }
        />
        <StatCard title="Candidates in pool" value={analytics?.total_candidates} icon={Users} />
        <StatCard title="Saved candidates" value={analytics?.total_saved} icon={Bookmark} />
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Recent searches</CardTitle>
          <Button asChild variant="ghost" size="sm">
            <Link href="/history">
              View all <ArrowRight />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {searchesLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : recentSearches && recentSearches.items.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Query</TableHead>
                  <TableHead className="w-28">Status</TableHead>
                  <TableHead className="w-20 text-right">Results</TableHead>
                  <TableHead className="w-40">When</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentSearches.items.map((search) => (
                  <TableRow key={search.id}>
                    <TableCell className="max-w-md truncate font-medium">
                      {search.raw_query}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_BADGE[search.status]}>{search.status}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {search.result_count}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(search.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="py-10 text-center">
              <p className="text-sm text-muted-foreground">
                No searches yet — run your first one to build a talent pool.
              </p>
              <Button asChild className="mt-4">
                <Link href="/search">Start searching</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
