"use client";

import {
  Bookmark,
  BookmarkX,
  Download,
  History as HistoryIcon,
  LogIn,
  Search as SearchIcon,
  UserPlus,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHistory } from "@/hooks/use-api";
import { formatDateTime, labelForAction } from "@/lib/utils";

const ACTION_ICONS: Record<string, React.ElementType> = {
  "search.created": SearchIcon,
  "candidate.saved": Bookmark,
  "candidate.unsaved": BookmarkX,
  "export.created": Download,
  "user.register": UserPlus,
  "user.login": LogIn,
};

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useHistory(page);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Activity history</h1>
        <p className="text-sm text-muted-foreground">
          A trail of your searches, saves and exports.
        </p>
      </div>

      <Card>
        <CardContent className="p-4">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-12 w-full" />
              ))}
            </div>
          ) : data && data.items.length > 0 ? (
            <ul className="divide-y">
              {data.items.map((event) => {
                const Icon = ACTION_ICONS[event.action] ?? HistoryIcon;
                const meta = event.meta as { query?: string; format?: string };
                return (
                  <li key={event.id} className="flex items-center gap-3 py-3">
                    <span className="rounded-md bg-muted p-2 text-muted-foreground">
                      <Icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{labelForAction(event.action)}</p>
                      {(meta.query || meta.format) && (
                        <p className="truncate text-xs text-muted-foreground">
                          {meta.query ?? `Format: ${meta.format?.toUpperCase()}`}
                        </p>
                      )}
                    </div>
                    <time className="shrink-0 text-xs text-muted-foreground">
                      {formatDateTime(event.created_at)}
                    </time>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No activity recorded yet.
            </p>
          )}
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <div className="flex justify-end gap-2">
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
      )}
    </div>
  );
}
