"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import type {
  AnalyticsOverview,
  Candidate,
  CandidateDetail,
  ExportFormat,
  HistoryEvent,
  Note,
  Page,
  SavedCandidate,
  Search,
  SearchDetail,
  TokenPair,
  User,
} from "@/types/api";

/* ----------------------------- auth ----------------------------------- */

export function useLogin() {
  const { setTokens, setUser } = useAuthStore();
  return useMutation({
    mutationFn: async (payload: { email: string; password: string }) => {
      const tokens = await api.post<TokenPair>("/auth/login", payload);
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await api.get<User>("/auth/me");
      setUser(user);
      return user;
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (payload: { email: string; password: string; full_name?: string }) =>
      api.post<User>("/auth/register", payload),
  });
}

export function useCurrentUser() {
  const { accessToken, setUser } = useAuthStore();
  return useQuery({
    queryKey: ["me"],
    enabled: Boolean(accessToken),
    queryFn: async () => {
      const user = await api.get<User>("/auth/me");
      setUser(user);
      return user;
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { full_name?: string; password?: string }) =>
      api.patch<User>("/auth/me", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
}

/* ---------------------------- searches -------------------------------- */

export function useCreateSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { query: string; max_results?: number }) =>
      api.post<Search>("/searches", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["searches"] }),
  });
}

const ACTIVE_STATUSES = new Set([
  "pending",
  "understanding",
  "searching",
  "collecting",
  "ranking",
]);

export function useSearch(searchId: string | null) {
  return useQuery({
    queryKey: ["search", searchId],
    enabled: Boolean(searchId),
    queryFn: () => api.get<Search>(`/searches/${searchId}`),
    // poll while the pipeline is running
    refetchInterval: (query) =>
      query.state.data && ACTIVE_STATUSES.has(query.state.data.status) ? 1200 : false,
  });
}

export function useSearches(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["searches", page, pageSize],
    queryFn: () =>
      api.get<Page<Search>>("/searches", { page, page_size: pageSize }),
    placeholderData: keepPreviousData,
  });
}

export function useSearchResults(searchId: string | null, minScore?: number) {
  return useQuery({
    queryKey: ["search-results", searchId, minScore],
    enabled: Boolean(searchId),
    queryFn: () =>
      api.get<SearchDetail>(`/searches/${searchId}/results`, {
        page_size: 50,
        min_score: minScore,
      }),
  });
}

/* --------------------------- candidates ------------------------------- */

export type SearchMode = "keyword" | "semantic" | "hybrid";

export interface CandidateFilters {
  q?: string;
  mode?: SearchMode;
  skills?: string[];
  countries?: string[];
  cities?: string[];
  companies?: string[];
  technologies?: string[];
  min_years_experience?: number;
}

export function useCandidates(filters: CandidateFilters, page = 1, pageSize = 12) {
  return useQuery({
    queryKey: ["candidates", filters, page, pageSize],
    queryFn: () =>
      api.get<Page<Candidate>>("/candidates", {
        ...filters,
        page,
        page_size: pageSize,
      }),
    placeholderData: keepPreviousData,
  });
}

export function useCandidate(candidateId: string | null) {
  return useQuery({
    queryKey: ["candidate", candidateId],
    enabled: Boolean(candidateId),
    queryFn: () => api.get<CandidateDetail>(`/candidates/${candidateId}`),
  });
}

/* ------------------------------ saved --------------------------------- */

export function useSaved(page = 1, pageSize = 12) {
  return useQuery({
    queryKey: ["saved", page, pageSize],
    queryFn: () => api.get<Page<SavedCandidate>>("/saved", { page, page_size: pageSize }),
    placeholderData: keepPreviousData,
  });
}

export function useSaveCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { candidate_id: string; tags?: string[] }) =>
      api.post<SavedCandidate>("/saved", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved"] }),
  });
}

export function useUnsaveCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (candidateId: string) => api.delete(`/saved/${candidateId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved"] }),
  });
}

/* ------------------------------ notes --------------------------------- */

export function useNotes(candidateId: string | null) {
  return useQuery({
    queryKey: ["notes", candidateId],
    enabled: Boolean(candidateId),
    queryFn: () => api.get<Note[]>(`/notes/candidate/${candidateId}`),
  });
}

export function useCreateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { candidate_id: string; body: string }) =>
      api.post<Note>("/notes", payload),
    onSuccess: (note) =>
      queryClient.invalidateQueries({ queryKey: ["notes", note.candidate_id] }),
  });
}

export function useDeleteNote(candidateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (noteId: string) => api.delete(`/notes/${noteId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notes", candidateId] }),
  });
}

/* --------------------------- history/analytics ------------------------ */

export function useHistory(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["history", page, pageSize],
    queryFn: () => api.get<Page<HistoryEvent>>("/history", { page, page_size: pageSize }),
    placeholderData: keepPreviousData,
  });
}

export function useAnalytics(days = 30) {
  return useQuery({
    queryKey: ["analytics", days],
    queryFn: () => api.get<AnalyticsOverview>("/analytics", { days }),
  });
}

/* ------------------------------ export -------------------------------- */

export function useExport() {
  return useMutation({
    mutationFn: async (payload: { search_id: string; format: ExportFormat }) => {
      const response = await api.download("/exports", payload);
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") ?? "";
      const filename =
        /filename="?([^";]+)"?/.exec(disposition)?.[1] ??
        `candidates.${payload.format}`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      return filename;
    },
  });
}
