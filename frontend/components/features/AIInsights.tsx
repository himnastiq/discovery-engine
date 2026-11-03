'use client';

import React, { useMemo, useState } from 'react';
import Image from 'next/image';
import { Sparkles, RotateCcw, Film, ShoppingBag, Newspaper, ArrowUpRight, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { useMoviePoster } from '@/lib/api/hooks';
import type { ScoredItem } from '@/lib/api/schemas';

export interface AIInsightsProps {
  items: ScoredItem[];
  cardType?: 'movie' | 'product' | 'article';
  type?: string;
  userId?: string | null;
  onSelectItem?: (item: ScoredItem) => void;
  isLoading?: boolean;
  className?: string;
}

export function AIInsights({
  items,
  cardType = 'movie',
  type,
  userId,
  onSelectItem,
  isLoading = false,
  className = '',
}: AIInsightsProps) {
  const [seed, setSeed] = useState(() => Math.floor(Math.random() * 1000));

  // Query actual LLM insight synthesis from the Gemini chat backend
  const {
    data: chatData,
    isLoading: isChatLoading,
    isFetching: isChatFetching,
    refetch: refetchChat,
  } = useQuery({
    queryKey: ['aiInsights', type, userId],
    queryFn: async ({ signal }) => {
      if (!type) return null;
      return apiClient.postChat(
        {
          type,
          user_id: userId || null,
          messages: [
            {
              role: 'user',
              content: 'Recommend the top 3 best items for my profile.',
            },
          ],
        },
        signal
      );
    },
    enabled: Boolean(type),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  // Convert LLM candidate picks to ScoredItem format
  const llmItems: ScoredItem[] | null = useMemo(() => {
    if (!chatData?.picks || chatData.picks.length === 0) return null;
    return chatData.picks.slice(0, 3).map((p, idx) => ({
      item_id: p.item_id,
      title: p.title,
      subtitle: p.subtitle ?? undefined,
      categories: p.categories || [],
      year: p.year ?? undefined,
      score: 1.0 - idx * 0.1,
      display_score: 98 - idx * 4,
      reason: {
        kind: 'llm',
        text: p.reason,
      },
      meta: {},
    }));
  }, [chatData]);

  // Fallback to local pseudo-random permutation of engine candidate items
  const sampledItems = useMemo(() => {
    if (llmItems && llmItems.length > 0) return llmItems;
    if (!items || items.length === 0) return [];
    if (items.length <= 3) return items;

    const pool = [...items];
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.abs(Math.sin(seed * 997 + i * 37)) * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    return pool.slice(0, 3);
  }, [items, seed, llmItems]);

  const handleShuffle = () => {
    if (type) {
      refetchChat();
    }
    setSeed((prev) => prev + 1);
  };

  const isSynthesizing = isChatLoading || isChatFetching;
  const isLLMActive = chatData?.mode === 'llm';

  return (
    <section
      aria-labelledby="ai-insights-title"
      className={`relative rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:p-5 overflow-hidden ${className}`}
    >
      {/* Decorative top accent line with gradient */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[var(--color-accent)] via-purple-500 to-[var(--color-accent-text)] opacity-80" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-[4px] bg-[var(--color-accent)]/15 text-[var(--color-accent-text)] flex items-center justify-center">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <h2
              id="ai-insights-title"
              className="text-sm sm:text-base font-bold text-[var(--color-text)] tracking-tight"
            >
              AI Insights
            </h2>
            <span
              className={`text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full border flex items-center gap-1.5 ${
                isLLMActive
                  ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                  : 'bg-[var(--color-accent)]/10 text-[var(--color-accent-text)] border-[var(--color-accent)]/20'
              }`}
            >
              {isSynthesizing ? (
                <>
                  <Loader2 className="h-2.5 w-2.5 animate-spin" />
                  Updating...
                </>
              ) : isLLMActive ? (
                <>
                  <Sparkles className="h-2.5 w-2.5" />
                  AI Recommended
                </>
              ) : (
                'LLM Integrated'
              )}
            </span>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1">
            Top signals synthesized across your personalized profile.
          </p>
        </div>

        {(items && items.length > 3 || Boolean(type)) && (
          <button
            type="button"
            onClick={handleShuffle}
            disabled={isSynthesizing}
            className="inline-flex items-center gap-1.5 self-start sm:self-auto px-2.5 py-1 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)] bg-[var(--color-elevated)] hover:bg-[var(--color-border)] rounded-[4px] border border-[var(--color-border)] transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)] disabled:opacity-50"
            title="Sample different AI recommendations"
            aria-label="Regenerate or shuffle AI insights"
          >
            <RotateCcw className={`h-3 w-3 ${isSynthesizing ? 'animate-spin' : ''}`} />
            <span>Shuffle</span>
          </button>
        )}
      </div>

      {/* Content: 3 Items / Skeletons / Empty State */}
      {isLoading || (isSynthesizing && sampledItems.length === 0) ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-elevated)]/40 p-3 flex gap-3 items-center"
            >
              <div className="h-20 w-14 rounded bg-[var(--color-elevated)] shrink-0" />
              <div className="space-y-2 flex-1 min-w-0">
                <div className="h-3 w-3/4 rounded bg-[var(--color-elevated)]" />
                <div className="h-2 w-1/2 rounded bg-[var(--color-elevated)]" />
              </div>
            </div>
          ))}
        </div>
      ) : sampledItems.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {sampledItems.map((item, idx) => (
            <AIInsightItemCard
              key={item.item_id || idx}
              item={item}
              cardType={cardType}
              onSelect={onSelectItem}
              index={idx}
            />
          ))}
        </div>
      ) : (
        <div className="py-6 text-center text-xs text-[var(--color-text-muted)] border border-dashed border-[var(--color-border)] rounded-[4px]">
          No recommendations available to generate insights yet.
        </div>
      )}
    </section>
  );
}

