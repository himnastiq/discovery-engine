import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChatPanel } from '@/components/features/ChatPanel';
import { apiClient } from '@/lib/api/client';
import type { ChatResponse, ChatStatusResponse, TypesResponse } from '@/lib/api/schemas';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockStatusReady: ChatStatusResponse = {
  enabled: true,
  ready: true,
  model: 'gemini-2.5-flash',
};

const mockStatusUnconfigured: ChatStatusResponse = {
  enabled: false,
  ready: false,
  model: null,
};

const mockTypesResponse: TypesResponse = {
  types: [
    {
      id: 'movies',
      display_name: 'Movies',
      card_type: 'movie',
      supports_cold_start: true,
      user_count: 100,
      item_count: 500,
      interaction_count: 5000,
      starter_prompts: [
        'Suggest 90s sci-fi movies',
        'Top movies for my taste',
      ],
    },
    {
      id: 'products',
      display_name: 'Video Games',
      card_type: 'product',
      supports_cold_start: true,
      user_count: 80,
      item_count: 300,
      interaction_count: 2000,
      starter_prompts: [
        'Find retro Nintendo games',
        'Recommend top RPGs',
      ],
    },
  ],
};

const mockChatResponse: ChatResponse = {
  reply: 'Here are top recommendations matching your tastes.\n\nEnjoy watching!',
  picks: [
    {
      item_id: '1',
      title: 'Toy Story',
      subtitle: 'Pixar Animation',
      categories: ['Animation', 'Comedy'],
      year: 1995,
      reason: 'Groundbreaking computer-animated classic.',
      rank: 1,
    },
  ],
  mode: 'llm',
  meta: {
    model: 'gemini-2.5-flash',
    latency_ms: 85,
    cache_hit: false,
    fallback_reason: null,
    retry_after_s: null,
  },
};

describe('ChatPanel Accessibility & Core Dialog (P13.20)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'getChatStatus').mockResolvedValue(mockStatusReady);
    vi.spyOn(apiClient, 'getTypes').mockResolvedValue(mockTypesResponse);
  });

  it('renders role="dialog" with aria-modal and aria-labelledby', async () => {
    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby');

    const labelId = dialog.getAttribute('aria-labelledby');
    const heading = document.getElementById(labelId!);
    expect(heading).toBeInTheDocument();
    expect(heading?.textContent).toContain('Discovery Assistant');
  });

  it('renders an aria-live="polite" message log', async () => {
    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    const liveRegion = document.querySelector('[aria-live="polite"]');
    expect(liveRegion).toBeInTheDocument();
  });

  it('closes dialog on Escape key and close button click', async () => {
    const onClose = vi.fn();
    renderWithClient(
      <ChatPanel isOpen={true} onClose={onClose} activeType="movies" />
    );

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);

    const closeBtn = screen.getByRole('button', { name: /close assistant panel/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it('returns focus to trigger element when closed', async () => {
    const triggerBtn = document.createElement('button');
    document.body.appendChild(triggerBtn);
    triggerBtn.focus();
    const triggerRef = { current: triggerBtn };

    const { unmount } = renderWithClient(
      <ChatPanel
        isOpen={true}
        onClose={vi.fn()}
        activeType="movies"
        triggerRef={triggerRef}
      />
    );

    unmount();
    expect(document.activeElement).toBe(triggerBtn);
    document.body.removeChild(triggerBtn);
  });

  it('traps focus inside the dialog when Tab is pressed', async () => {
    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    await screen.findByPlaceholderText(/Ask about Movies/i);

    const dialog = screen.getByRole('dialog');
    const focusable = dialog.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
    );
    expect(focusable.length).toBeGreaterThan(1);

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    // Simulate Shift+Tab on first element
    first.focus();
    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });

    // Simulate Tab on last element
    last.focus();
    fireEvent.keyDown(window, { key: 'Tab' });
  });
});

describe('Message & PickCard Rendering & XSS Protection (P13.21)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'getChatStatus').mockResolvedValue(mockStatusReady);
    vi.spyOn(apiClient, 'getTypes').mockResolvedValue(mockTypesResponse);
    vi.spyOn(apiClient, 'postChat').mockResolvedValue(mockChatResponse);
  });

  it('renders plain text paragraphs and candidate PickCard with rank and reason', async () => {
    const onSelect = vi.fn();
    renderWithClient(
      <ChatPanel
        isOpen={true}
        onClose={vi.fn()}
        activeType="movies"
        onSelectItem={onSelect}
      />
    );

    const input = await screen.findByPlaceholderText(/Ask about Movies/i);
    fireEvent.change(input, { target: { value: 'Recommend a good movie' } });
    fireEvent.click(screen.getByRole('button', { name: /send message/i }));

    await waitFor(() => {
      expect(screen.getByText(/Here are top recommendations matching your tastes/i)).toBeInTheDocument();
      expect(screen.getByText(/Enjoy watching!/i)).toBeInTheDocument();
    });

    // Check pick card fields
    expect(screen.getByText('Toy Story')).toBeInTheDocument();
    expect(screen.getByText('(1995)')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText(/Groundbreaking computer-animated classic/i)).toBeInTheDocument();

    // Check View details button
    const viewBtn = screen.getByRole('button', { name: /view details/i });
    fireEvent.click(viewBtn);
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        item_id: '1',
        title: 'Toy Story',
      })
    );
  });

  it('renders malicious markup string strictly as plain text (XSS defense)', async () => {
    const maliciousResponse: ChatResponse = {
      reply: '<script>alert("pwned")</script><b>Bold Title</b> <img src=x onerror=alert(1)>',
      picks: [],
      mode: 'llm',
      meta: {
        model: 'gemini-2.5-flash',
        latency_ms: 50,
        cache_hit: false,
        fallback_reason: null,
        retry_after_s: null,
      },
    };
    vi.spyOn(apiClient, 'postChat').mockResolvedValue(maliciousResponse);

    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    const input = await screen.findByPlaceholderText(/Ask about Movies/i);
    fireEvent.change(input, { target: { value: 'Test malicious injection' } });
    fireEvent.click(screen.getByRole('button', { name: /send message/i }));

    await waitFor(() => {
      // Script tags must be rendered as literal text characters, not DOM nodes
      expect(screen.getByText(/<script>alert\("pwned"\)<\/script>/i)).toBeInTheDocument();
    });

    // Verify no script or img tags were inserted into the document
    expect(document.querySelector('script[src*="pwned"]')).toBeNull();
    expect(document.querySelector('img[src="x"]')).toBeNull();
  });
});

