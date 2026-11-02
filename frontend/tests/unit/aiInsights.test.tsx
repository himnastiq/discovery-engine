import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AIInsights } from '@/components/features/AIInsights';
import type { ScoredItem } from '@/lib/api/schemas';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('AIInsights Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockItems: ScoredItem[] = [
    {
      item_id: '385',
      title: 'The Matrix (1999)',
      categories: ['Action', 'Sci-Fi'],
      display_score: 0.94,
      score: 0.94,
      year: 1999,
      image_url: null,
      meta: {},
    },
    {
      item_id: '423',
      title: 'Blade Runner (1982)',
      categories: ['Sci-Fi', 'Film-Noir'],
      display_score: 0.88,
      score: 0.88,
      year: 1982,
      image_url: null,
      meta: {},
    },
    {
      item_id: '1240',
      title: 'The Terminator (1984)',
      categories: ['Action', 'Sci-Fi'],
      display_score: 0.85,
      score: 0.85,
      year: 1984,
      image_url: null,
      meta: {},
    },
    {
      item_id: '2571',
      title: 'The Matrix Reloaded (2003)',
      categories: ['Action', 'Sci-Fi'],
      display_score: 0.81,
      score: 0.81,
      year: 2003,
      image_url: null,
      meta: {},
    },
    {
      item_id: '589',
      title: 'Terminator 2 (1991)',
      categories: ['Action', 'Sci-Fi'],
      display_score: 0.92,
      score: 0.92,
      year: 1991,
      image_url: null,
      meta: {},
    },
  ];

  it('renders AI Insights title, preview badge, and 3 sampled items', () => {
    renderWithClient(
      <AIInsights items={mockItems} cardType="movie" onSelectItem={vi.fn()} />
    );

    expect(screen.getByRole('heading', { name: /ai insights/i })).toBeInTheDocument();
    expect(screen.getByText(/preview|live/i)).toBeInTheDocument();

    // Verify 3 signal chips are rendered
    expect(screen.getByText('Signal #1')).toBeInTheDocument();
    expect(screen.getByText('Signal #2')).toBeInTheDocument();
    expect(screen.getByText('Signal #3')).toBeInTheDocument();
    expect(screen.queryByText('Signal #4')).not.toBeInTheDocument();
  });

  it('renders loading skeletons when isLoading is true', () => {
    const { container } = renderWithClient(
      <AIInsights items={[]} cardType="movie" isLoading={true} />
    );

    expect(screen.getByRole('heading', { name: /ai insights/i })).toBeInTheDocument();
    const pulses = container.querySelectorAll('.animate-pulse');
    expect(pulses.length).toBeGreaterThan(0);
  });

  it('renders empty fallback when items array is empty', () => {
    renderWithClient(
      <AIInsights items={[]} cardType="movie" isLoading={false} />
    );

    expect(
      screen.getByText(/no recommendations available to generate insights yet/i)
    ).toBeInTheDocument();
  });

  it('triggers onSelectItem callback when an insight card is clicked', () => {
    const onSelect = vi.fn();
    renderWithClient(
      <AIInsights items={mockItems} cardType="movie" onSelectItem={onSelect} />
    );

    const firstCard = screen.getByText('Signal #1').closest('article');
    expect(firstCard).not.toBeNull();
    if (firstCard) {
      fireEvent.click(firstCard);
      expect(onSelect).toHaveBeenCalledTimes(1);
      expect(onSelect).toHaveBeenCalledWith(
        expect.objectContaining({
          item_id: expect.any(String),
          title: expect.any(String),
        })
      );
    }
  });

  it('renders shuffle button when items count > 3 and handles shuffle click', () => {
    renderWithClient(
      <AIInsights items={mockItems} cardType="movie" onSelectItem={vi.fn()} />
    );

    const shuffleButton = screen.getByRole('button', { name: /shuffle ai insights/i });
    expect(shuffleButton).toBeInTheDocument();

    fireEvent.click(shuffleButton);
    // Still renders 3 signals
    expect(screen.getByText('Signal #1')).toBeInTheDocument();
    expect(screen.getByText('Signal #2')).toBeInTheDocument();
    expect(screen.getByText('Signal #3')).toBeInTheDocument();
  });
});
