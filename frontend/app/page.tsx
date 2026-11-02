'use client';

import React, { Suspense } from 'react';
// import { AlertCircle, Sparkles } from 'lucide-react';
import { AlertCircle, Search } from 'lucide-react';
import { AppHeader } from '@/components/shell/AppHeader';
import { TabNavigation } from '@/components/shell/TabNavigation';
import { useUrlState } from '@/lib/hooks/useUrlState';
import { useTypes } from '@/lib/api/hooks';
import { ForYouTab } from '@/components/tabs/ForYouTab';
import { CompareTab } from '@/components/tabs/CompareTab';
import { ColdStartTab } from '@/components/tabs/ColdStartTab';
import { EvaluationTab } from '@/components/tabs/EvaluationTab';
import { ItemDrawer } from '@/components/features/ItemDrawer';
import { ChatPanel } from '@/components/features/ChatPanel';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { Sparkles } from 'lucide-react';

function DashboardContent() {
  const [isChatOpen, setIsChatOpen] = React.useState(false);
  const {
    type,
    tab,
    user,
    k,
    item,
    setTab,
    setUser,
    setK,
    setItem,
    switchType,
  } = useUrlState();

  const cardType: 'movie' | 'product' | 'article' =
    type === 'products' ? 'product' : type === 'articles' ? 'article' : 'movie';

  const { isError: isTypesError, refetch: refetchTypes } = useTypes();

  if (isTypesError) {
    return (
      <div className="flex-1 flex flex-col bg-[var(--color-bg)] text-[var(--color-text)] min-h-screen">
        <header className="sticky top-0 z-40 w-full border-b border-[var(--color-border)] bg-[var(--color-bg)]">
          <div className="max-w-shell mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-[4px] bg-[var(--color-accent)] text-white flex items-center justify-center font-bold text-xs shadow-sm">
                <Search className="h-4 w-4" />
              </div>
              <span className="font-bold text-sm sm:text-base tracking-tight text-[var(--color-text)]">
                Discovery Engine
              </span>
            </div>
          </div>
        </header>
        <main className="flex-1 max-w-shell w-full mx-auto px-4 sm:px-6 py-12 flex items-center justify-center">
          <div
            role="alert"
            className="rounded-[var(--radius-card)] border border-red-500/30 bg-red-950/20 p-8 max-w-lg w-full text-center space-y-4"
          >
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 text-red-400">
              <AlertCircle className="h-6 w-6" />
            </div>
            <div className="space-y-2">
              <h2 className="text-lg font-bold text-[var(--color-text)]">
                Recommender Service Unavailable
              </h2>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Could not connect to the Discovery Engine backend API. Please ensure the backend server is running.
              </p>
            </div>
            <Button
              onClick={() => refetchTypes()}
              className="w-full sm:w-auto"
            >
              Try again
            </Button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-[var(--color-bg)] text-[var(--color-text)] min-h-screen">
      <AppHeader
        currentType={type}
        onTypeChange={(newType, defaultUser) => switchType(newType, defaultUser)}
        currentUser={user}
        onUserChange={setUser}
        onOpenChat={() => setIsChatOpen(true)}
      />
      <TabNavigation activeTab={tab} onTabChange={setTab} />

      <main className="flex-1 max-w-shell w-full mx-auto px-4 sm:px-6 py-8 lg:py-10">
        {/* Tab 1: For You */}
        {tab === 'for-you' && (
          <ForYouTab
            type={type}
            user={user}
            k={k}
            onKChange={setK}
            onSelectItem={(selected) => setItem(selected.item_id)}
          />
        )}

        {/* Tab 2: Compare */}
        {tab === 'compare' && (
          <CompareTab
            type={type}
            user={user}
            k={k}
            onKChange={setK}
            onSelectItem={(selected) => setItem(selected.item_id)}
          />
        )}

        {/* Tab 3: Cold Start */}
        {tab === 'cold-start' && (
          <ColdStartTab
            type={type}
            k={k}
            onKChange={setK}
            onSelectItem={(selected) => setItem(selected.item_id)}
          />
        )}

        {/* Tab 4: Evaluation */}
        {tab === 'evaluation' && (
          <EvaluationTab type={type} />
        )}
      </main>

      {/* Item Details Drawer (accessible deep-linked dialog) */}
      <ItemDrawer
        type={type}
        itemId={item}
        cardType={cardType}
        onClose={() => setItem(null)}
        onSelectItem={(selected) => setItem(selected.item_id)}
      />

      {/* Floating Chat Launcher (no pulse animation) */}
      <button
        type="button"
        onClick={() => setIsChatOpen(true)}
        aria-label="Open Discovery Assistant"
        className="fixed bottom-6 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-accent)] text-white shadow-xl hover:bg-[var(--color-accent-hover)] transition-transform hover:scale-105 focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)] cursor-pointer"
      >
        <Sparkles className="h-5 w-5" />
      </button>

      {/* Discovery Assistant Chatbot Dialog */}
      <ChatPanel
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        activeType={type}
        activeUserId={user}
        onSelectItem={(selected) => setItem(selected.item_id)}
      />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex flex-col bg-[var(--color-bg)] text-[var(--color-text)] p-6 space-y-6 max-w-shell mx-auto">
          <Skeleton className="h-16 w-full rounded-[var(--radius-card)] bg-[var(--color-surface)]" />
          <Skeleton className="h-12 w-full rounded-[var(--radius-card)] bg-[var(--color-surface)]" />
          <Skeleton className="h-96 w-full rounded-[var(--radius-card)] bg-[var(--color-surface)]" />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
