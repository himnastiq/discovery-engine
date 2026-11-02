import { describe, it, expect } from 'vitest';
import type { components } from '@/src/lib/api/generated';
import {
  ChatMessageSchema,
  ChatRequestSchema,
  ChatPickSchema,
  ChatMetaSchema,
  ChatResponseSchema,
  ChatStatusResponseSchema,
  type ChatMessage,
  type ChatRequest,
  type ChatPick,
  type ChatMeta,
  type ChatResponse,
  type ChatStatusResponse,
} from '@/lib/api/schemas';
import chatResponseFixture from '../fixtures/chat_response.json';
import chatStatusFixture from '../fixtures/chat_status.json';

// =============================================================================
// Compile-time OpenAPI <-> Zod Type Contract Verification (P13.19)
// =============================================================================

type OpenAPIChatMessage = components['schemas']['ChatMessage'];
type OpenAPIChatMeta = components['schemas']['ChatMeta'];
type OpenAPIChatPick = components['schemas']['ChatPick'];
type OpenAPIChatRequest = components['schemas']['ChatRequest'];
type OpenAPIChatResponse = components['schemas']['ChatResponse'];
type OpenAPIChatStatusResponse = components['schemas']['ChatStatusResponse'];

// Type-level assignability assertions (will fail compilation if schemas drift):
const _verifyMessageAssignable: OpenAPIChatMessage = {} as ChatMessage;
const _verifyMetaAssignable: OpenAPIChatMeta = {} as ChatMeta;
const _verifyPickAssignable: OpenAPIChatPick = {} as ChatPick;
const _verifyRequestAssignable: OpenAPIChatRequest = {} as ChatRequest;
const _verifyResponseAssignable: OpenAPIChatResponse = {} as ChatResponse;
const _verifyStatusAssignable: OpenAPIChatStatusResponse = {} as ChatStatusResponse;

// Suppress unused variable warnings in tests
void _verifyMessageAssignable;
void _verifyMetaAssignable;
void _verifyPickAssignable;
void _verifyRequestAssignable;
void _verifyResponseAssignable;
void _verifyStatusAssignable;

// =============================================================================
// Runtime Contract Tests (P13.19 Acceptance)
// =============================================================================

describe('Chat Schemas & OpenAPI Contract Tests (P13.19)', () => {
  it('validates ChatResponse schema against recorded backend fixture', () => {
    const result = ChatResponseSchema.safeParse(chatResponseFixture);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.reply).toContain('personalized recommendations');
      expect(result.data.mode).toBe('llm');
      expect(result.data.picks.length).toBe(2);
      expect(result.data.picks[0].item_id).toBe('1');
      expect(result.data.picks[0].rank).toBe(1);
      expect(result.data.picks[0].categories).toEqual(['Animation', 'Adventure', 'Comedy']);
      expect(result.data.meta.model).toBe('gemini-2.5-flash');
      expect(result.data.meta.latency_ms).toBe(142);
      expect(result.data.meta.cache_hit).toBe(false);
      expect(result.data.meta.fallback_reason).toBeNull();
    }
  });

  it('validates ChatStatusResponse schema against recorded backend fixture', () => {
    const result = ChatStatusResponseSchema.safeParse(chatStatusFixture);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.enabled).toBe(true);
      expect(result.data.ready).toBe(true);
      expect(result.data.model).toBe('gemini-2.5-flash');
    }
  });

  it('validates single ChatMessage and rejects invalid role', () => {
    const validMessage = { role: 'user', content: 'What movies do you recommend?' };
    expect(ChatMessageSchema.safeParse(validMessage).success).toBe(true);

    const invalidRole = { role: 'system', content: 'Hello' };
    expect(ChatMessageSchema.safeParse(invalidRole).success).toBe(false);
  });

  it('validates ChatMeta diagnostic properties', () => {
    const validMeta = {
      model: 'gemini-2.5-flash',
      latency_ms: 120,
      cache_hit: true,
      fallback_reason: null,
      retry_after_s: null,
    };
    expect(ChatMetaSchema.safeParse(validMeta).success).toBe(true);

    const invalidMeta = {
      model: 'gemini-2.5-flash',
      latency_ms: 'not-a-number',
      cache_hit: true,
    };
    expect(ChatMetaSchema.safeParse(invalidMeta).success).toBe(false);
  });

  it('validates engine-only fallback response payload correctly', () => {
    const fallbackPayload = {
      reply: 'Here are popular recommendations while the assistant is busy:',
      picks: [
        {
          item_id: '50',
          title: 'The Usual Suspects',
          categories: ['Crime', 'Mystery', 'Thriller'],
          reason: 'Consistently top-ranked item in catalogue',
          rank: 1,
        },
      ],
      mode: 'fallback',
      meta: {
        model: null,
        latency_ms: 12,
        cache_hit: true,
        fallback_reason: 'rate_limited',
        retry_after_s: 15,
      },
    };

    const result = ChatResponseSchema.safeParse(fallbackPayload);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.mode).toBe('fallback');
      expect(result.data.meta.fallback_reason).toBe('rate_limited');
      expect(result.data.meta.retry_after_s).toBe(15);
      expect(result.data.picks[0].rank).toBe(1);
    }
  });

  it('validates valid ChatRequest and enforces contract boundaries', () => {
    const validRequest = {
      type: 'movies',
      user_id: '42',
      messages: [
        { role: 'user', content: 'Recommend a good space sci-fi movie' },
        { role: 'assistant', content: 'How about 2001: A Space Odyssey?' },
        { role: 'user', content: 'Something a bit faster-paced' },
      ],
    };

    const parsed = ChatRequestSchema.safeParse(validRequest);
    expect(parsed.success).toBe(true);
  });

  it('rejects ChatRequest where last message is NOT from user', () => {
    const invalidRequest = {
      type: 'movies',
      user_id: '42',
      messages: [
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'Hi there!' },
      ],
    };

    const result = ChatRequestSchema.safeParse(invalidRequest);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('The last message must be from the user');
    }
  });

  it('rejects ChatRequest exceeding message count limit (max 10)', () => {
    const messages = Array.from({ length: 11 }, (_, i) => ({
      role: (i % 2 === 0 ? 'user' : 'assistant') as 'user' | 'assistant',
      content: `Message ${i}`,
    }));
    // Ensure last message is from user
    messages[10].role = 'user';

    const result = ChatRequestSchema.safeParse({
      type: 'movies',
      messages,
    });
    expect(result.success).toBe(false);
  });

  it('rejects ChatRequest exceeding total 4000 char length limit', () => {
    const longContent = 'A'.repeat(450);
    const messages = [
      { role: 'user' as const, content: longContent },
      { role: 'assistant' as const, content: longContent },
      { role: 'user' as const, content: longContent },
      { role: 'assistant' as const, content: longContent },
      { role: 'user' as const, content: longContent },
      { role: 'assistant' as const, content: longContent },
      { role: 'user' as const, content: longContent },
      { role: 'assistant' as const, content: longContent },
      { role: 'user' as const, content: longContent },
      { role: 'user' as const, content: longContent },
    ]; // 10 * 450 = 4500 chars > 4000

    const result = ChatRequestSchema.safeParse({
      type: 'movies',
      messages,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('4,000 characters');
    }
  });

  it('rejects malformed ChatPick with invalid rank (< 1)', () => {
    const malformedPick = {
      item_id: '99',
      title: 'Invalid Rank Item',
      reason: 'Testing',
      rank: 0, // rank must be >= 1
    };

    const result = ChatPickSchema.safeParse(malformedPick);
    expect(result.success).toBe(false);
  });
});
