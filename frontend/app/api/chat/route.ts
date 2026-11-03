import { NextRequest, NextResponse } from 'next/server';
import { proxyToBackend } from '@/lib/server/proxy';
import { ChatRequestSchema, ChatResponseSchema } from '@/lib/api/schemas';

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
    timeoutMs: 60000,
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