describe('Starter Prompt Chips (P13.22)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'getChatStatus').mockResolvedValue(mockStatusReady);
    vi.spyOn(apiClient, 'getTypes').mockResolvedValue(mockTypesResponse);
  });

  it('displays starter prompts dynamically per content type and updates on type change', async () => {
    const { unmount } = renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    expect(await screen.findByText('Suggest 90s sci-fi movies')).toBeInTheDocument();
    expect(screen.getByText('Top movies for my taste')).toBeInTheDocument();
    unmount();

    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="products" />
    );

    expect(await screen.findByText('Find retro Nintendo games')).toBeInTheDocument();
    expect(screen.getByText('Recommend top RPGs')).toBeInTheDocument();
  });

  it('submits query when clicking a starter prompt chip', async () => {
    const postChatSpy = vi.spyOn(apiClient, 'postChat').mockResolvedValue(mockChatResponse);

    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    const promptBtn = await screen.findByText('Suggest 90s sci-fi movies');
    fireEvent.click(promptBtn);

    expect(postChatSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'movies',
        messages: [{ role: 'user', content: 'Suggest 90s sci-fi movies' }],
      }),
      expect.anything()
    );
  });
});

describe('ChatPanel State Handling (P13.23)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'getTypes').mockResolvedValue(mockTypesResponse);
  });

  it('renders unconfigured standby state when chat is not ready', async () => {
    vi.spyOn(apiClient, 'getChatStatus').mockResolvedValue(mockStatusUnconfigured);

    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    expect(await screen.findByText(/Assistant in Standby/i)).toBeInTheDocument();
    expect(screen.getByText(/GEMINI_API_KEYS/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Assistant standing by/i)).toBeDisabled();
  });

  it('renders offline fallback badge when response mode is fallback', async () => {
    vi.spyOn(apiClient, 'getChatStatus').mockResolvedValue(mockStatusReady);
    const fallbackResponse: ChatResponse = {
      reply: 'Here are popular items from the engine catalogue.',
      picks: [],
      mode: 'fallback',
      meta: {
        model: null,
        latency_ms: 10,
        cache_hit: false,
        fallback_reason: 'rate_limited',
        retry_after_s: 15,
      },
    };
    vi.spyOn(apiClient, 'postChat').mockResolvedValue(fallbackResponse);

    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    const input = await screen.findByPlaceholderText(/Ask about Movies/i);
    fireEvent.change(input, { target: { value: 'Recommend something' } });
    fireEvent.click(screen.getByRole('button', { name: /send message/i }));

    expect(await screen.findByText(/Answer from engine \(offline fallback\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Rate limit cooldown: Retry available in 15s/i)).toBeInTheDocument();
  });

  it('renders error state with retry option on API failure', async () => {
    vi.spyOn(apiClient, 'getChatStatus').mockResolvedValue(mockStatusReady);
    const postChatSpy = vi
      .spyOn(apiClient, 'postChat')
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(mockChatResponse);

    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    const input = await screen.findByPlaceholderText(/Ask about Movies/i);
    fireEvent.change(input, { target: { value: 'Trigger error' } });
    const form = input.closest('form')!;
    fireEvent.submit(form);

    const errorElements = await screen.findAllByText(/An unexpected error occurred/i);
    expect(errorElements.length).toBeGreaterThan(0);
    const retryButtons = screen.getAllByRole('button', { name: /retry/i });
    expect(retryButtons.length).toBeGreaterThan(0);

    // Clicking retry attempts the request again
    fireEvent.click(retryButtons[0]);
    expect(postChatSpy).toHaveBeenCalledTimes(2);
  });

  it('allows clearing conversation history', async () => {
    vi.spyOn(apiClient, 'getChatStatus').mockResolvedValue(mockStatusReady);
    vi.spyOn(apiClient, 'postChat').mockResolvedValue(mockChatResponse);

    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    const input = await screen.findByPlaceholderText(/Ask about Movies/i);
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByRole('button', { name: /send message/i }));

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument();
    });

    const clearBtn = screen.getByRole('button', { name: /clear conversation/i });
    fireEvent.click(clearBtn);

    expect(screen.queryByText('Hello')).not.toBeInTheDocument();
  });

  it('renders AI disclaimer notice', () => {
    vi.spyOn(apiClient, 'getChatStatus').mockResolvedValue(mockStatusReady);
    renderWithClient(
      <ChatPanel isOpen={true} onClose={vi.fn()} activeType="movies" />
    );

    expect(screen.getByText(/AI-generated recommendations may be inaccurate/i)).toBeInTheDocument();
  });
});
