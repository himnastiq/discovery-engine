'use client';

import React, { useEffect, useRef, useState, useId } from 'react';
import {
  X,
  Send,
  RotateCcw,
  Sparkles,
  Bot,
  User,
  AlertCircle,
  Clock,
  Square,
  ShieldCheck,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { useTypes } from '@/lib/api/hooks';
import { PickCard } from './PickCard';
import { Badge } from '@/components/ui/Badge';
import type { ChatMessage, ChatPick, ScoredItem } from '@/lib/api/schemas';

export interface ChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
  activeType: string;
  activeUserId?: string | null;
  onSelectItem?: (item: ScoredItem) => void;
  triggerRef?: React.RefObject<HTMLElement | null>;
}

interface MessageEntry {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  picks?: ChatPick[];
  mode?: 'llm' | 'fallback';
  isError?: boolean;
}

let messageIdCounter = 0;
function getNextMessageId(role: string): string {
  messageIdCounter += 1;
  return `msg-${messageIdCounter}-${role}`;
}

export function ChatPanel({
  isOpen,
  onClose,
  activeType,
  activeUserId,
  onSelectItem,
  triggerRef,
}: ChatPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<MessageEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [retryAfterSeconds, setRetryAfterSeconds] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const panelTitleId = useId();

  // Status check for onboarding readiness
  const { data: statusData } = useQuery({
    queryKey: ['chatStatus'],
    queryFn: ({ signal }) => apiClient.getChatStatus(signal),
    staleTime: 60 * 1000,
  });

  // Dynamic content types to resolve starter prompts
  const { data: typesData } = useTypes();
  const currentTypeInfo = typesData?.types?.find((t) => t.id === activeType);
  const starterPrompts = currentTypeInfo?.starter_prompts?.length
    ? currentTypeInfo.starter_prompts
    : [
      'Suggest recommendations based on my profile',
      'What hidden gems do you recommend?',
      'Recommend top choices for my taste',
    ];

  // Focus restoration & initial focus
  useEffect(() => {
    if (isOpen) {
      previouslyFocusedRef.current =
        triggerRef?.current || (document.activeElement as HTMLElement);
      setTimeout(() => {
        panelRef.current?.focus();
      }, 50);
    } else {
      previouslyFocusedRef.current?.focus();
    }
  }, [isOpen, triggerRef]);

  // Focus trap & Escape listener
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'Tab') {
        if (!panelRef.current) return;
        const focusableElements = panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Rate limit countdown timer
  useEffect(() => {
    if (retryAfterSeconds === null || retryAfterSeconds <= 0) return;

    const timer = setInterval(() => {
      setRetryAfterSeconds((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(timer);
          return null;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [retryAfterSeconds]);

  // Abort in-flight request
  const handleAbort = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  };

  // Clear in-memory conversation
  const handleClear = () => {
    handleAbort();
    setMessages([]);
    setErrorMessage(null);
    setRetryAfterSeconds(null);
  };

  // Send message
  const handleSend = async (messageText?: string) => {
    const textToSend = (messageText !== undefined ? messageText : input).trim();
    if (!textToSend || isLoading) return;

    setInput('');
    setErrorMessage(null);

    const userMessage: MessageEntry = {
      id: getNextMessageId('user'),
      role: 'user',
      content: textToSend,
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const historyPayload: ChatMessage[] = newMessages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await apiClient.postChat(
        {
          type: activeType,
          user_id: activeUserId || null,
          messages: historyPayload,
        },
        controller.signal
      );

      const assistantMessage: MessageEntry = {
        id: getNextMessageId('assistant'),
        role: 'assistant',
        content: res.reply,
        picks: res.picks,
        mode: res.mode,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (res.meta?.retry_after_s) {
        setRetryAfterSeconds(res.meta.retry_after_s);
      }
    } catch (err: unknown) {
      if (controller.signal.aborted) {
        // User aborted intentionally
        return;
      }

      let errorDisplay = 'An unexpected error occurred. Please try again.';
      if (err && typeof err === 'object' && 'statusCode' in err) {
        const apiErr = err as { statusCode: number; details?: { retry_after?: number } };
        if (apiErr.statusCode === 429) {
          const retrySec = apiErr.details?.retry_after || 15;
          setRetryAfterSeconds(retrySec);
          errorDisplay = `Rate limit reached. Please wait ${retrySec} seconds before sending another message.`;
        }
      }

      setErrorMessage(errorDisplay);
      setMessages((prev) => [
        ...prev,
        {
          id: getNextMessageId('error'),
          role: 'assistant',
          content: errorDisplay,
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleRetryLast = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMsg) {
      // Remove any trailing error message
      setMessages((prev) => prev.filter((m) => !m.isError));
      handleSend(lastUserMsg.content);
    }
  };

  if (!isOpen) return null;

  const isConfigured = statusData?.ready ?? false;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/80 backdrop-blur-xs transition-opacity duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby={panelTitleId}
    >
      {/* Backdrop click area */}
      <div
        className="fixed inset-0 cursor-pointer"
        aria-hidden="true"
        onClick={onClose}
      />

      {/* Slide-out Sheet */}
      <div
        ref={panelRef}
        tabIndex={-1}
        className="relative z-10 flex h-[100dvh] w-full max-w-lg flex-col border-l border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl focus:outline-none pb-[env(safe-area-inset-bottom)]"
      >
        {/* Header */}
        <div className="sticky top-0 z-20 flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)]/95 px-5 py-3.5 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <div className="rounded-[4px] bg-[var(--color-elevated)] p-1.5 text-[var(--color-accent-text)] border border-[var(--color-border)]">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 id={panelTitleId} className="text-sm font-semibold text-[var(--color-text)]">
                  Discovery Assistant
                </h3>
                <Badge
                  variant="outline"
                  className="text-[10px] uppercase tracking-wider text-[var(--color-accent-text)] border-[var(--color-border)]"
                >
                  Concierge
                </Badge>
              </div>
              <p className="text-[11px] text-[var(--color-text-muted)]">
                LLM-augmented concierge over engine recommendations
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {messages.length > 0 && (
              <button
                type="button"
                onClick={handleClear}
                aria-label="Clear conversation"
                title="Clear conversation"
                className="rounded-[4px] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)] cursor-pointer"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close assistant panel"
              className="rounded-[4px] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)] cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Rate-limit active notification */}
        {retryAfterSeconds !== null && retryAfterSeconds > 0 && (
          <div
            role="status"
            className="flex items-center gap-2 border-b border-[var(--color-border)] bg-[var(--color-elevated)] px-4 py-2 text-xs text-[var(--color-accent-text)]"
          >
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>Rate limit cooldown: Retry available in {retryAfterSeconds}s</span>
          </div>
        )}

        {/* Message Log */}
        <div
          aria-live="polite"
          className="flex-1 overflow-y-auto p-4 space-y-4 text-sm"
        >
          {/* Unconfigured / Standby Onboarding Banner */}
          {!isConfigured && (
            <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-elevated)] p-4 text-[var(--color-text)]">
              <div className="flex items-start gap-3">
                <Bot className="h-5 w-5 text-[var(--color-accent-text)] shrink-0 mt-0.5" />
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold">Assistant in Standby</h4>
                  <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                    Discovery Assistant is standing by. Add your Gemini API key in the server
                    environment (`GEMINI_API_KEYS`) to activate conversational recommendations.
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    All core ML models (SAR, TF-IDF) and standard recommendation tabs remain fully
                    operational.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Conversation history */}
          {messages.length === 0 && isConfigured && (
            <div className="text-center py-8 text-[var(--color-text-muted)] space-y-3">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-elevated)] border border-[var(--color-border)] text-[var(--color-accent-text)]">
                <Bot className="h-6 w-6" />
              </div>
              <h4 className="text-sm font-medium text-[var(--color-text)]">
                How can I help you discover {currentTypeInfo?.display_name || 'items'}?
              </h4>
              <p className="text-xs max-w-xs mx-auto text-[var(--color-text-secondary)]">
                Ask for suggestions based on your taste profile, genre preferences, or similar items.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-elevated)] text-[var(--color-accent-text)] border border-[var(--color-border)]">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div
                className={`flex max-w-[85%] flex-col gap-2 rounded-[var(--radius-card)] p-3 text-xs leading-relaxed ${msg.role === 'user'
                    ? 'bg-[var(--color-accent-active)] text-white ml-auto'
                    : msg.isError
                      ? 'border border-[var(--color-error)]/40 bg-[var(--color-elevated)] text-[var(--color-error)]'
                      : 'border border-[var(--color-border)] bg-[var(--color-elevated)] text-[var(--color-text)]'
                  }`}
              >
                {/* Fallback badge */}
                {msg.mode === 'fallback' && (
                  <div className="flex items-center gap-1.5 text-[10px] font-medium text-[var(--color-text-muted)] border-b border-[var(--color-border)] pb-1.5">
                    <ShieldCheck className="h-3 w-3 text-[var(--color-success)]" />
                    <span>Answer from engine (offline fallback)</span>
                  </div>
                )}

                {/* Plain text message paragraphs */}
                <div className="space-y-2">
                  {msg.content.split('\n\n').map((paragraph, idx) => (
                    <p key={idx} className="whitespace-pre-wrap">
                      {paragraph}
                    </p>
                  ))}
                </div>

                {/* Pick cards */}
                {msg.picks && msg.picks.length > 0 && (
                  <div className="mt-2 space-y-2 pt-2 border-t border-[var(--color-border)]">
                    <p className="text-[11px] font-medium text-[var(--color-text-secondary)]">
                      Engine Candidate Picks:
                    </p>
                    {msg.picks.map((pick) => (
                      <PickCard
                        key={pick.item_id}
                        pick={pick}
                        cardType={currentTypeInfo?.card_type || 'movie'}
                        onSelect={onSelectItem}
                      />
                    ))}
                  </div>
                )}

                {/* Error with retry */}
                {msg.isError && (
                  <div className="mt-2 pt-2 border-t border-[var(--color-border)] flex items-center justify-between">
                    <span className="text-[10px] text-[var(--color-text-muted)]">Request failed</span>
                    <button
                      type="button"
                      onClick={handleRetryLast}
                      className="text-xs font-semibold underline text-[var(--color-accent-text)] hover:opacity-80 cursor-pointer"
                    >
                      Retry
                    </button>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-elevated)] text-[var(--color-text)] border border-[var(--color-border)]">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex gap-3 items-center text-[var(--color-text-secondary)]">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-elevated)] text-[var(--color-accent-text)] border border-[var(--color-border)]">
                <Bot className="h-4 w-4" />
              </div>
              <div className="flex items-center gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-elevated)] px-3 py-2 text-xs">
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent-text)] animate-bounce" />
                  <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent-text)] animate-bounce [animation-delay:0.2s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent-text)] animate-bounce [animation-delay:0.4s]" />
                </span>
                <span className="text-[var(--color-text-muted)]">Consulting recommendation engine...</span>
              </div>
              <button
                type="button"
                onClick={handleAbort}
                aria-label="Stop generating response"
                className="flex items-center gap-1 rounded-[4px] border border-[var(--color-border)] px-2 py-1 text-[11px] text-[var(--color-text-secondary)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)] cursor-pointer"
              >
                <Square className="h-3 w-3 fill-current" />
                <span>Stop</span>
              </button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Starter Prompts */}
        {isConfigured && messages.length === 0 && (
          <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/80 p-3">
            <p className="mb-2 text-[11px] font-medium text-[var(--color-text-muted)]">
              Starter Prompts:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => handleSend(prompt)}
                  className="rounded-[4px] border border-[var(--color-border)] bg-[var(--color-elevated)] px-2.5 py-1 text-xs text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-text)] transition-colors cursor-pointer text-left"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error notification banner */}
        {errorMessage && (
          <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 flex items-center justify-between text-xs text-[var(--color-error)]">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              type="button"
              onClick={handleRetryLast}
              className="font-medium underline hover:opacity-80 cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Input Footer */}
        <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                isConfigured
                  ? `Ask about ${currentTypeInfo?.display_name || 'recommendations'}...`
                  : 'Assistant standing by (configure keys in env)'
              }
              disabled={!isConfigured || isLoading || (retryAfterSeconds !== null && retryAfterSeconds > 0)}
              maxLength={500}
              className="flex-1 rounded-[4px] border border-[var(--color-border)] bg-[var(--color-elevated)] px-3 py-2 text-xs text-[var(--color-text)] placeholder-[var(--color-text-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)] disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={
                !input.trim() ||
                isLoading ||
                !isConfigured ||
                (retryAfterSeconds !== null && retryAfterSeconds > 0)
              }
              aria-label="Send message"
              className="flex h-8 w-8 items-center justify-center rounded-[4px] bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)]"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </form>

          {/* AI Notice */}
          <p className="mt-2 text-center text-[10px] text-[var(--color-text-muted)]">
            AI-generated recommendations may be inaccurate. Picks are grounded in engine candidates.
          </p>
        </div>
      </div>
    </div>
  );
}
