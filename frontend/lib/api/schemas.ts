import { z } from 'zod';

// ---------------------------------------------------------------------------
// Error Schemas
// ---------------------------------------------------------------------------

export const ErrorDetailSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.any().optional().nullable(),
});

export const ErrorResponseSchema = z.object({
  error: ErrorDetailSchema,
});

export type ErrorDetail = z.infer<typeof ErrorDetailSchema>;
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

// ---------------------------------------------------------------------------
// Health & Types Schemas
// ---------------------------------------------------------------------------

export const HealthTypeStatusSchema = z.object({
  available: z.boolean(),
  version: z.string().optional().nullable(),
  reason: z.string().optional().nullable(),
});

export const HealthResponseSchema = z.object({
  status: z.string(),
  types: z.record(z.string(), HealthTypeStatusSchema).default({}),
  version: z.string().default('1.0.0'),
});

export const TypeInfoSchema = z.object({
  id: z.string(),
  display_name: z.string(),
  card_type: z.enum(['movie', 'product', 'article']),
  supports_cold_start: z.boolean(),
  available: z.boolean().default(true).optional(),
  error: z.string().optional().nullable(),
  user_count: z.number().default(0),
  item_count: z.number().default(0),
  interaction_count: z.number().default(0),
});

export const TypesResponseSchema = z.object({
  types: z.array(TypeInfoSchema),
});

export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type TypeInfo = z.infer<typeof TypeInfoSchema>;
export type TypesResponse = z.infer<typeof TypesResponseSchema>;

// ---------------------------------------------------------------------------
// Users Schemas
// ---------------------------------------------------------------------------

export const UserSummarySchema = z.object({
  user_id: z.string(),
  persona: z.string().optional().nullable(),
  interaction_count: z.number().default(0),
  is_demo: z.boolean().default(false),
  top_categories: z.array(z.string()).default([]),
});

export const UsersResponseSchema = z.object({
  content_type: z.string(),
  total: z.number(),
  users: z.array(UserSummarySchema),
});

export const CategoryShareSchema = z.object({
  category: z.string(),
  count: z.number(),
  share: z.number(),
});

export const RecentInteractionSchema = z.object({
  item_id: z.string(),
  title: z.string(),
  signal: z.number().optional().nullable(),
  timestamp: z.union([z.number(), z.string()]).optional().nullable(),
});

export const UserProfileResponseSchema = z.object({
  user_id: z.string(),
  content_type: z.string(),
  persona: z.string().optional().nullable(),
  interaction_count: z.number(),
  positive_count: z.number(),
  first_activity: z.union([z.number(), z.string()]).optional().nullable(),
  last_activity: z.union([z.number(), z.string()]).optional().nullable(),
  top_categories: z.array(CategoryShareSchema).default([]),
  recent_items: z.array(RecentInteractionSchema).default([]),
});

export type UserSummary = z.infer<typeof UserSummarySchema>;
export type UsersResponse = z.infer<typeof UsersResponseSchema>;
export type UserProfileResponse = z.infer<typeof UserProfileResponseSchema>;

// ---------------------------------------------------------------------------
// Items & Search Schemas
// ---------------------------------------------------------------------------

export const ItemDetailSchema = z.object({
  item_id: z.string(),
  title: z.string(),
  subtitle: z.string().optional().nullable(),
  categories: z.array(z.string()).default([]),
  year: z.number().optional().nullable(),
  image_url: z.string().optional().nullable(),
  text: z.string().optional().nullable(),
  popularity_rank: z.number().optional().nullable(),
  meta: z.record(z.string(), z.any()).default({}),
});

export const SearchItemSchema = z.object({
  item_id: z.string(),
  title: z.string(),
  subtitle: z.string().optional().nullable(),
  categories: z.array(z.string()).default([]),
  year: z.number().optional().nullable(),
  image_url: z.string().optional().nullable(),
  popularity_rank: z.number().optional().nullable(),
  match_type: z.string().optional().nullable(),
});

export const SearchResponseSchema = z.object({
  content_type: z.string(),
  query: z.string(),
  total_matches: z.number(),
  results: z.array(SearchItemSchema),
});

export type ItemDetail = z.infer<typeof ItemDetailSchema>;
export type SearchItem = z.infer<typeof SearchItemSchema>;
export type SearchResponse = z.infer<typeof SearchResponseSchema>;

// ---------------------------------------------------------------------------
// Recommendations & Cold-Start Schemas
// ---------------------------------------------------------------------------

export const RecommendationReasonSchema = z.object({
  kind: z.string(),
  item_id: z.string().optional().nullable(),
  text: z.string().optional().nullable(),
  similarity_score: z.number().optional().nullable(),
});

export const ScoredItemResponseSchema = z.object({
  item_id: z.string(),
  title: z.string(),
  subtitle: z.string().optional().nullable(),
  categories: z.array(z.string()).default([]),
  year: z.number().optional().nullable(),
  image_url: z.string().optional().nullable(),
  score: z.number(),
  display_score: z.number(),
  reason: RecommendationReasonSchema.optional().nullable(),
  meta: z.record(z.string(), z.any()).default({}),
});