function AIInsightItemCard({
  item,
  cardType = 'movie',
  onSelect,
  index,
}: {
  item: ScoredItem;
  cardType?: 'movie' | 'product' | 'article';
  onSelect?: (item: ScoredItem) => void;
  index: number;
}) {
  const [imageError, setImageError] = useState(false);

  // Dynamic TMDB poster resolution for movies when image_url is missing
  const { data: tmdbPosterUrl } = useMoviePoster(
    item.title,
    item.year,
    cardType === 'movie' && !item.image_url
  );
  const activeImageUrl = item.image_url || tmdbPosterUrl;

  const handleClick = () => {
    onSelect?.(item);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect?.(item);
    }
  };

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="group relative flex gap-3 p-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-elevated)]/50 hover:bg-[var(--color-elevated)] hover:border-[var(--color-accent)]/50 transition-all cursor-pointer focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)] text-left"
    >
      {/* Thumbnail */}
      <div className="relative h-20 w-14 shrink-0 overflow-hidden rounded-[4px] bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center">
        {activeImageUrl && !imageError ? (
          <Image
            src={activeImageUrl}
            alt={item.title}
            fill
            unoptimized
            sizes="56px"
            className="object-cover transition-transform duration-200 group-hover:scale-105"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="text-[var(--color-text-muted)]">
            {cardType === 'movie' ? (
              <Film className="h-5 w-5 opacity-40 text-[var(--color-accent)]" />
            ) : cardType === 'product' ? (
              <ShoppingBag className="h-5 w-5 opacity-40 text-[var(--color-accent)]" />
            ) : (
              <Newspaper className="h-5 w-5 opacity-40 text-[var(--color-accent)]" />
            )}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div>
          <div className="mb-1">
            <span className="text-[10px] font-semibold text-[var(--color-accent-text)] uppercase tracking-wider">
              Signal #{index + 1}
            </span>
          </div>
          <p className="text-xs sm:text-sm font-semibold text-[var(--color-text)] line-clamp-2 group-hover:text-[var(--color-accent-text)] transition-colors">
            {item.title}
          </p>
        </div>

        <div className="mt-2 flex items-center justify-between gap-1 text-[11px] text-[var(--color-text-muted)]">
          <span className="truncate" title={item.reason?.text || item.categories?.join(', ') || ''}>
            {item.reason?.text || item.categories?.[0] || (item.year ? String(item.year) : '')}
          </span>
          <ArrowUpRight className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-[var(--color-text-secondary)]" />
        </div>
      </div>
    </article>
  );
}
