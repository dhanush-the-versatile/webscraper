"use client";

import {
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  Briefcase,
  ExternalLink,
  Github,
  Globe,
  Linkedin,
  Mail,
  MapPin,
  Star,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  useCandidate,
  useCreateNote,
  useDeleteNote,
  useNotes,
  useSaveCandidate,
  useUnsaveCandidate,
} from "@/hooks/use-api";
import { formatDate, formatDateTime, initials } from "@/lib/utils";

function LinkButton({ href, icon: Icon, label }: { href: string | null; icon: React.ElementType; label: string }) {
  if (!href) return null;
  return (
    <Button asChild variant="outline" size="sm">
      <a href={href} target="_blank" rel="noopener noreferrer">
        <Icon /> {label}
      </a>
    </Button>
  );
}

function NotesPanel({ candidateId }: { candidateId: string }) {
  const { data: notes, isLoading } = useNotes(candidateId);
  const createNote = useCreateNote();
  const deleteNote = useDeleteNote(candidateId);
  const [body, setBody] = useState("");

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Textarea
          rows={3}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="Add a private note about this candidate…"
        />
        <Button
          size="sm"
          disabled={!body.trim() || createNote.isPending}
          onClick={() =>
            createNote.mutate(
              { candidate_id: candidateId, body: body.trim() },
              { onSuccess: () => setBody("") },
            )
          }
        >
          Add note
        </Button>
      </div>
      {isLoading ? (
        <Skeleton className="h-16 w-full" />
      ) : notes && notes.length > 0 ? (
        <ul className="space-y-3">
          {notes.map((note) => (
            <li key={note.id} className="rounded-lg border p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="whitespace-pre-wrap text-sm">{note.body}</p>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
                  aria-label="Delete note"
                  onClick={() => deleteNote.mutate(note.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {formatDateTime(note.created_at)}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No notes yet.</p>
      )}
    </div>
  );
}

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data: candidate, isLoading, error } = useCandidate(params.id);
  const save = useSaveCandidate();
  const unsave = useUnsaveCandidate();
  const isSaved = save.isSuccess;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 py-12 text-center">
        <p className="text-muted-foreground">Candidate not found.</p>
        <Button variant="outline" onClick={() => router.back()}>
          <ArrowLeft /> Go back
        </Button>
      </div>
    );
  }

  const location = [candidate.city, candidate.country].filter(Boolean).join(", ");
  const stats = candidate.github_stats ?? {};

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2 text-muted-foreground">
        <Link href="/candidates">
          <ArrowLeft /> All candidates
        </Link>
      </Button>

      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap items-start gap-4">
            <Avatar className="h-16 w-16">
              <AvatarImage src={candidate.avatar_url ?? undefined} alt="" />
              <AvatarFallback className="text-lg">{initials(candidate.full_name)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-semibold">{candidate.full_name}</h1>
              <p className="text-muted-foreground">{candidate.headline ?? "—"}</p>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                {candidate.company && (
                  <span className="inline-flex items-center gap-1.5">
                    <Briefcase className="h-4 w-4" /> {candidate.company}
                  </span>
                )}
                {location && (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="h-4 w-4" /> {location}
                  </span>
                )}
                {candidate.years_experience !== null && (
                  <span>{candidate.years_experience} years experience</span>
                )}
                {candidate.public_email && (
                  <a
                    href={`mailto:${candidate.public_email}`}
                    className="inline-flex items-center gap-1.5 hover:text-foreground"
                  >
                    <Mail className="h-4 w-4" /> {candidate.public_email}
                  </a>
                )}
              </div>
            </div>
            <Button
              variant={isSaved ? "secondary" : "default"}
              disabled={save.isPending || unsave.isPending}
              onClick={() =>
                isSaved
                  ? unsave.mutate(candidate.id, { onSuccess: () => save.reset() })
                  : save.mutate({ candidate_id: candidate.id })
              }
            >
              {isSaved ? <BookmarkCheck /> : <Bookmark />}
              {isSaved ? "Saved" : "Save candidate"}
            </Button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <LinkButton href={candidate.linkedin_url} icon={Linkedin} label="LinkedIn" />
            <LinkButton href={candidate.github_url} icon={Github} label="GitHub" />
            <LinkButton href={candidate.portfolio_url} icon={Globe} label="Portfolio" />
            <LinkButton href={candidate.website_url} icon={ExternalLink} label="Website" />
          </div>

          {candidate.bio && (
            <>
              <Separator className="my-4" />
              <p className="whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                {candidate.bio}
              </p>
            </>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="sources">Sources ({candidate.sources.length})</TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Skills &amp; technologies</CardTitle>
            </CardHeader>
            <CardContent>
              {candidate.skills.length || candidate.technologies.length ? (
                <div className="flex flex-wrap gap-2">
                  {candidate.skills.map((skill) => (
                    <Badge key={skill.name} variant="secondary">
                      {skill.name}
                    </Badge>
                  ))}
                  {candidate.technologies
                    .filter((tech) => !candidate.skills.some((s) => s.name.toLowerCase() === tech))
                    .map((tech) => (
                      <Badge key={tech} variant="outline">
                        {tech}
                      </Badge>
                    ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No public skills detected.</p>
              )}
            </CardContent>
          </Card>

          {(stats.public_repos !== undefined || (stats.top_repos?.length ?? 0) > 0) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">GitHub activity</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-4 text-sm">
                  <span>
                    <strong className="tabular-nums">{stats.public_repos ?? 0}</strong>{" "}
                    <span className="text-muted-foreground">repos</span>
                  </span>
                  <span>
                    <strong className="tabular-nums">{stats.followers ?? 0}</strong>{" "}
                    <span className="text-muted-foreground">followers</span>
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Star className="h-3.5 w-3.5 text-amber-500" />
                    <strong className="tabular-nums">{stats.total_stars ?? 0}</strong>{" "}
                    <span className="text-muted-foreground">stars</span>
                  </span>
                </div>
                {stats.top_repos && stats.top_repos.length > 0 && (
                  <ul className="space-y-2">
                    {stats.top_repos.map((repo) => (
                      <li key={repo.url} className="rounded-md border p-3 text-sm">
                        <div className="flex items-center justify-between gap-2">
                          <a
                            href={repo.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium text-primary hover:underline"
                          >
                            {repo.name}
                          </a>
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                            <Star className="h-3 w-3" /> {repo.stars}
                            {repo.language && <span>· {repo.language}</span>}
                          </span>
                        </div>
                        {repo.description && (
                          <p className="mt-1 text-xs text-muted-foreground">{repo.description}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}

          {candidate.experiences.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Experience</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {candidate.experiences.map((experience) => (
                    <li key={experience.id} className="rounded-md border p-3 text-sm">
                      <p className="font-medium">
                        {experience.title ?? "Role"}{" "}
                        {experience.company && (
                          <span className="text-muted-foreground">@ {experience.company}</span>
                        )}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {experience.start_date ?? "?"} — {experience.is_current ? "present" : experience.end_date ?? "?"}
                      </p>
                      {experience.description && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {experience.description}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="sources">
          <Card>
            <CardContent className="p-4">
              <ul className="space-y-3">
                {candidate.sources.map((source) => (
                  <li key={source.id} className="rounded-md border p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="uppercase">
                        {source.source_type}
                      </Badge>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="truncate text-sm text-primary hover:underline"
                      >
                        {source.title ?? source.url}
                      </a>
                      <span className="ml-auto text-xs text-muted-foreground">
                        fetched {formatDate(source.fetched_at)}
                      </span>
                    </div>
                    {source.snippet && (
                      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                        {source.snippet}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-muted-foreground">
                Extraction confidence: {(candidate.extraction_confidence * 100).toFixed(0)}% ·
                Only publicly available information is shown.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notes">
          <Card>
            <CardContent className="p-4">
              <NotesPanel candidateId={candidate.id} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
