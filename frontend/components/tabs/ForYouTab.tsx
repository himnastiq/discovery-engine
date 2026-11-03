'use client';

import React from 'react';
import Link from 'next/link';
import { SlidersHorizontal, ArrowRight, TrendingUp } from 'lucide-react';
import { useRecommendations, usePopular } from '@/lib/api/hooks';
import { ProfileCard } from '@/components/features/ProfileCard';
import { RecCard } from '@/components/features/RecCard';
import { ModeBadge } from '@/components/features/ModeBadge';
import { AIInsights } from '@/components/features/AIInsights';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import type { ScoredItem } from '@/lib/api/schemas';

export interface ForYouTabProps {
  type: string;
  user: string;
  k: number;
  onKChange: (k: number) => void;
  onSelectItem?: (item: ScoredItem) => void;
}

interface DomainMeta {
  catalogLabel: string;
}

const DOMAIN_METAS: Record<string, DomainMeta> = {
  movies: {
    catalogLabel: 'MovieLens 1M',
  },
  products: {
    catalogLabel: 'Amazon Video Games',
  },
  articles: {
    catalogLabel: 'MIND News Feed',
  },
};

export function ForYouTab({
  type,
  user,
  k,
  onKChange,
  onSelectItem,
}: ForYouTabProps) {
  const { data: recData, isLoading, isError, refetch } = useRecommendations(type, user, k);
  const { data: popularData } = usePopular(type, 3);

  const cardType: 'movie' | 'product' | 'article' =
    type === 'products' ? 'product' : type === 'articles' ? 'article' : 'movie';

  const meta = DOMAIN_METAS[type] || DOMAIN_METAS.movies;
  const kOptions = [5, 10, 20];

  if (isError) {
    return (
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <ErrorState
          title="Failed to fetch recommendations"
          message={`Could not load recommendations for User #${user} in ${type}.`}
          onRetry={refetch}
        />
      </div>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[20rem_minmax(0,1fr)] lg:items-start">
      {/* 1. User Profile Summary (Desktop Sidebar, Stacked on Mobile) */}
      <div>
        <ProfileCard type={type} userId={user} />
      </div>

      {/* 2. Main Content: AI Insights, Personalized Feed, Trending, and Exploration Callout */}
      <div className="space-y-8 min-w-0">
        {/* AI Insights Bar */}
        <AIInsights
          items={recData?.results || []}
          cardType={cardType}
          type={type}
          userId={user}
          onSelectItem={onSelectItem}
          isLoading={isLoading}
        />

        {/* Personalized Recommendations Section */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--color-border)] pb-3">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h3 className="text-lg font-bold text-[var(--color-text)]">
                Personalized Recommendations
              </h3>
              {recData && <ModeBadge mode={recData.mode} />}
              <span className="text-xs text-[var(--color-text-secondary)] bg-[var(--color-surface)] px-2 py-0.5 rounded-[4px] border border-[var(--color-border)] tabular-nums">
                {meta.catalogLabel}
              </span>
            </div>

            {/* k Selector (5, 10, 20) */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--color-text-muted)] flex items-center gap-1">
                <SlidersHorizontal className="h-3 w-3" /> Show:
              </span>
              <div
                role="group"
                aria-label="Number of recommendations"
                className="inline-flex rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5 text-xs"
              >
                {kOptions.map((kOpt) => {
                  const isActive = k === kOpt;
                  return (
                    <button
                      key={kOpt}
                      type="button"
                      onClick={() => onKChange(kOpt)}
                      className={`px-2.5 py-1 text-xs font-semibold rounded-[4px] transition-all cursor-pointer tabular-nums focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)] ${
                        isActive
                          ? 'bg-[var(--color-elevated)] text-[var(--color-accent-text)] border border-[var(--color-border)] shadow-xs'
                          : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
                      }`}
                    >
                      k={kOpt}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-5">
              {Array.from({ length: k }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 space-y-3"
                >
                  <Skeleton className="aspect-[2/3] w-full rounded-[4px] bg-[var(--color-elevated)]" />
                  <Skeleton className="h-4 w-4/5 bg-[var(--color-elevated)]" />
                  <Skeleton className="h-3 w-1/2 bg-[var(--color-elevated)]" />
                </div>
              ))}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && (!recData || recData.results.length === 0) && (
            <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
              <EmptyState
                title="No recommendations generated"
                description={`The model did not return any recommendations for User #${user} with k=${k}.`}
              />
            </div>
          )}

          {/* Recommendation Cards Grid */}
          {!isLoading && recData && recData.results.length > 0 && (
            <div
              role="region"
              aria-label="Recommendation results"
              className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-5"
            >
              {recData.results.slice(0, k).map((item, idx) => (
                <RecCard
                  key={`${item.item_id}-${idx}`}
                  item={item}
                  cardType={cardType}
                  onSelect={onSelectItem}
                  priority={idx < 3}
                />
              ))}
            </div>
          )}
        </div>

        {/* Trending Discovery Section */}
        <div className="space-y-4 pt-2">
          <div className="border-b border-[var(--color-border)] pb-2 flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-[var(--color-text)] flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-[var(--color-accent)]" />
                <span>Trending Now in {type.charAt(0).toUpperCase() + type.slice(1)}</span>
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Top popular {type} across the entire catalog baseline
              </p>
            </div>
          </div>

          {popularData && popularData.results.length > 0 && (
            <div
              role="region"
              aria-label={`Trending ${type}`}
              className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-5"
            >
              {popularData.results.slice(0, 3).map((item, idx) => (
                <RecCard
                  key={`popular-${item.item_id}-${idx}`}
                  item={item}
                  cardType={cardType}
                  onSelect={onSelectItem}
                />
              ))}
            </div>
          )}
        </div>

        {/* Quick Discovery Callout Banner */}
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-sm sm:text-base font-bold text-[var(--color-text)]">
              Ready to explore further?
            </h3>
            <p className="text-xs sm:text-sm text-[var(--color-text-secondary)] mt-0.5">
              Compare model recommendations side-by-side or simulate cold-start user journeys.
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Link
              href={`/?type=${type}&tab=compare`}
              className="px-4 py-2 bg-[var(--color-accent)] text-white text-xs font-bold rounded-[var(--radius-card)] hover:bg-[var(--color-accent-hover)] active:bg-[var(--color-accent-active)] transition-colors inline-flex items-center gap-1.5 focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)]"
            >
              <span>Compare Models</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <Link
              href={`/?type=${type}&tab=cold-start`}
              className="px-4 py-2 bg-[var(--color-elevated)] text-[var(--color-text)] text-xs font-semibold rounded-[var(--radius-card)] hover:bg-[var(--color-elevated)]/80 border border-[var(--color-border)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)]"
            >
              Cold Start Demo
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
