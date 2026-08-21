import type { PaginatedResponse } from "../types/api";

/**
 * The FastAPI backend returns list endpoints as
 *   { items: [...], total, limit, offset, has_more }
 * while the frontend's PaginatedResponse<T> declares `data: T[]`.
 *
 * Every list page read `response.data ?? []`, got undefined, and rendered an
 * empty state even though the API had returned rows. Normalising here fixes
 * all of them at once and keeps the components and query keys untouched.
 *
 * Tolerates three wire shapes: `{items}` (this backend), `{data}` (the shape
 * the frontend was written against), and a bare array.
 */
export function normalizeList<T>(body: unknown): PaginatedResponse<T> {
  if (Array.isArray(body)) {
    return { data: body as T[], total: body.length, limit: body.length, offset: 0, has_more: false };
  }

  const raw = (body ?? {}) as Record<string, unknown>;
  const items = (Array.isArray(raw["items"]) ? raw["items"] : Array.isArray(raw["data"]) ? raw["data"] : []) as T[];

  return {
    data: items,
    total: typeof raw["total"] === "number" ? raw["total"] : items.length,
    limit: typeof raw["limit"] === "number" ? raw["limit"] : items.length,
    offset: typeof raw["offset"] === "number" ? raw["offset"] : 0,
    has_more: raw["has_more"] === true,
  };
}

/**
 * Same idea for endpoints that wrap their array under a domain-specific key,
 * e.g. GET /api/v1/agents/status -> { agents: [...], window_hours, ... }.
 */
export function unwrapArray<T>(body: unknown, key: string): T[] {
  if (Array.isArray(body)) return body as T[];
  const raw = (body ?? {}) as Record<string, unknown>;
  for (const candidate of [key, "items", "data"]) {
    if (Array.isArray(raw[candidate])) return raw[candidate] as T[];
  }
  return [];
}
