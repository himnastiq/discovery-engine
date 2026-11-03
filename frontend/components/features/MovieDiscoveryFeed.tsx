'use client';

import React, { useMemo } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  Clapperboard,
  Heart,
  Target,
  ArrowRight,
  SlidersHorizontal,
} from 'lucide-react';
import { useUserState } from '@/lib/user-state';
import { useHybridRecommendations } from '@/lib/hooks/useHybridRecommendations';
import { CRITICALLY_ACCLAIMED_MOVIES } from '@/lib/curated';
import { AIInsights } from './AIInsights';
import { MovieCarouselRow } from './MovieCarouselRow';
import { ProfileCard } from './ProfileCard';
import type { ScoredItem } from '@/lib/api/schemas';
import type { CarouselMovie } from '@/lib/curated';
import type { RecommendResponse } from '@/lib/api/client';

export interface MovieDiscoveryFeedProps {
  user: string;
  k: number;
  onKChange: (k: number) => void;
  onSelectItem?: (item: ScoredItem) => void;
  recData?: RecommendResponse | null;
  isLoading?: boolean;
}

export function MovieDiscoveryFeed({
  user,
  k,
  onKChange,
  onSelectItem,
  recData: propRecData,
  isLoading: propIsLoading,
}: MovieDiscoveryFeedProps) {
  const { state, isHydrated } = useUserState();

  const movieEntries = useMemo(
    () => Object.values(state.movies),
    [state.movies]
  );

  const activeEntries = useMemo(
    () =>
      movieEntries.filter(
        (m) =>
          m.rating !== null ||
          m.liked ||
          m.inWatchlist ||
          m.watched ||
          (m.watchProgress ?? 0) > 0
      ),
    [movieEntries]
  );

  const hasActivity = activeEntries.length > 0;
  const hasGenreSeed = state.favoriteGenres.length >= 3;
  // If demo user is selected (e.g. user '1'), they also have taste signals from dataset
  const hasTasteSignal = hasActivity || hasGenreSeed || Boolean(user);

  const watchlistIds = useMemo(
    () =>
      movieEntries
        .filter((m) => m.inWatchlist)
        .sort((a, b) => new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime())
        .map((m) => m.movieId),
    [movieEntries]
  );

  const likedIds = useMemo(
    () =>
      movieEntries
        .filter((m) => m.liked)
        .sort((a, b) => new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime())
        .map((m) => m.movieId),
    [movieEntries]
  );

  const ratedIds = useMemo(
    () =>
      movieEntries
        .filter((m) => m.rating !== null)
        .sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0))
        .map((m) => m.movieId),
    [movieEntries]
  );

  const recentlyWatched = useMemo(
    () =>
      movieEntries
        .filter((m) => m.watched && m.watchedAt)
        .sort(
          (a, b) =>
            new Date(b.watchedAt!).getTime() - new Date(a.watchedAt!).getTime()
        )
        .map((m) => m.movieId),
    [movieEntries]
  );

  const {
    forYou: hookRecommendedMovies,
    trending: trendingMovies,
    becauseYouLiked,
    topGenrePicks,
  } = useHybridRecommendations(user, propRecData);

  const recommendedMovies = useMemo(() => {
    if (propRecData?.results) {
      return propRecData.results.map((item, idx) => ({
        id: item.item_id,
        title: item.title,
        poster: item.image_url || null,
        year: item.year || null,
        rating: item.display_score ? Number((item.display_score * 10).toFixed(1)) : null,
        rank: idx + 1,
        matchPercentage: Math.round(item.display_score * 100),
        reason: item.reason?.text,
        categories: item.categories,
      }));
    }
    return hookRecommendedMovies;
  }, [propRecData, hookRecommendedMovies]);

  const insightItems: ScoredItem[] = useMemo(() => {
    if (propRecData?.results && propRecData.results.length > 0) {
      return propRecData.results;
    }
    return recommendedMovies.map((m) => ({
      item_id: String(m.id),
      title: m.title,
      subtitle: m.reason ?? null,
      categories: m.categories ?? [],
      year: typeof m.year === 'number' ? m.year : null,
      image_url: m.poster,
      score: m.rating ? m.rating / 10 : 0.85,
      display_score: m.matchPercentage ? m.matchPercentage / 100 : 0.85,
      meta: {},
    }));
  }, [propRecData, recommendedMovies]);

  const handleCarouselSelect = (carouselMovie: CarouselMovie) => {
    if (!onSelectItem) return;
    const item: ScoredItem = {
      item_id: String(carouselMovie.id),
      title: carouselMovie.title,
      subtitle: carouselMovie.reason ?? null,
      categories: carouselMovie.categories ?? [],
      year: typeof carouselMovie.year === 'number' ? carouselMovie.year : null,
      image_url: carouselMovie.poster,
      score: carouselMovie.rating ? carouselMovie.rating / 10 : 0.8,
      display_score: carouselMovie.matchPercentage ? carouselMovie.matchPercentage / 100 : 0.8,
      meta: {},
    };
    onSelectItem(item);
  };

  const kOptions = [5, 10, 20];

  if (!isHydrated || propIsLoading) {
    return <MovieFeedSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Grid: Sidebar (ProfileCard) + Main Content (Feed) */}
      <div className="grid gap-8 lg:grid-cols-[20rem_minmax(0,1fr)] lg:items-start">
        {/* User Profile Summary (Sidebar as in Articles and Products) */}
        <div>
          <ProfileCard type="movies" userId={user} />
        </div>

        {/* Main Content: AI Insights and Recommendations Feed */}
        <div className="space-y-6 min-w-0">
          {/* AI Insights Rectangle (Replaces TasteProfiler) */}
          <AIInsights
            items={insightItems}
            cardType="movie"
            type="movies"
            userId={user}
            onSelectItem={onSelectItem}
            isLoading={propIsLoading}
          />

          {/* Recommendations / Carousels */}
          {hasTasteSignal ? (
            <div className="space-y-6">
              {/* Recently Watched */}
              {recentlyWatched.length > 0 && (
                <MovieCarouselRow
                  title="Recently Watched"
                  ids={recentlyWatched}
                  onSelectItem={handleCarouselSelect}
                />
              )}

              {/* Your Watchlist */}
              {watchlistIds.length > 0 && (
                <MovieCarouselRow
                  title="Your Watchlist"
                  ids={watchlistIds}
                  onSelectItem={handleCarouselSelect}
                />
              )}

              {/* Liked Movies */}
              {likedIds.length > 0 && (
                <MovieCarouselRow
                  title="Liked Movies"
                  ids={likedIds}
                  onSelectItem={handleCarouselSelect}
                />
              )}

              {/* Top Rated by You */}
              {ratedIds.length > 0 && (
                <MovieCarouselRow
                  title="Top Rated by You"
                  ids={ratedIds}
                  onSelectItem={handleCarouselSelect}
                />
              )}

              {/* Personalized Recommendations with k selector */}
              {recommendedMovies.length > 0 && (
                <div className="relative">
                  <div className="flex items-center justify-between mb-1">
                    <span className="sr-only">Personalized Recommendations Controls</span>
                    <div className="ml-auto flex items-center gap-2 mb-2">
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
                                  ? 'bg-[var(--color-elevated)] text-[var(--color-accent-text)] border border-[var(--color-border)]'
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

                  <MovieCarouselRow
                    title="Personalized Recommendations"
                    subtitle="Personalized discovery based on real-time interest"
                    items={recommendedMovies.slice(0, k)}
                    onSelectItem={handleCarouselSelect}
                  />
                </div>
              )}

              {/* Because You Liked / Rated Row */}
              {becauseYouLiked && (
                <MovieCarouselRow
                  title={`Because You ${
                    becauseYouLiked.sourceMovie.interaction === 'rated' ? 'Rated' : 'Liked'
                  } ${becauseYouLiked.sourceMovie.title}`}
                  subtitle="Curated titles sharing similar tone, genre blend, and story depth"
                  items={becauseYouLiked.recommendations}
                  onSelectItem={handleCarouselSelect}
                />
              )}

              {/* Deep-Dive Top Genre Picks */}
              {topGenrePicks && topGenrePicks.movies.length > 0 && (
                <MovieCarouselRow
                  title={`Top Picks in ${topGenrePicks.genreName}`}
                  subtitle="Highest scoring recommendations in your primary genre focus"
                  items={topGenrePicks.movies}
                  onSelectItem={handleCarouselSelect}
                />
              )}

              {/* Trending Now */}
              {trendingMovies.length > 0 && (
                <MovieCarouselRow
                  title="Trending Now"
                  subtitle="Top popular movies across the catalogue"
                  items={trendingMovies}
                  onSelectItem={handleCarouselSelect}
                />
              )}

              {/* Critically Acclaimed Masterworks */}
              <MovieCarouselRow
                title="Critically Acclaimed Masterpieces"
                subtitle="Universally praised cinema to build your taste profile"
                items={CRITICALLY_ACCLAIMED_MOVIES}
                onSelectItem={handleCarouselSelect}
              />
            </div>
          ) : (
            <MovieFeedEmptyState />
          )}

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
                href="/?type=movies&tab=compare"
                className="px-4 py-2 bg-[var(--color-accent)] text-white text-xs font-bold rounded-[var(--radius-card)] hover:bg-[var(--color-accent-hover)] active:bg-[var(--color-accent-active)] transition-colors inline-flex items-center gap-1.5 focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)]"
              >
                <span>Compare Models</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Link
                href="/?type=movies&tab=cold-start"
                className="px-4 py-2 bg-[var(--color-elevated)] text-[var(--color-text)] text-xs font-semibold rounded-[var(--radius-card)] hover:bg-[var(--color-elevated)]/80 border border-[var(--color-border)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)]"
              >
                Cold Start Demo
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MovieFeedSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-hidden="true">
      <div className="border-b border-[var(--color-border)] pb-4 space-y-2">
        <div className="h-7 w-56 rounded bg-[var(--color-surface)]" />
        <div className="h-4 w-80 max-w-full rounded bg-[var(--color-surface)]" />
      </div>
      <div className="grid gap-8 lg:grid-cols-[20rem_minmax(0,1fr)] lg:items-start">
        <div className="h-72 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)]" />
        <div className="space-y-6">
          <div className="h-32 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)]" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="aspect-[2/3] rounded-[var(--radius-card)] bg-[var(--color-surface)]"
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function MovieFeedEmptyState() {
  const steps = [
    {
      icon: <Target className="h-4 w-4" />,
      title: 'Pick your genres',
      description: 'Choose 3 or more genres above.',
    },
    {
      icon: <Heart className="h-4 w-4" />,
      title: 'Save or rate movies',
      description: 'Add to your watchlist or like titles.',
    },
    {
      icon: <Sparkles className="h-4 w-4" />,
      title: 'Get your feed',
      description: 'Personalized carousels appear automatically.',
    },
  ];

  return (
    <section className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-10 text-center mb-6">
      <div className="flex flex-col items-center max-w-lg mx-auto">
        <div className="w-12 h-12 rounded-full bg-[var(--color-elevated)] border border-[var(--color-border)] flex items-center justify-center text-[var(--color-accent)] mb-4">
          <Clapperboard className="h-6 w-6" />
        </div>

        <h3 className="text-lg font-bold tracking-tight text-[var(--color-text)]">
          It&apos;s empty in here
        </h3>
        <p className="mt-1 text-xs sm:text-sm text-[var(--color-text-secondary)] leading-relaxed">
          Add movies to your watchlist, rate a few favorites, or pick your
          favorite genres above to generate personalized recommendations.
        </p>

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
          {steps.map((step) => (
            <div
              key={step.title}
              className="bg-[var(--color-elevated)] border border-[var(--color-border)] rounded-[var(--radius-card)] p-3 text-left"
            >
              <div className="flex items-center gap-1.5 text-[var(--color-accent-text)]">
                {step.icon}
                <span className="text-xs font-semibold text-[var(--color-text)]">
                  {step.title}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-[var(--color-text-muted)] leading-snug">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default MovieDiscoveryFeed;
