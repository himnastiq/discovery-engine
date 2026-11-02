# Discovery Engine: Evaluator Walkthrough & Demo Script

> **Target Presentation Time:** 5-7 minutes (Stopwatch baseline: 5 min 45 s)  
> **Derivation & License Notice:** This software is derived from [Microsoft Recommenders](https://github.com/recommenders-team/recommenders) (v1.2.1) under the [MIT License](https://opensource.org/licenses/MIT). Developed strictly for **non-commercial** educational and academic showcase use.

---

## 1. Pre-Demo Setup & Verification Checklist

Complete this checklist prior to presenting to evaluators:

1. **Verify Artifact Integrity:**
   - Confirm final artifacts exist in `artifacts/` (real datasets: MovieLens 1M, Amazon Video Games, MIND-small).
   - Ensure manifests match current code hash.
2. **Port Readiness & Process State:**
   - Confirm ports 8000 and 3000 are unallocated:
     ```powershell
     python tools/demo.py --stop
     ```
3. **Launch Demo Supervisor:**
   - Start unified demo:
     ```bash
     make demo
     ```
     *(or PowerShell without make)*
     ```powershell
     python tools/demo.py
     ```
   - Verify `/v1/health` reports status `ok` and all three content types are available.
4. **Browser & Network Configuration:**
   - Open Chrome at `http://localhost:3000` with desktop resolution set to 1280x800.
   - Network resilience: if offline, placeholder poster cards render gracefully without blocking.
   - Backup assets ready: pre-captured screenshots available in `docs/screenshots/`.

---

## 2. Demo Personas & Starting Users

The platform ships with pre-computed demo personas categorized by interaction density (`heavy`, `mainstream`, `niche`, `casual`). Always start with the primary showcase user for each vertical:

- **Movies Starting User:** User `210` (heavy persona, Action / Thriller affinity)
- **Products Starting User:** User `A119Q9NFGVOEJZ` (heavy persona, Video Games affinity)
- **Articles Starting User:** User `U1030` (heavy persona, News / Lifestyle affinity)

<!-- GENERATED:personas_table:START -->
| Domain | User ID | Persona Label | Interaction Count | Top Affinity Categories |
|---|---|---|---|---|
| **Movies** | `210` | `heavy` | 110 | Action, Thriller, Adventure |
| **Movies** | `18` | `heavy` | 305 | Action, Drama, Adventure |
| **Movies** | `318` | `mainstream` | 21 | Drama, Comedy, Children's |
| **Movies** | `144` | `mainstream` | 32 | Drama, Sci-Fi, Action |
| **Movies** | `57` | `niche` | 64 | Comedy, Drama, Action |
| **Movies** | `50` | `niche` | 43 | Drama, Comedy, Action |
| **Movies** | `273` | `heavy` | 187 | Comedy, Action, Drama |
| **Movies** | `225` | `heavy` | 507 | Drama, Comedy, Thriller |
| **Products** | `A119Q9NFGVOEJZ` | `heavy` | 91 | Video Games, Games, More Systems |
| **Products** | `A114TMHW9GRMPB` | `heavy` | 140 | Video Games, Games, PlayStation 3 |
| **Products** | `A11XB83K6SDSO9` | `mainstream` | 16 | Video Games, Games, PlayStation 3 |
| **Products** | `A11F5CNC4KJB3Q` | `mainstream` | 25 | Video Games, Xbox 360, Games |
| **Products** | `A1143YEAZYMYHJ` | `niche` | 22 | Video Games, Games, PlayStation 3 |
| **Products** | `A12GIOKE26ZFKJ` | `niche` | 45 | Video Games, Games, Kids & Family |
| **Products** | `A11IHV8N5A8IC7` | `casual` | 8 | Video Games, Games, Nintendo DS |
| **Products** | `A10FGXGHS2VS9` | `casual` | 5 | Video Games, Games, Nintendo DS |
| **Articles** | `U1030` | `heavy` | 112 | news, lifestyle, newsus |
| **Articles** | `U10103` | `heavy` | 225 | news, autos, newsus |
| **Articles** | `U10119` | `mainstream` | 19 | news, sports, football_nfl |
| **Articles** | `U1041` | `mainstream` | 22 | news, finance, lifestyle |
| **Articles** | `U10216` | `niche` | 71 | news, lifestyle, newsus |
| **Articles** | `U10257` | `niche` | 17 | news, video, animals |
| **Articles** | `U10435` | `casual` | 7 | movies, movies-celebrity, sports |
| **Articles** | `U10418` | `casual` | 5 | lifestyle, lifestyleroyals, tv |
<!-- GENERATED:personas_table:END -->

---

## 3. Structured Walkthrough Script (5-7 Minutes)

| Timestamp | Screen / View | Action & Demonstration | What It Proves (Repository Evidence) |
|---|---|---|---|
| **00:00 - 00:30** | Terminal & Shell Header | Introduce Discovery Engine. Highlight derivation statement (Microsoft Recommenders, MIT License, non-commercial educational use). Point out unified interface serving Movies, Products, and Articles. | Transparent licensing provenance and multi-domain scope ([`docs/ATTRIBUTION.md`](ATTRIBUTION.md), [`docs/ORIGINAL_VS_DERIVED.md`](ORIGINAL_VS_DERIVED.md)). |
| **00:30 - 01:45** | **Movies** (`/?type=movies&tab=for-you&user=210`) | Display For You tab for User `210`. Point out profile card (interaction count, top genres). Inspect top recommendations with reason badges ("Because you rated..."). Click a movie card to open Item Details Drawer showing metadata and item-to-item similarity recommendations. | Collaborative filtering via Simple Algorithm for Recommendation (SAR); explainable recommendations; deep-linked drawer dialog (`backend/engine/models/sar.py`, [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)). |
| **01:45 - 02:45** | **Movies Compare Tab** (`/?tab=compare`) | Switch to Compare tab. Demonstrate side-by-side comparison between "Popular for Everyone" and "Personalized for User #1". Toggle "User vs. User" comparison mode to show contrast between distinct tastes. | Transparency against popularity baselines; diversity in personalized retrieval ([`docs/RESULTS.md`](RESULTS.md)). |
| **02:45 - 03:45** | **Cold Start Live Moment** (`/?tab=cold-start`) | Navigate to Cold Start tab. Point out initial empty state defaulting gracefully to popularity fallback. Type "matrix" in search box, click "Add The Matrix" and a Sci-Fi companion. Watch recommendation mode dynamically flip from popularity fallback to personalized retrieval in real time. | Dynamic affinity vector generation on CPU without database sessions or retraining (`backend/engine/models/sar.py`, `frontend/components/tabs/ColdStartTab.tsx`). |
| **03:45 - 04:30** | **Products & Articles Adaptation** (`/?type=products`, `/?type=articles`) | Switch content type to Products: observe adaptively styled e-commerce cards (brand, pricing, platform tags). Switch to Articles: observe 24h freshness decay window and text-driven TF-IDF content recommendations. | Domain adaptation: identical engine abstractions ingest rating matrices, purchase baskets, and raw text streams without core modifications ([`docs/ARCHITECTURE.md`](ARCHITECTURE.md), `tools/core_unchanged.py`). |
| **04:30 - 05:15** | **Evaluation Tab** (`/?tab=evaluation`) | Open Evaluation tab. Walk through offline benchmarks, cold-start degradation curves, catalog coverage, and Shannon entropy diversity. Highlight the honest confidence interval overlap on MovieLens NDCG@10 and dual-protocol news evaluation. | Honest, reproducible evaluation; 95% bootstrap confidence intervals; no inflated marketing claims ([`docs/RESULTS.md`](RESULTS.md), `docs/gate_matrix.json`). |
| **05:15 - 06:15** | **Discovery Assistant** (Chat Panel) | Click "Ask AI" in header. Walk through natural-language queries across 3 verticals: (1) Movies: *"Recommend a good mind-bending sci-fi movie"* (click "View Item" to open ItemDrawer); (2) Products: *"Best multiplayer racing game for family game night"*; (3) Articles: *"Latest developments in artificial intelligence and robotics"*. Demonstrate forced fallback: simulate rate limit or disabled keys; observe "Answered by recommendation engine" fallback badge with top engine candidates. | LLM concierge over engine candidates; zero hallucinated items; client secret isolation; health-aware QuotaManager and graceful engine fallback (`backend/engine/llm/`, Decision D-036). |
| **06:15 - 06:45** | **System Conformance & Wrap-up** | Conclude demonstration. Reiterate sub-150ms CPU serving latency, zero GPU dependencies, and 11 Conformance Gates. Offer to dive into architectural records or offline metrics. | Production engineering rigor and architectural boundary integrity ([`docs/CONFORMANCE.md`](CONFORMANCE.md)). |

---

## 4. Evaluator FAQ & Grounded Answers

Every answer below is grounded in repository artifacts, code, or formal decision records:

| Question | Grounded Answer | Source Evidence |
|---|---|---|
| **Why use SAR for movies and products?** | Simple Algorithm for Recommendation (SAR) computes item co-occurrence matrices with time decay. It offers fast, deterministic CPU training and sub-millisecond inference without GPU infrastructure, while generating clear explanation badges ("Because you liked X"). | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), `backend/engine/models/sar.py`, Decision D-001 |
| **Why use TF-IDF for news articles?** | News recommendation faces extreme cold start: hundreds of newly published articles arrive daily with zero historical clicks. Pure collaborative filtering fails on unseen items. TF-IDF extracts unigram/bigram token vectors directly from article text and applies an exponential 24h temporal decay window to prioritize freshness. | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), `backend/engine/models/tfidf.py`, Decision D-002, Decision D-025 |
| **How does cold start work in real time?** | When a user has zero interactions, the engine serves frequency-ranked Popularity items (`mode="popularity"`). When items are selected in the Cold Start tab, the frontend POSTs their IDs and weights to `/v1/recommend/cold-start`. The engine treats this list as a temporary user vector, multiplies it against the item-to-item similarity matrix on the fly, and returns personalized recommendations (`mode="personalized"`) without saving to a database. | `backend/engine/models/sar.py`, `backend/api/routes/recommend.py`, `frontend/components/tabs/ColdStartTab.tsx` |
| **What is original versus derived code?** | The repository contains 90.0% original implementation and 10.0% derived reference code. The derived portion (`backend/discovery/`) consists of trimmed Microsoft Recommenders modules (SAR single-node, data splitters, metrics). All domain adapters, FastAPI serving endpoints, Next.js UI, evaluation harnesses, and gate verification suites are completely original. | [`docs/ORIGINAL_VS_DERIVED.md`](ORIGINAL_VS_DERIVED.md), [`docs/ATTRIBUTION.md`](ATTRIBUTION.md), [`docs/VENDORED_FILES.md`](VENDORED_FILES.md) |
| **How was data leakage prevented?** | Splitters enforce strict chronological ordering: training sets contain events prior to a temporal cutoff, while test sets contain subsequent events. User-stratified holdouts ensure test users have historical training context. The pipeline includes an automated shuffled-label sanity check that randomly permutes interaction labels to verify test metrics collapse to near zero. | [`docs/DATASETS.md`](DATASETS.md), `backend/engine/adapters/`, Decision D-004, Decision D-015 |
| **What are the primary system limitations?** | (1) Absence of negative feedback: ratings below 4.0 stars are treated as non-interactions. (2) Single split with fixed seed: no cross-validation folds. (3) Catalog capping: product items are capped to an 8,000 budget to guarantee CPU memory bounds. (4) Offline vs. online gap: offline simulation cannot measure user delight or interactive browsing. | [`docs/DECISIONS.md`](DECISIONS.md) (D-011, D-018), [`docs/RESULTS.md`](RESULTS.md) |
| **Why is the Movies model not ahead of Popularity on every metric?** | On MovieLens 1M, blockbusters heavily dominate viewing habits. Bootstrap confidence intervals for SAR and Popularity overlap at NDCG@10 ([0.0763, 0.1118] vs [0.0764, 0.1086]). We report this overlap transparently rather than claiming artificial superiority. | [`docs/RESULTS.md`](RESULTS.md), `artifacts/movies/metrics.json`, Decision D-011 |
| **What does MIND-small mean for news results?** | MIND-small provides a 50,000-user sample across a 6-day window. We evaluate under two complementary protocols: (1) full-catalog ranking across all published articles, and (2) impression reranking over the specific candidate slate presented to the user. | [`docs/RESULTS.md`](RESULTS.md), `artifacts/articles/metrics.json`, Decision D-025 |
| **Why does the API avoid deep-learning frameworks?** | Heavy deep-learning frameworks (PyTorch, TensorFlow) introduce multi-gigabyte container footprints, cold-start import delays, and GPU hosting overhead. SAR and TF-IDF operate with pure NumPy/SciPy/Polars, achieving sub-150ms latency on commodity CPU instances. | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), `backend/pyproject.toml` |
| **How does adding a new content type work?** | Adding a domain requires implementing a `DatasetAdapter` subclass, writing a declarative configuration YAML, and annotating the class with `@registry.register_adapter("new_type")`. The core engine and FastAPI routers dynamically discover and serve the new type without core engine modifications. | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), `backend/engine/adapters/base.py`, `tools/core_unchanged.py` |
| **Is any Large Language Model (LLM) involved?** | No LLMs are used for candidate generation or scoring. Recommendations are produced entirely by deterministic ML algorithms: item co-occurrence graphs (SAR) and token cosine similarity (TF-IDF). The optional Discovery Assistant chatbot acts strictly as an LLM concierge over engine-provided candidates: it translates user queries, selects from engine candidates, and provides plain-text explanations. 100% of candidate attributes, categories, and ranks displayed on cards are grounded in catalog lookups, and under rate limits or errors it instantly falls back to pure engine recommendations. | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), `backend/engine/llm/`, Decision D-036 |

---

## 5. Live Failure Plan & Graceful Degradation

If unexpected issues arise during a live evaluation:

1. **Port Conflict or Zombie Process:**
   - Run `python tools/demo.py --stop --force` and restart with `python tools/demo.py`.
2. **Missing Remote Poster Images:**
   - Explain that the UI shell is designed with graceful degradation: when external image CDN requests fail or network is disabled, adaptive SVG placeholder cards render seamlessly with zero broken layouts.
3. **Severe Local Machine Hang:**
   - Switch smoothly to the pre-captured, verified screenshot assets located in `docs/screenshots/` (covering all three content domains, drawer dialogs, evaluation views, and mobile viewports) or the recorded screen capture.
4. **Presentation Discipline (What NOT to Claim):**
   - Never claim the model surpasses Popularity on MovieLens without explicitly citing the overlapping confidence intervals.
   - Never claim offline metrics predict online real-world conversion rates.
   - Never claim deep-learning or LLM capabilities where simple, robust statistical algorithms are serving recommendations.
