'use client';

import React from 'react';
import {
  BookOpen,
  GitBranch,
  ShieldCheck,
  AlertTriangle,
  ExternalLink,
  Code2,
  Database,
  Layers,
} from 'lucide-react';
import { useAbout } from '@/lib/api/hooks';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/ui/ErrorState';

export function AboutTab() {
  const { data: aboutData, isLoading, isError, refetch } = useAbout();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24 w-full bg-[var(--color-surface)]" />
        <Skeleton className="h-64 w-full bg-[var(--color-surface)]" />
        <Skeleton className="h-48 w-full bg-[var(--color-surface)]" />
      </div>
    );
  }

  if (isError || !aboutData) {
    return (
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <ErrorState
          title="About information unavailable"
          message="Could not load system attribution and provenance metadata from /v1/about."
          onRetry={refetch}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* 1. Header & System Attribution Banner */}
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--color-border)] pb-4">
          <div>
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-[var(--color-accent)]" />
              <h2 className="text-lg font-bold text-[var(--color-text)]">
                {aboutData.title} <span className="text-xs text-[var(--color-accent-text)] font-mono">v{aboutData.version}</span>
              </h2>
            </div>
            <p className="text-sm text-[var(--color-text-secondary)] mt-1">
              {aboutData.description}
            </p>
          </div>
          <div className="rounded bg-[var(--color-elevated)] border border-[var(--color-border)] px-3 py-1.5 text-[12px] text-[var(--color-text-muted)]">
            MIT Licensed Reference Implementation
          </div>
        </div>

        {/* Derivation Statement */}
        <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] border border-[var(--color-border)] p-4 text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-[var(--color-text)] flex items-center gap-1.5">
              <GitBranch className="h-3.5 w-3.5 text-[var(--color-accent)]" /> Recommenders Derivation Statement
            </span>
            <a
              href="https://github.com/recommenders-team/recommenders"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[var(--color-accent-text)] hover:underline text-[12px]"
            >
              <span>recommenders-team/recommenders</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <p className="text-[var(--color-text-secondary)] leading-relaxed">
            This project contains code <strong>derived from Microsoft Recommenders</strong> (v1.2.1, PyPI release{' '}
            <code className="text-[var(--color-text)] font-mono">recommenders==1.2.1</code>), licensed under the MIT License.
            The vendored package (<code className="text-[var(--color-text)] font-mono">backend/discovery/</code>) has been
            trimmed of heavy framework dependencies (TensorFlow, PyTorch, Azure, Spark) and patched for minimal compatibility
            while maintaining mathematical equivalence.
          </p>
          <p className="text-[12px] text-[var(--color-text-muted)] italic">
            {aboutData.non_commercial_notice}
          </p>
        </div>
      </div>

      {/* 2. Architecture Diagram (SVG) */}
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 space-y-4">
        <h3 className="text-sm font-bold text-[var(--color-text)] flex items-center gap-2">
          <Layers className="h-4 w-4 text-[var(--color-accent)]" />
          <span>System Architecture & Pipeline Flow</span>
        </h3>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Decoupled end-to-end architecture from raw multi-domain datasets to FastAPI serving and Next.js frontend.
        </p>

        {/* Flowchart Diagram in SVG */}
        <div
          tabIndex={0}
          role="region"
          aria-label="System architecture diagram flowchart"
          className="w-full overflow-x-auto py-2 focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent)]"
        >
          <svg
            viewBox="0 0 780 140"
            role="img"
            className="w-full min-w-[700px] h-32 select-none"
            aria-label="System architecture diagram"
          >
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 8 5 L 0 9 z" fill="#71717A" />
              </marker>
            </defs>

            {/* Step 1: Raw Data */}
            <g transform="translate(10, 40)">
              <rect width="105" height="55" rx="6" fill="#141414" stroke="#2A2A2A" strokeWidth="1" />
              <text x="52" y="24" fill="#FFFFFF" fontSize="11" fontWeight="bold" textAnchor="middle">Raw Data</text>
              <text x="52" y="40" fill="#71717A" fontSize="9" textAnchor="middle">ML1M / Amazon / MIND</text>
            </g>

            {/* Arrow 1 */}
            <line x1="115" y1="67" x2="135" y2="67" stroke="#71717A" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Step 2: Adapters */}
            <g transform="translate(140, 40)">
              <rect width="105" height="55" rx="6" fill="#141414" stroke="#2A2A2A" strokeWidth="1" />
              <text x="52" y="24" fill="#FFFFFF" fontSize="11" fontWeight="bold" textAnchor="middle">Adapters</text>
              <text x="52" y="40" fill="#71717A" fontSize="9" textAnchor="middle">Canonical Schema</text>
            </g>

            {/* Arrow 2 */}
            <line x1="245" y1="67" x2="265" y2="67" stroke="#71717A" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Step 3: Models */}
            <g transform="translate(270, 40)">
              <rect width="105" height="55" rx="6" fill="#1F1F1F" stroke="#E50914" strokeWidth="1.5" />
              <text x="52" y="24" fill="#FF4A53" fontSize="11" fontWeight="bold" textAnchor="middle">Model Registry</text>
              <text x="52" y="40" fill="#D4D4D8" fontSize="9" textAnchor="middle">SAR / TF-IDF Profile</text>
            </g>

            {/* Arrow 3 */}
            <line x1="375" y1="67" x2="395" y2="67" stroke="#71717A" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Step 4: Evaluation */}
            <g transform="translate(400, 40)">
              <rect width="105" height="55" rx="6" fill="#141414" stroke="#2A2A2A" strokeWidth="1" />
              <text x="52" y="24" fill="#FFFFFF" fontSize="11" fontWeight="bold" textAnchor="middle">Eval Harness</text>
              <text x="52" y="40" fill="#71717A" fontSize="9" textAnchor="middle">Temporal / Bootstrap</text>
            </g>

            {/* Arrow 4 */}
            <line x1="505" y1="67" x2="525" y2="67" stroke="#71717A" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Step 5: FastAPI */}
            <g transform="translate(530, 40)">
              <rect width="105" height="55" rx="6" fill="#141414" stroke="#2A2A2A" strokeWidth="1" />
              <text x="52" y="24" fill="#FFFFFF" fontSize="11" fontWeight="bold" textAnchor="middle">FastAPI Engine</text>
              <text x="52" y="40" fill="#71717A" fontSize="9" textAnchor="middle">REST API / OpenAPI</text>
            </g>

            {/* Arrow 5 */}
            <line x1="635" y1="67" x2="655" y2="67" stroke="#71717A" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Step 6: Next.js */}
            <g transform="translate(660, 40)">
              <rect width="105" height="55" rx="6" fill="#1F1F1F" stroke="#E50914" strokeWidth="1.5" />
              <text x="52" y="24" fill="#FF4A53" fontSize="11" fontWeight="bold" textAnchor="middle">Next.js 16 UI</text>
              <text x="52" y="40" fill="#D4D4D8" fontSize="9" textAnchor="middle">React 19 Dashboard</text>
            </g>
          </svg>
        </div>
      </div>

      {/* 3. Original vs. Derived Code Table */}
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 space-y-4">
        <h3 className="text-sm font-bold text-[var(--color-text)] flex items-center gap-2">
          <Code2 className="h-4 w-4 text-[var(--color-accent)]" />
          <span>Original vs. Derived Codebase Division</span>
        </h3>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Full transparency regarding newly authored code versus third-party open-source algorithms.
        </p>

        <div
          tabIndex={0}
          role="region"
          aria-label="Original vs Derived Codebase Division Table"
          className="overflow-x-auto focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent)]"
        >
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-[var(--color-text-muted)] font-semibold">
                <th className="py-2.5 pr-4">Subsystem / Path</th>
                <th className="py-2.5 px-3">Classification</th>
                <th className="py-2.5 px-3">Engineering Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]/60">
              <tr className="hover:bg-[var(--color-elevated)]/40 transition-colors">
                <td className="py-2.5 pr-4 font-mono text-[var(--color-text)]">backend/discovery/</td>
                <td className="py-2.5 px-3">
                  <span className="rounded bg-amber-950/40 text-amber-400 border border-amber-800/40 px-2 py-0.5 text-[12px] font-semibold">
                    Derived (MIT)
                  </span>
                </td>
                <td className="py-2.5 px-3 text-[var(--color-text-secondary)]">
                  Microsoft Recommenders core algorithms (SAR item similarity, TF-IDF news representation, chronological splitters, evaluation metrics). Stripped of deep learning dependencies.
                </td>
              </tr>
              <tr className="hover:bg-[var(--color-elevated)]/40 transition-colors">
                <td className="py-2.5 pr-4 font-mono text-[var(--color-text)]">backend/engine/</td>
                <td className="py-2.5 px-3">
                  <span className="rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40 px-2 py-0.5 text-[12px] font-semibold">
                    Original Work
                  </span>
                </td>
                <td className="py-2.5 px-3 text-[var(--color-text-secondary)]">
                  Cross-domain adapter pipeline (Movies, Products, Articles), canonical schema transformation, artifact serialisation, cold-start history normalizer, and invariant test harness.
                </td>
              </tr>
              <tr className="hover:bg-[var(--color-elevated)]/40 transition-colors">
                <td className="py-2.5 pr-4 font-mono text-[var(--color-text)]">backend/api/</td>
                <td className="py-2.5 px-3">
                  <span className="rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40 px-2 py-0.5 text-[12px] font-semibold">
                    Original Work
                  </span>
                </td>
                <td className="py-2.5 px-3 text-[var(--color-text-secondary)]">
                  FastAPI REST routing, Pydantic v2 schemas, item search index, latency benchmarking, and unified error handling with RFC 7807 compliance.
                </td>
              </tr>
              <tr className="hover:bg-[var(--color-elevated)]/40 transition-colors">
                <td className="py-2.5 pr-4 font-mono text-[var(--color-text)]">frontend/</td>
                <td className="py-2.5 px-3">
                  <span className="rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40 px-2 py-0.5 text-[12px] font-semibold">
                    Original Work
                  </span>
                </td>
                <td className="py-2.5 px-3 text-[var(--color-text-secondary)]">
                  Next.js 16 App Router dashboard, React 19 UI, Tailwind v4 entertainment tokens, deep-linked URL synchronization, and accessible keyboard navigation.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Dataset Citations & Academic Attribution */}
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 space-y-4">
        <h3 className="text-sm font-bold text-[var(--color-text)] flex items-center gap-2">
          <Database className="h-4 w-4 text-[var(--color-accent)]" />
          <span>Dataset Citations & Research Licenses</span>
        </h3>

        <div className="space-y-3 text-xs">
          {aboutData.attributions.map((attr) => (
            <div
              key={attr.name}
              className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] border border-[var(--color-border)] p-4 space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-[var(--color-text)]">{attr.name}</h4>
                <span className="text-[12px] font-semibold text-[var(--color-accent-text)] bg-[var(--color-bg)] px-2 py-0.5 rounded border border-[var(--color-border)]">
                  {attr.license}
                </span>
              </div>
              <p className="text-[var(--color-text-secondary)] italic leading-relaxed font-serif">
                &ldquo;{attr.citation}&rdquo;
              </p>
              <div className="flex items-center justify-between pt-1 text-[12px]">
                <span className="text-[var(--color-text-muted)]">{attr.original_vs_derived}</span>
                <a
                  href={attr.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:underline"
                >
                  <span>Data Source</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          ))}

          {/* MIND and Synthetic Notice */}
          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] border border-[var(--color-border)] p-4 space-y-1.5">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-[var(--color-text)]">MIND: Microsoft News Dataset</h4>
              <span className="text-[12px] font-semibold text-neutral-300 bg-[var(--color-bg)] px-2 py-0.5 rounded border border-[var(--color-border)]">
                Microsoft Research MSR-LA License
              </span>
            </div>
            <p className="text-[var(--color-text-secondary)] italic leading-relaxed font-serif">
              &ldquo;Wu, F., et al. (2020). MIND: A Large-scale Dataset for News Recommendation. Proceedings of the 58th Annual Meeting of the ACL, 3597–3606.&rdquo;
            </p>
            <p className="text-[12px] text-[var(--color-text-muted)] pt-0.5">
              Includes fallback support for synthetic offline test partitions (explicitly marked in provenance banners) to guarantee 100% offline reproducibility without external network downloads.
            </p>
          </div>

          {/* TMDB Poster Attribution */}
          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] border border-[var(--color-border)] p-4 space-y-1.5">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-[var(--color-text)]">The Movie Database (TMDB)</h4>
              <span className="text-[10px] font-semibold text-[var(--color-accent-text)] bg-[var(--color-bg)] px-2 py-0.5 rounded border border-[var(--color-border)]">
                API Attribution
              </span>
            </div>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Movie poster artwork is dynamically queried via the TMDB API. <strong>This product uses the TMDB API but is not endorsed or certified by TMDB.</strong>
            </p>
          </div>

          {/* Google Gemini LLM Concierge Attribution */}
          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] border border-[var(--color-border)] p-4 space-y-1.5">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-[var(--color-text)]">Google Gemini API (Discovery Assistant)</h4>
              <span className="text-[10px] font-semibold text-[var(--color-accent-text)] bg-[var(--color-bg)] px-2 py-0.5 rounded border border-[var(--color-border)]">
                AI Service Notice
              </span>
            </div>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              The Discovery Assistant chatbot utilizes the Google Gemini API (gemini-2.5-flash) as an LLM concierge. <strong>AI-generated responses and natural-language explanations may contain inaccuracies;</strong> all recommended items and ranks are grounded in and strictly validated against the engine&apos;s offline catalog. Only aggregate category shares and candidate item titles are sent upstream; zero raw user IDs or personal data are transmitted.
            </p>
          </div>
        </div>
      </div>

      {/* 5. Documented Limitations & Failure Modes (from DECISIONS.md D-018) */}
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 space-y-4">
        <h3 className="text-sm font-bold text-[var(--color-text)] flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <span>Known Limitations & Failure Modes (Decision Record D-018)</span>
        </h3>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Intellectual honesty regarding collaborative filtering trade-offs and domain assumptions.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] p-4 border border-[var(--color-border)] space-y-2">
            <h4 className="font-bold text-[var(--color-text)]">1. Popularity Bias & Monoculture</h4>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Global popularity achieves high HitRate by concentrating on blockbuster items (~1.3% catalogue coverage in MovieLens).
              SAR mitigates this by expanding catalogue exploration by 3.5x with personalized genre matching.
            </p>
          </div>

          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] p-4 border border-[var(--color-border)] space-y-2">
            <h4 className="font-bold text-[var(--color-text)]">2. Cold-Start Collaborative Matrix Sparsity</h4>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Items with zero interactions in training have an all-zero row in co-occurrence matrices. While collaborative models cannot score unrated items,
              content-based TF-IDF models index new articles immediately from textual metadata.
            </p>
          </div>

          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] p-4 border border-[var(--color-border)] space-y-2">
            <h4 className="font-bold text-[var(--color-text)]">3. Cross-Domain Signal Heterogeneity</h4>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Explicit ratings (Movies 1–5), verified transactions (Products), and implicit browsing clicks (Articles) carry fundamentally distinct semantic costs and acquisition dynamics.
            </p>
          </div>

          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] p-4 border border-[var(--color-border)] space-y-2">
            <h4 className="font-bold text-[var(--color-text)]">4. Cold-Start Valleys (&le; 5 Interactions)</h4>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              In sparse e-commerce, a single initial purchase can temporarily degrade performance below popularity fallback before recovering once &ge; 3 items establish a taste vector.
            </p>
          </div>

          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] p-4 border border-[var(--color-border)] space-y-2">
            <h4 className="font-bold text-[var(--color-text)]">5. News Freshness Horizon & Recency Decay</h4>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Articles decay within 24 hours. The candidate pool is restricted to active recency windows, trading off long-term topic matching for guaranteed fresh content.
            </p>
          </div>

          <div className="rounded-[var(--radius-card)] bg-[var(--color-elevated)] p-4 border border-[var(--color-border)] space-y-2">
            <h4 className="font-bold text-[var(--color-text)]">6. Counterfactual Logging Policy Bias</h4>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Offline news metrics evaluate candidates pre-selected by historical production systems; live user engagement may differ due to presentation position bias and fatigue.
            </p>
          </div>
        </div>
      </div>

      {/* 6. Non-Commercial College Showcase Statement */}
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 flex items-center gap-3 text-xs">
        <ShieldCheck className="h-5 w-5 text-emerald-500 shrink-0" />
        <p className="text-[var(--color-text-secondary)] leading-relaxed">
          <strong>Non-Commercial College Showcase:</strong> Developed strictly for educational evaluation and student portfolio demonstration.
          No commercial rights are asserted; all dataset licenses, copyrights, and Microsoft Recommenders attributions remain with their original authors.
        </p>
      </div>
    </div>
  );
}
