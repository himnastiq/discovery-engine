import { z } from 'zod';
import {
  ErrorResponseSchema,
  TypesResponseSchema,
  UsersResponseSchema,
  UserProfileResponseSchema,
  RecommendResponseSchema,
  ItemDetailSchema,
  SearchResponseSchema,
  MetricsResponseSchema,
  AboutResponseSchema,
  ChatStatusResponseSchema,
  ChatResponseSchema,
  type ColdStartRequest,
  type ChatRequest,
} from './schemas';
export type {
  TypesResponse,
  UsersResponse,
  UserProfileResponse,
  RecommendResponse,
  ItemDetail,
  SearchResponse,
  MetricsResponse,
  AboutResponse,
  ColdStartRequest,
  ChatRequest,
  ChatResponse,
  ChatStatusResponse,
} from './schemas';

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code: string = 'API_ERROR',
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiFetch<T>(
  schema: z.ZodType<T>,
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = path.startsWith('/api') ? path : `/api${path.startsWith('/') ? '' : '/'}${path}`;

  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err: unknown) {
    throw new ApiError(
      err instanceof Error ? err.message : 'Network request failed',
      0,
      'NETWORK_FAILURE',
      err
    );
  }

  let data: unknown;
  try {
    data = await res.json();
  } catch (err: unknown) {
    throw new ApiError(
      `Unexpected response from server: malformed JSON response from ${path}`,
      res.status || 502,
      'INVALID_JSON',
      err
    );
  }

  if (!res.ok) {
    const errorParsed = ErrorResponseSchema.safeParse(data);
    if (errorParsed.success) {
      throw new ApiError(
        errorParsed.data.error.message,
        res.status,
        errorParsed.data.error.code,
        errorParsed.data.error.details
      );
    }
    throw new ApiError(
      `API request failed with status ${res.status}`,
      res.status,
      'HTTP_ERROR',
      data
    );
  }

  const result = schema.safeParse(data);
  if (!result.success) {
    console.error(`[Zod ValidationError] Payload from ${path} did not match schema:`, result.error);
    throw new ApiError(
      `Unexpected response from server: ${result.error.issues[0]?.message || 'schema validation failed'}`,
      res.status,
      'SCHEMA_VALIDATION_ERROR',
      z.treeifyError(result.error)
    );
  }

  return result.data;
}

// ---------------------------------------------------------------------------
// Convenience client methods
// ---------------------------------------------------------------------------

export const apiClient = {
  getTypes: (signal?: AbortSignal) => apiFetch(TypesResponseSchema, '/api/types', { signal }),

  getUsers: (type: string, query?: string, signal?: AbortSignal) => {
    const q = query ? `?query=${encodeURIComponent(query)}` : '';
    return apiFetch(UsersResponseSchema, `/api/types/${encodeURIComponent(type)}/users${q}`, { signal });
  },

  getUserProfile: (type: string, userId: string, signal?: AbortSignal) =>
    apiFetch(
      UserProfileResponseSchema,
      `/api/types/${encodeURIComponent(type)}/users/${encodeURIComponent(userId)}/profile`,
      { signal }
    ),

  getRecommendations: (type: string, userId?: string, k: number = 10, signal?: AbortSignal) => {
    const params = new URLSearchParams();
    if (userId) params.set('user_id', userId);
    params.set('k', String(k));
    return apiFetch(
      RecommendResponseSchema,
      `/api/types/${encodeURIComponent(type)}/recommend?${params.toString()}`,
      { signal }
    );
  },

  getPopular: (type: string, k: number = 10, signal?: AbortSignal) =>
    apiFetch(
      RecommendResponseSchema,
      `/api/types/${encodeURIComponent(type)}/popular?k=${k}`,
      { signal }
    ),

  getSimilar: (type: string, itemId: string, k: number = 10, signal?: AbortSignal) =>
    apiFetch(
      RecommendResponseSchema,
      `/api/types/${encodeURIComponent(type)}/similar?item_id=${encodeURIComponent(itemId)}&k=${k}`,
      { signal }
    ),

  getItemDetail: (type: string, itemId: string, signal?: AbortSignal) =>
    apiFetch(
      ItemDetailSchema,
      `/api/types/${encodeURIComponent(type)}/items/${encodeURIComponent(itemId)}`,
      { signal }
    ),

  searchItems: (type: string, query: string, limit: number = 20, signal?: AbortSignal) =>
    apiFetch(
      SearchResponseSchema,
      `/api/types/${encodeURIComponent(type)}/search?q=${encodeURIComponent(query)}&limit=${limit}`,
      { signal }
    ),

  postColdStart: (request: ColdStartRequest, signal?: AbortSignal) =>
    apiFetch(RecommendResponseSchema, '/api/recommend/cold-start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal,
    }),

  getMetrics: (type: string, signal?: AbortSignal) =>
    apiFetch(
      MetricsResponseSchema,
      `/api/types/${encodeURIComponent(type)}/metrics`,
      { signal }
    ),

  getAbout: (signal?: AbortSignal) => apiFetch(AboutResponseSchema, '/api/about', { signal }),

  getChatStatus: (signal?: AbortSignal) =>
    apiFetch(ChatStatusResponseSchema, '/api/chat', { signal }),

  postChat: (request: ChatRequest, signal?: AbortSignal) =>
    apiFetch(ChatResponseSchema, '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal,
    }),
};