export const RecommendResponseSchema = z.object({
  content_type: z.string(),
  user_id: z.string().optional().nullable(),
  query_item_id: z.string().optional().nullable(),
  mode: z.enum(['personalized', 'popularity']).optional().default('popularity'),
  k: z.number(),
  results: z.array(ScoredItemResponseSchema),
  meta: z.record(z.string(), z.any()).default({}),
});

export const ColdStartHistoryItemSchema = z.object({
  item_id: z.string(),
  signal: z.number().min(0).max(5).optional().nullable(),
});

export const ColdStartRequestSchema = z.object({
  type: z.string(),
  history: z.array(ColdStartHistoryItemSchema).max(200),
  exclude: z.array(z.string()).default([]),
  k: z.number().int().min(1).max(50).default(10),
});

export type RecommendationReason = z.infer<typeof RecommendationReasonSchema>;
export type ScoredItem = z.infer<typeof ScoredItemResponseSchema>;
export type RecommendResponse = z.infer<typeof RecommendResponseSchema>;
export type ColdStartRequest = z.infer<typeof ColdStartRequestSchema>;

// ---------------------------------------------------------------------------
// Metrics & About Schemas
// ---------------------------------------------------------------------------

export const MetricsResponseSchema = z
  .object({
    content_type: z.string(),
    dataset_variant: z.string(),
    is_synthetic: z.boolean().default(false),
    synthetic_demo: z.boolean().default(false),
    provenance_banner: z.string().optional().nullable(),
    models: z.record(z.string(), z.any()).optional(),
    protocol: z.record(z.string(), z.any()).optional(),
    cold_start_curves: z.record(z.string(), z.any()).optional(),
  })
  .passthrough();

export const DatasetAttributionSchema = z.object({
  name: z.string(),
  citation: z.string(),
  license: z.string(),
  source_url: z.string(),
  original_vs_derived: z.string(),
});

export const AboutResponseSchema = z.object({
  title: z.string().default('Discovery Engine'),
  version: z.string().default('1.0.0'),
  description: z.string(),
  attributions: z.array(DatasetAttributionSchema),
  non_commercial_notice: z.string(),
});

export type MetricsResponse = z.infer<typeof MetricsResponseSchema>;
export type DatasetAttribution = z.infer<typeof DatasetAttributionSchema>;
export type AboutResponse = z.infer<typeof AboutResponseSchema>;

// ---------------------------------------------------------------------------
// Chat Schemas (Phase 13)
// ---------------------------------------------------------------------------

export const ChatMessageSchema = z.object({
  role: z.enum(['user', 'assistant']),
  content: z.string().min(1).max(500),
});

export const ChatRequestSchema = z
  .object({
    type: z.string().min(1).max(50),
    user_id: z.string().nullable().optional(),
    messages: z.array(ChatMessageSchema).min(1).max(10),
  })
  .refine(
    (data) => {
      const totalChars = data.messages.reduce((acc, m) => acc + m.content.length, 0);
      return totalChars <= 4000;
    },
    { message: 'Total content across messages must not exceed 4,000 characters' }
  )
  .refine(
    (data) => {
      return data.messages[data.messages.length - 1].role === 'user';
    },
    { message: 'The last message must be from the user' }
  );

export const ChatPickSchema = z.object({
  item_id: z.string(),
  title: z.string(),
  subtitle: z.string().nullable().optional(),
  categories: z.array(z.string()).default([]),
  year: z.number().nullable().optional(),
  reason: z.string(),
  rank: z.number().int().min(1),
});

export const PickCardSchema = ChatPickSchema;

export const ChatMetaSchema = z.object({
  model: z.string().nullable().optional(),
  latency_ms: z.number(),
  cache_hit: z.boolean().default(false),
  fallback_reason: z
    .enum([
      'rate_limited',
      'timeout',
      'upstream_error',
      'bad_output',
      'disabled',
      'no_credentials',
    ])
    .nullable()
    .optional(),
  retry_after_s: z.number().nullable().optional(),
});

export const ChatResponseSchema = z.object({
  reply: z.string(),
  picks: z.array(ChatPickSchema).default([]),
  mode: z.enum(['llm', 'fallback']),
  meta: ChatMetaSchema,
});

export const ChatStatusResponseSchema = z.object({
  enabled: z.boolean(),
  ready: z.boolean(),
  model: z.string().nullable().optional(),
});

export const ChatStatusSchema = ChatStatusResponseSchema;

export type ChatMessage = z.infer<typeof ChatMessageSchema>;
export type ChatRequest = z.infer<typeof ChatRequestSchema>;
export type ChatPick = z.infer<typeof ChatPickSchema>;
export type PickCard = ChatPick;
export type ChatMeta = z.infer<typeof ChatMetaSchema>;
export type ChatResponse = z.infer<typeof ChatResponseSchema>;
export type ChatStatusResponse = z.infer<typeof ChatStatusResponseSchema>;
export type ChatStatus = ChatStatusResponse;


