"use client";

import { Bookmark } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CandidateCard } from "@/components/candidates/candidate-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSaved } from "@/hooks/use-api";

export default function SavedPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useSaved(page);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Saved candidates</h1>
        <p className="text-sm text-muted-foreground">
          Your shortlist across all searches.
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-52 rounded-xl" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.items.map((saved, index) => (
              <div key={saved.id} className="space-y-2">
                <CandidateCard candidate={saved.candidate} saved index={index} />
                {saved.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 px-1">
                    {saved.tags.map((tag) => (
                      <Badge key={tag} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
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
        </>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
            <Bookmark className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Nothing saved yet. Save promising candidates from your search results.
            </p>
            <Button asChild>
              <Link href="/search">Find candidates</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
