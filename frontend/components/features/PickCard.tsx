'use client';

import React from 'react';
import Image from 'next/image';
import { Film, ShoppingBag, Newspaper, ChevronRight } from 'lucide-react';
import { useMoviePoster } from '@/lib/api/hooks';
import { Badge } from '@/components/ui/Badge';
import type { ChatPick, ScoredItem } from '@/lib/api/schemas';

export interface PickCardProps {
  pick: ChatPick;
  cardType?: 'movie' | 'product' | 'article';
  onSelect?: (item: ScoredItem) => void;
}

export function PickCard({ pick, cardType = 'movie', onSelect }: PickCardProps) {
  const { data: posterUrl } = useMoviePoster(
    pick.title,
    pick.year,
    cardType === 'movie'
  );

  const handleSelect = () => {
    if (!onSelect) return;
    const scoredItem: ScoredItem = {
      item_id: pick.item_id,
      title: pick.title,
      subtitle: pick.subtitle || null,
      categories: pick.categories || [],
      year: pick.year || null,
      score: 1.0,
      display_score: 1.0,
      reason: {
        kind: 'chat_recommendation',
        item_id: pick.item_id,
        text: pick.reason,
        similarity_score: null,
      },
      meta: {},
    };
    onSelect(scoredItem);
  };

  return (
    <div
      data-testid={`pick-card-${pick.item_id}`}
      className="group relative flex flex-col sm:flex-row gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-elevated)] p-3 text-[var(--color-text)] transition-colors hover:border-[var(--color-border-strong)]"
    >
      {/* Poster thumbnail or icon fallback */}
      <div className="relative h-24 w-16 shrink-0 overflow-hidden rounded-[4px] bg-[var(--color-surface)] flex items-center justify-center border border-[var(--color-border)]">
        {posterUrl ? (
          <Image
            src={posterUrl}
            alt={pick.title}
            fill
            sizes="64px"
            className="object-cover"
            unoptimized
          />
        ) : (
          <div className="text-[var(--color-text-muted)]">
            {cardType === 'movie' && <Film className="h-6 w-6" />}
            {cardType === 'product' && <ShoppingBag className="h-6 w-6" />}
            {cardType === 'article' && <Newspaper className="h-6 w-6" />}
          </div>
        )}
      </div>

      {/* Item info and rationale */}
      <div className="flex flex-1 flex-col justify-between">
        <div>
          <div className="flex items-start justify-between gap-2">
            <h4 className="text-sm font-semibold text-[var(--color-text)] line-clamp-1">
              {pick.title}
              {pick.year ? (
                <span className="ml-1.5 text-xs font-normal text-[var(--color-text-muted)]">
                  ({pick.year})
                </span>
              ) : null}
            </h4>
            <Badge
              variant="outline"
              className="shrink-0 text-[11px] font-mono border-[var(--color-border-strong)] text-[var(--color-text-secondary)]"
            >
              #{pick.rank}
            </Badge>
          </div>

          {pick.subtitle ? (
            <p className="mt-0.5 text-xs text-[var(--color-text-secondary)] line-clamp-1">
              {pick.subtitle}
            </p>
          ) : null}

          {/* Categories */}
          {pick.categories && pick.categories.length > 0 ? (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {pick.categories.slice(0, 3).map((category) => (
                <span
                  key={category}
                  className="rounded-[3px] bg-[var(--color-surface)] px-1.5 py-0.5 text-[10px] text-[var(--color-text-muted)] border border-[var(--color-border)]"
                >
                  {category}
                </span>
              ))}
            </div>
          ) : null}

          {/* Reason text */}
          <p className="mt-2 text-xs italic text-[var(--color-text-secondary)] line-clamp-2">
            &ldquo;{pick.reason}&rdquo;
          </p>
        </div>

        {/* Action Button */}
        {onSelect ? (
          <div className="mt-2.5 flex justify-end">
            <button
              type="button"
              onClick={handleSelect}
              className="inline-flex items-center gap-1 rounded-[4px] px-2.5 py-1 text-xs font-medium text-[var(--color-accent-text)] hover:bg-[var(--color-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)] cursor-pointer"
            >
              <span>View details</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
