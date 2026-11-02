import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { proxyToBackend } from '@/lib/server/proxy';

// Zod schema for chat request (Phase 13, section 4.1)
export const ChatRequestSchema = z
  .object({
    type: z.string().min(1).max(50),
    user_id: z.string().nullable().optional(),
    messages: z
      .array(
        z.object({
          role: z.enum(['user', 'assistant']),
          content: z.string().min(1).max(500),
        })
      )
      .min(1)
      .max(10),
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

// Zod schema for chat response picks
export const PickCardSchema = z.object({
  item_id: z.string(),
  title: z.string(),
  subtitle: z.string().nullable().optional(),
  categories: z.array(z.string()).default([]),
  year: z.number().nullable().optional(),
  reason: z.string(),
  rank: z.number().int().min(1),
});

// Zod schema for full chat response
export const ChatResponseSchema = z.object({
  reply: z.string(),
  picks: z.array(PickCardSchema).default([]),
  mode: z.enum(['llm', 'fallback']),
  meta: z.object({
    model: z.string().nullable().optional(),
    latency_ms: z.number(),
    cache_hit: z.boolean(),
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
  }),
});

// Zod schema for chat status response
export const ChatStatusSchema = z.object({
  enabled: z.boolean(),
  ready: z.boolean(),
  model: z.string().nullable().optional(),
});

export async function GET(): Promise<NextResponse> {
  return proxyToBackend('/v1/chat/status');
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  let jsonBody: unknown;
  try {
    jsonBody = await req.json();
  } catch {
    return NextResponse.json(
      {
        error: {
          code: 'INVALID_JSON',
          message: 'Request body must be valid JSON',
        },
      },
      { status: 400 }
    );
  }

  const parsed = ChatRequestSchema.safeParse(jsonBody);
  if (!parsed.success) {
    return NextResponse.json(
      {
        error: {
          code: 'VALIDATION_ERROR',
          message: parsed.error.issues.map((i) => i.message).join('; '),
          details: parsed.error.format(),
        },
      },
      { status: 422 }
    );
  }

  const proxyRes = await proxyToBackend('/v1/chat', {
    method: 'POST',
    body: JSON.stringify(parsed.data),
  });

  // If proxy returned error or rate limit, forward status and Retry-After intact
  if (!proxyRes.ok) {
    return proxyRes;
  }

  try {
    const rawData = await proxyRes.json();
    const validated = ChatResponseSchema.safeParse(rawData);
    if (!validated.success) {
      console.warn('[chat proxy] Upstream response validation notice:', validated.error);
      return NextResponse.json(rawData, { status: proxyRes.status });
    }
    return NextResponse.json(validated.data, { status: 200 });
  } catch {
    return proxyRes;
  }
}
