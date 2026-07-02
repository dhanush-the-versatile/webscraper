"use client";

import { useAuthStore } from "@/store/auth";
import type { ApiErrorBody, TokenPair } from "@/types/api";

/**
 * Minimal typed API client with bearer auth and transparent refresh-on-401.
 * All calls go through the Next.js rewrite (`/api/backend/*`) so the browser
 * never needs CORS and the backend origin stays configurable server-side.
 */
const BASE = "/api/backend";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let code = "unknown_error";
  let message = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as ApiErrorBody;
    code = body.error?.code ?? code;
    message = body.error?.message ?? message;
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(response.status, code, message);
}

let refreshInFlight: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const { refreshToken, setTokens, logout } = useAuthStore.getState();
  if (!refreshToken) return false;
  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        logout();
        return false;
      }
      const pair = (await response.json()) as TokenPair;
      setTokens(pair.access_token, pair.refresh_token);
      return true;
    } catch {
      logout();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | string[] | undefined | null>;
  raw?: boolean; // return the Response (for file downloads)
}

async function request<T>(path: string, options: RequestOptions = {}, retried = false): Promise<T> {
  const { accessToken } = useAuthStore.getState();
  const url = new URL(`${BASE}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      value.forEach((item) => url.searchParams.append(key, String(item)));
    } else {
      url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url.toString(), {
    method: options.method ?? "GET",
    headers: {
      ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401 && !retried && (await tryRefresh())) {
    return request<T>(path, options, true);
  }
  if (!response.ok) throw await parseError(response);
  if (options.raw) return response as unknown as T;
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, params?: RequestOptions["params"]) =>
    request<T>(path, { params }),
  post: <T>(path: string, body?: unknown, params?: RequestOptions["params"]) =>
    request<T>(path, { method: "POST", body, params }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  download: (path: string, body?: unknown) =>
    request<Response>(path, { method: "POST", body, raw: true }),
};
