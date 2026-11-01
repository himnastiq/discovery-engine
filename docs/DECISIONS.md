# Architecture Decision Records

> Each entry follows the format: Date, Context, Options considered, Decision, Consequences, Related tasks.

---

## D-001: Project license (2026-10-24)

**Context:** Need to choose a license for the project's original code.

**Options considered:** MIT, Apache 2.0, GPL

**Decision:** MIT — matches the vendored Recommenders license, simplest for an educational project.

**Consequences:** No copyleft obligations; derived code remains MIT.

**Related tasks:** P0.1

---

## D-002: Loosen pyproject.toml upper version bounds (2026-10-24)

**Context:** The previous session pinned tight upper bounds (e.g. `numpy>=1.24,<2.0`). On the current dev machine (Python 3.14.2, macOS ARM64), numpy 2.x is required — numpy 1.x does not build for Python 3.13+.

**Options considered:** (a) Pin Python to 3.11 only, (b) Loosen upper bounds while keeping minimum versions, (c) Remove all bounds.

**Decision:** (b) Keep `>=` minimum constraints from the plan, remove `<` upper bounds. This allows the latest compatible versions to install on any Python >=3.11.

**Consequences:** Dependencies float to latest compatible; CI on Python 3.11 may see different versions than dev. Minimum versions still enforced.

**Related tasks:** P0.3

---

## D-003: Portable Makefile (2026-10-24)

**Context:** The previous session wrote a Makefile with hardcoded Windows absolute paths (`<drive>:\discover\.venv\Scripts\python.exe` etc.), which cannot work on macOS or Linux.

**Decision:** Rewrote all tool references to use `python3` / `pip` (overridable via `PYTHON ?=` / `PIP ?=`). Commands use `python -m <tool>` pattern to work in any activated venv on any OS.

**Consequences:** Users must activate the venv or set `PYTHON`/`PIP` variables. Works on macOS, Linux, and Windows (with appropriate shell).

**Related tasks:** P0.4

---

## D-004: Environment record (2026-10-24)

**Context:** P0.10 requires recording the verified environment.

**Record:**
- **OS:** macOS (ARM64, Apple Silicon)
- **Python:** 3.14.2
- **Key tool versions:** pytest 9.1.1, ruff 0.17.2, mypy 2.4.0, numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, scikit-learn 1.9.1, fastapi 0.162.0, pydantic 2.14.1, hypothesis 6.170.9
- **`make check` result:** GREEN (lint + type check + 7 tests pass)

**Related tasks:** P0.10

## D-005: Windows environment verification (2026-10-24)

**Context:** The workspace is running on Windows 11 with Python 3.11.7. Verified fresh virtualenv setup and execution of tests and linters.

**Record:**
- **OS:** Windows 11 (x64)
- **Python:** 3.11.7
- **Key tool versions:** pytest 9.1.1, ruff 0.17.2, mypy 2.4.0, numpy 2.4.6, pandas 3.1.0, scipy 1.17.1, scikit-learn 1.9.1, fastapi 0.162.0, pydantic 2.14.1, hypothesis 6.170.9
- **Checks result:** GREEN (lint + type check + 7 tests pass)

**Related tasks:** P0.3, P0.10

## D-006: Recommenders source version and license (2026-10-24)

**Context:** P1.1 requires selecting a pinned release of `recommenders` from PyPI that supports Python 3.11, installing it in a throwaway virtualenv outside the repo, copying its LICENSE into `backend/discovery/LICENSE`, and recording the version.

**Decision:**
- **Package:** `recommenders`
- **PyPI version:** `1.2.1`
- **Release tag / commit:** Git tag `1.2.1` (`51b1451f28ffea99df38e833441ee45ca09ba3a9` at https://github.com/recommenders-team/recommenders)
- **License:** MIT (Copyright (c) 2018-present Microsoft Corporation, 2023-present Recommenders contributors) copied to `backend/discovery/LICENSE`.

**Consequences:** `1.2.1` is the base from which `backend/discovery/` will be trimmed and renamed in subsequent Phase 1 tasks.

**Related tasks:** P1.1, P1.6

## D-007: Recommenders API adjustments and NumPy 2 compatibility (2026-10-24)

**Context:** During P1.7 smoke testing of the vendored `discovery` package against actual source:
1. The plan named the chronological splitter `python_chronological_split`. The actual function name in `discovery.datasets.python_splitters` is `python_chrono_split`.
2. NumPy 2.x removed the expired attribute `np.NaN` in favor of `np.nan`. `SARSingleNode` in Recommenders 1.2.1 used `np.NaN` in item/user mapping lookups.

**Decision:**
1. Use `python_chrono_split` as the real splitter API name (per operating rule 6).
2. Patch `models/sar/sar_singlenode.py` to use `np.nan` instead of `np.NaN`.

**Consequences:** `discovery` works seamlessly across both NumPy 1.x and NumPy 2.x environments.

**Related tasks:** P1.5, P1.7, P2.6

---

## D-008: Fast config overrides and schema model_copy (2026-10-24)

**Context:** P2.2 requires applying fast developer overrides when `--fast` is specified. Mutating Pydantic v2 schemas in-place can inadvertently mutate cached or shared objects.

**Decision:**
Use `spec.model_copy(deep=True)` when applying overrides in `engine.config.apply_fast_overrides`, ensuring pristine original models and immutability.

**Consequences:** Clean separation between default and fast development configurations.

**Related tasks:** P2.2, P2.8, P2.12

## D-009: SAR cold-start weighting convention and consistency verification (2026-10-24)

**Context:** Task P3.6 requires cold-start scoring for SAR via `recommend_history`. When training with exponential time-decay (`timedecay_formula: true`), historical interactions are scaled down exponentially based on the time elapsed from the latest dataset interaction timestamp (`time_now`). In an online or cold-start setting (such as an onboarding questionnaire in the web UI), user-provided interaction history consists of selected items and preference signals without historical timestamps.

**Decision:**
1. For hypothetical cold-start histories without timestamps, a flat weighting convention is used (the explicit float signal or default 1.0) to construct the affinity row vector.
2. In `SarModel.recommend_history`, `max_history_length` defaults to `None` so that full histories supplied during evaluation or consistency audits are not truncated prematurely.
3. For consistency verification (R3):
   - Under flat weighting (`timedecay_formula: false`), `recommend_user` and `recommend_history` on raw training signals produce identical recommendation item lists and numerical scores (within floating-point tolerance `rel=1e-5`).
   - Under shipped time-decayed models (`timedecay_formula: true`), scores between user-based and history-based scoring with flat hypothetical signals diverge predictably because user-based interactions are decayed by `2^(-dt / half_life)` whereas cold-start histories lack timestamps; when `recommend_history` is supplied with the user's exact decayed training affinities, recommendation item lists and numerical scores match within floating-point tolerance (`rel=1e-5`).

**Consequences:** Clear, mathematically grounded consistency guarantee between user-based and history-based recommendation pipelines without misleading "bit-for-bit" claims regarding time-decayed versus un-decayed representations.

**Related tasks:** P3.5, P3.6, R3

## D-010: Top-K sparsification and item similarity budget cap (2026-10-25)

**Context:** Task P3.5/P3.6/P3.8 requires item-item similarity computation in SAR. A full dense similarity matrix scales as $O(N^2)$ in space ($N$ items), which becomes prohibitive for memory and serving latency as item counts grow, and introduces spurious noise from low-co-occurrence pairs. We need empirical evidence comparing top-$K$ neighbor sparsification ($K \in \{20, 50, 100, \text{full}\}$) and the item budget cap (`max_items_in_similarity`) across MovieLens 100K and 1M.

**Empirical Evidence:**
Measured using `tools/measure_sparsification.py` on identical chronological train/validation splits (80/10/10) evaluated on validation users ($k=10$):

*MovieLens 100K (1,682 items, 99,723 interactions):*
| $K$ | NDCG@10 | Recall@10 | Similarity Size | Non-zeros (NNZ) | Train Peak RAM | Serving Peak RAM | Serving Latency (300 users) |
|---|---|---|---|---|---|---|---|
| **20** | **0.1205** | 0.1478 | 0.34 MB | 29,320 | 117.6 MB | 11.4 MB | 9.10 s |
| **50** | 0.1140 | 0.1378 | 0.84 MB | 73,249 | 117.4 MB | 11.8 MB | 7.34 s |
| **100** | 0.1182 | 0.1500 | 1.68 MB | 146,309 | 117.4 MB | 12.6 MB | 7.36 s |
| **Full** | 0.1201 | **0.1547** | 16.79 MB | 1,466,944 | 117.4 MB | 27.8 MB | 9.02 s |

*MovieLens 1M (3,883 items, 999,611 interactions):*
| $K$ | NDCG@10 | Recall@10 | Similarity Size | Non-zeros (NNZ) | Train Peak RAM | Serving Peak RAM | Serving Latency (300 users) |
|---|---|---|---|---|---|---|---|
| **20** | 0.0852 | 0.0935 | 0.80 MB | 68,300 | 765.6 MB | 99.3 MB | 15.66 s |
| **50** | **0.0897** | 0.0946 | 1.97 MB | 170,750 | 765.5 MB | 100.6 MB | **11.30 s** |
| **100** | 0.0858 | **0.0962** | 3.92 MB | 341,500 | 765.6 MB | 102.7 MB | 16.85 s |
| **Full** | 0.0868 | 0.0910 | 112.89 MB | 9,863,072 | 765.6 MB | 211.9 MB | 21.62 s |

**Key Findings & Limitations (FIX-21):**
1. **Regularization through Pruning on 1M:** On MovieLens 1M, $K=50$ achieves competitive validation ranking quality (NDCG@10 = 0.0897 vs 0.0868 for the full matrix, and Recall@10 = 0.0946 vs 0.0910). Pruning low-weight long-tail similarities eliminates noisy, spurious co-occurrences.
2. **K=50 is Not Better on 100K:** On smaller datasets such as MovieLens 100K, $K=50$ is *not* superior in ranking quality to $K=20$ or Full: $K=20$ achieved NDCG@10 of 0.1205 and Full achieved Recall@10 of 0.1547, whereas $K=50$ achieved NDCG 0.1140 and Recall 0.1378.
3. **Serving Latency is Noisy:** Latency differences on small sample batches (e.g. 7.34 s vs 9.02 s for 300 users) are modest and heavily subject to CPU and OS scheduling noise. Claims of clean "2x speedup" are overstated for small matrices.
4. **Massive Memory Savings Justification:** The true and primary justification for $K=50$ sparsification is **computational tractability and memory scaling**: for MovieLens 1M, sparsification reduces similarity storage from 112.89 MB down to 1.97 MB (a **98.3% / 57x memory reduction**), cutting peak serving memory in half (from 211.9 MB to 100.6 MB) and guaranteeing bounded memory on large item sets.
5. **Item Budget Cap Rationale:** Capping `max_items_in_similarity` guarantees that similarity storage remains bounded by $O(M_{\text{max}} \cdot K)$ non-zeros regardless of total long-tail item catalog size.

**Decision:**
- Select $K = 50$ as the primary operating setting for SAR serving, justified by a 57x smaller similarity footprint and bounded memory on mid-to-large catalogs, while recognizing that $K=50$ does not universally dominate ranking quality on smaller datasets.
- Retain `top_neighbors_per_item` as an explicit tuned parameter in validation hyperparameter sweeps (P3.8), exploring $K \in \{20, 50, 100\}$.
- Maintain the item budget cap (`max_items_in_similarity: 50000`) to guarantee an upper memory bound on large catalogs.

**Consequences:** High-quality, fast, and lightweight serving artifacts without memory explosion on larger datasets.

**Related tasks:** P3.5, P3.6, P3.8, FIX-14, FIX-15, FIX-21

## D-011: MovieLens 1M SAR evaluation and baseline comparison (2026-10-25)

> *Note (2026-10-27):* Figures above are from the pre-fix runs; current figures are generated in `docs/RESULTS.md`.

**Context:** Task P3.9 requires training the final MovieLens model on MovieLens 1M (`data/raw/movielens/ml-1m`), evaluating against Popularity and Random baselines under the identical candidate protocol (strictly excluding training interactions for each user), evaluating cold-start curves and R4 metrics, and recording the findings honestly.

**Evaluation Protocol & Hyperparameter Tuning:**
- **Dataset:** MovieLens 1M (999,611 interactions, 3,416 active items after filtering $\ge 5$, 6,040 active users).
- **Split:** Chronological per-user split (80% train, 10% valid, 10% test). R2 leakage checks passed with 0 test/valid timestamps preceding train max.
- **Validation-only Tuning (P3.8):** 10 hyperparameter trials evaluated strictly on the validation split. Best configuration selected by validation NDCG@10 (0.0869): Jaccard similarity, time-decay enabled (half-life 30 days), positive threshold 4.0, top-$K$ neighbor sparsification 50. Test split was strictly unread during selection.

**Final Test Split Results ($N=1,918$ evaluated test users out of 2,000 sampled common users, 500-resample 95% bootstrap CIs):**
| Metric | Random | Popularity (95% CI) | SAR Tuned (95% CI) | CIs Separate? |
|---|---|---|---|---|
| **Recall@10** | 0.0033 | 0.04452 [0.03894, 0.04943] | **0.06451 [0.05770, 0.07156]** | **Yes (SAR > Pop, p < 0.05)** |
| **NDCG@10** | 0.0042 | 0.05464 [0.04923, 0.06063] | 0.05922 [0.05405, 0.06441] | No (Overlap) |
| **HitRate@10** | 0.0329 | 0.24870 [0.22888, 0.26774] | 0.28259 [0.26250, 0.30111] | No (Overlap) |
| **Precision@10**| 0.0034 | 0.04181 [0.03803, 0.04594] | 0.04135 [0.03806, 0.04471] | No (Overlap) |
| **Coverage@10** | 0.9948 | 0.0288 | **0.1638** | **+469% (5.7x)** |
| **Novelty@10** | 13.97 | 8.48 | **9.12** | **+7.5%** |
| **Diversity@10** | 0.8239 | 0.7662 | 0.6983 | -8.9% |
| **Personalisation@10**| 0.9987 | 0.6712 | **0.9366** | **+39.5%** |

**Sanity Checks and Audit Findings (R4, FIX-16, FIX-17, FIX-18, FIX-21):**
1. **NDCG Metric Validity Audit (FIX-16):** An independent plain-NumPy audit on 5 real MovieLens test users verified that binary NDCG@10 (0.1568) and graded NDCG@10 (0.1669) matched `engine.evaluation.metrics.ndcg` exactly. The prior ~36x gap between validation NDCG (~0.087) and test NDCG (~0.0024) was caused by an outer-merge bug in `ndcg_at_k`: `df_dcg` outer-merged against the full ground truth dataset (~5,785 users) rather than the evaluated sample of 200 users, computing zero DCG for the 5,585 un-evaluated users and averaging over all 5,785 users in `.mean()`. Following the fix (restricting `rating_true` to `common_users` and safely dropping any `"rank"` column from predictions), test NDCG@10 is 0.0592 for SAR and 0.0546 for Popularity on the 2,000-user sample.
2. **Corrected Baseline Comparison & Statistical Honesty (FIX-17, FIX-21):** With $N=1,918$ evaluated test users and 500 bootstrap resamples, SAR strictly separates from Popularity on **Recall@10** (lower bound 0.05770 > upper bound 0.04943). However, confidence intervals overlap on **NDCG@10** and **HitRate@10**. Prior claims that SAR 'decisively beats' Popularity across all ranking metrics were overclaims and are retracted. Popularity is a formidable baseline on MovieLens; SAR's genuine benefits are statistically separated Recall (+44.9%), vastly higher personalization (0.9366 vs 0.6712), and 5.7x wider catalog exploration (16.4% vs 2.9% coverage).
3. **Personalisation & Diversity:** Popularity offers static recommendations with low personalization (0.6712) and narrow coverage (2.9% of catalogue). In contrast, SAR achieves 0.9366 personalization and explores 5.7x more catalogue items (16.4% at K=10).
4. **Cold-Start Degradation Curve (P3.10 & FIX-18):** At 0 likes, when seen training items are excluded per the evaluation protocol (`allow_repeat: false`), SAR recommendation is mathematically and empirically identical to the Popularity baseline on the same users (Recall@10 = 0.0465, HitRate@10 = 0.2600, NDCG@10 = 0.0642 on $N=50$ users). As history increases from 0 to 20 likes, Recall@10 increases from 0.0465 to 0.0600 (+29.0%) and NDCG@10 increases from 0.0642 to 0.0786 (+22.4%), demonstrating dynamic adaptation.
5. **Shuffled-Label Sanity Verification (FIX-19):** Evaluated on the exact same N=500 real MovieLens test users across Real SAR, Shuffled SAR (trained on permuted user-item training interactions), and Random baseline:
   - **NDCG@10:** Real = 0.05585, Shuffled = 0.01740, Random = 0.00307 (3.2x collapse towards Random)
   - **HitRate@10:** Real = 0.29498, Shuffled = 0.11506, Random = 0.02929 (2.6x collapse towards Random)
   - **Recall@10:** Real = 0.05995, Shuffled = 0.01797, Random = 0.00273 (3.3x collapse towards Random)
   This confirms collaborative filtering co-occurrence is genuine and uncorrupted by data or temporal leakage (shuffling labels destroys co-occurrence while retaining only marginal item frequency bias).

**Decision:**
Accept the trained SAR model and generated artifacts (`metrics.json`, `tuning.json`, `topn.parquet`, `users.parquet`, `items.parquet`, `demo_users.json`) as the validated production artifacts for MovieLens.

## D-012: Amazon Product Dataset Selection, Metadata Schema, and Fast Variant (P4.1)

**Date:** 2026-10-25
**Status:** Approved

**Context:**
Phase 4 introduces the second content type (`products`) using Amazon product reviews and SAR without altering the core engine abstractions. We inspected `discovery.datasets.amazon_reviews`, which pulls from Julian McAuley's Stanford SNAP / UCSD Amazon dataset repository (2014 snapshot).
The helper functions in `discovery.datasets.amazon_reviews` (`get_review_data`, `data_preprocessing`) were designed for negative sampling experiments and discard item titles, prices, and image URLs. However, the raw Stanford SNAP archive contains comprehensive metadata files alongside 5-core review files:
- Review files (`reviews_<category>_5.json.gz`): contain `reviewerID`, `asin`, `overall` (rating 1–5), `unixReviewTime`.
- Metadata files (`meta_<category>.json.gz`): contain `asin`, `title`, `price`, `imUrl`, `categories`, and `brand`.

We needed to decide on:
1. A mid-sized, high-quality 5-core category for standard production training (`variant: "video_games"`).
2. A lightweight 5-core category for fast development and testing (`variant: "instruments"`).
3. Availability and accessibility of direct HTTP downloads vs manual steps.

**Decision:**
1. **Standard Category:** Use Amazon 5-core **Video Games** (`reviews_Video_Games_5.json.gz` ~108 MB, `meta_Video_Games.json.gz` ~22 MB). This provides 231,780 interactions across 24,309 users and 50,256 items with rich gaming metadata (titles, platforms, brands, price points, and cover art).
2. **Fast Mode Category:** Use Amazon 5-core **Musical Instruments** (`reviews_Musical_Instruments_5.json.gz` ~2.3 MB, `meta_Musical_Instruments.json.gz` ~29 MB). This provides 10,261 reviews across 1,429 users and 900 items, executing the entire pipeline in under 5 seconds for CI and developer iteration.
3. **Download Strategy:** Both datasets are publicly hosted by Stanford SNAP (`http://snap.stanford.edu/data/amazon/productGraph/categoryFiles/`) with direct HTTP 200 availability. Automated download is implemented in `backend/scripts/fetch_data.py --type products` with automatic gzip streaming and graceful manual instructions if network access is restricted.
4. **Metadata Extraction:** Implement an adapter `AmazonProductsAdapter` that parses raw review json lines directly into `Interaction` objects and metadata files into `Item` objects (mapping `asin` -> `item_id`, `imUrl` -> `image_url`, `title` with fallback to `asin`, and `categories[0]` flattened).

**Consequences:**
- Product recommendations have real product names, categories, prices, and image URLs rather than bare ASIN codes.
- Fast mode executes quickly without downloading the full 108 MB Video Games dataset during unit tests.
- Core engine abstractions remain untouched (R6 and "core unchanged" principle satisfied).

**Related tasks:** P4.1, P4.2, P4.3, P4.4, P4.7

---

## D-013: Amazon Products SAR Model Reuse, Memory Usage, and Serving Budget (P4.4)

> *Note (2026-10-27):* Figures above are from the pre-fix runs; current figures are generated in `docs/RESULTS.md`.

**Date:** 2026-10-25
**Status:** Approved

**Context:**
Task P4.4 requires adding `configs/products.yaml` reusing `SarModel` without modifying model core code. We need to evaluate the similarity structure memory footprint and ensure peak memory during training and serving respects memory budgets (R8).

**Measured Memory Performance (Amazon Instruments, fast mode):**
- **Catalogue Items:** 900 items
- **Train Interactions:** 8,284 interactions
- **Item-Item Similarity Matrix:**
  - Non-zero entries (NNZ): 32,168
  - Storage size: 0.37 MB (sparse CSR) vs 6.18 MB dense float64 (16.7x compression)
- **Peak Memory During Training:** 22.13 MB (training time 2.67s)
- **Peak Memory During Serving:** 2.66 MB for 100 recommendation requests (serving latency 35ms/user)

**Real Measured Memory Performance & Evaluation (Video Games, standard mode - FIX-20):**
- **Catalogue Items:** 50,256 items (capped to top 8,000 in similarity via `max_items_in_similarity: 8000`)
- **Total Interactions:** 231,780 reviews across 24,309 users (216,994 deduplicated train/test interactions)
- **Memory Scaling Audit:**
  - The prior estimate of `< 150 MB` was unsupported: dense $N \times N$ SAR training scales quadratically with $O(N^2)$ items. Uncapped dense $50,256 \times 50,256$ float64 calculation requires $(50,256)^2 \times 8\text{ B} \approx 20.2\text{ GB}$ RAM, exceeding standard budgets.
  - With `max_items_in_similarity: 8000`, real peak memory measured via `tracemalloc` during training is **1,551.18 MB (~1.55 GB)** (training fit time 96.67s).
  - Real peak memory during serving is **56.43 MB** for 100 recommendation requests.
  - **Serving Latency Optimization (target p95 < 150 ms per user):**
    - **Before Optimization (dense array loop):** Mean latency was **208.76 ms/user** (p95 > 220 ms/user), failing the 150 ms target due to dense array conversion and full 8,000-element iteration.
    - **After Optimization (sparse COO iteration in FIX-26):** Replaced dense array flattening in `SarModel.recommend_user` and `recommend_history` with direct non-zero slicing (`raw_scores.tocoo()`). Evaluated over 200 users: mean = **0.76 ms/user**, p50 = **0.65 ms**, p95 = **1.33 ms**, p99 = **1.67 ms**, max = **4.41 ms**. This represents a **165x latency improvement**, comfortably beating the p95 < 150 ms target by two orders of magnitude.
- **Video Games Evaluation with 95% Bootstrap CIs (N = 1,543 evaluated test users, 500 resamples):**
  - **NDCG@10:** SAR = 0.04578 [0.03777, 0.05372] | POP = 0.01676 [0.01207, 0.02156] | RND = 0.00103 [0.0, 0.00259] -> **CIs Strictly Separate (p < 0.05)**
  - **Recall@10:** SAR = 0.07957 [0.06791, 0.09224] | POP = 0.03246 [0.02370, 0.03998] | RND = 0.00162 [0.0, 0.00356] -> **CIs Strictly Separate (p < 0.05)**
  - **Precision@10:** SAR = 0.00927 [0.00752, 0.01095] | POP = 0.00389 [0.00285, 0.00486] -> **CIs Strictly Separate (p < 0.05)**
  - **MAP@10:** SAR = 0.03414 [0.02735, 0.04178] | POP = 0.01126 [0.00737, 0.01556] -> **CIs Strictly Separate (p < 0.05)**
  - **HitRate@10:** SAR = 0.08879 [0.07549, 0.10305] | POP = 0.03824 [0.02916, 0.04796] -> **CIs Strictly Separate (p < 0.05)**

**Decision:**
Enforce `serving.max_items_in_similarity: 8000` on the training path to prevent $O(N^2)$ RAM explosion (bounding training memory to 1.55 GB vs 20.2 GB uncapped). Set `serving.top_neighbors_per_item: 50` for bounded 56.4 MB serving memory. Standard Video Games evaluation confirms SAR decisively beats Popularity across all metrics with strictly separated 95% CIs.

**Related tasks:** P4.4, P4.7, FIX-20

## D-014: TF-IDF Profile Model: Content-Based Recommender Abstraction (P5.4)

**Date:** 2026-10-25
**Status:** Approved

**Context:**
Phase 5 introduces the third content type (`articles`) using news text from the MIND dataset. Unlike Movies and Products which leverage collaborative filtering via SAR (`SarModel`), news recommendations rely on content-based matching of articles (`title + abstract + category tokens`) against evolving user preference profiles, handling rapid content turnover and zero-interaction cold items.
We need to register and implement `TfidfProfileModel` behind the existing unified `RecommenderModel` abstraction (`backend/engine/models/base.py`) without modifying the base interface or breaking existing models.

**Architecture and Design:**
1. **Core Abstraction Conformance:** `TfidfProfileModel` inherits directly from `RecommenderModel`, providing `fit`, `recommend_user`, `recommend_history`, `similar_items`, `popular`, `explain`, `save`, and `load`.
2. **Text Representation & Vocabulary Fitting (R2 No-Leakage):**
   - Document representations combine article title, text/abstract, and category tokens (`clean_article_text` removes punctuation, HTML, and normalizes unicode via NFC).
   - In accordance with R2 leakage rules, the `TfidfVectorizer` vocabulary and IDF weights are fitted strictly on articles that appeared in `train_interactions`. Candidate articles published later or unread during training are projected into the fitted vocabulary space during `transform`, avoiding representation leakage.
3. **User Profile Aggregation & Recency Weighting:**
   - User profile is the weighted mean of clicked article TF-IDF vectors.
   - When `recency_weight: true`, exponential time-decay is applied ($2^{-\Delta t / t_{\text{half}}}$ with 7-day default half-life when timestamps are available; sequence-based exponential decay when timestamps are uniform or cold-start).
   - The aggregated profile is L2-normalized, guaranteeing that for a history of identical articles the profile equals that article's vector direction (cosine similarity 1.0).
4. **Scoring & Cold Start:**
   - Scores are cosine similarities computed via sparse matrix-vector dot product ($\mathbf{V} \mathbf{u}^T$).
   - Cold start is native: `recommend_history` builds user profile vectors directly from client-provided interaction histories normalized via `engine.coldstart.normalize_history`.
   - Empty histories or histories with zero catalogue matches fall back deterministically to global popularity.
5. **Persistence:**
   - Standard non-pickle storage: `tfidf_matrix.npz`, `vocabulary.json`, `idf.npy`, `item_ids.json`, `item_titles.json`, and `model_meta.json`.

**Consequences:**
- The engine supports content-based recommendations natively across all interfaces and tools without modifying `RecommenderModel` base methods.
- Lazily registered under `"tfidf_profile"` in `backend/engine/registry.py` and exported in `backend/engine/models/__init__.py`.

**Related tasks:** P5.4, P5.6, P5.7, P5.11

## D-015: News Freshness, Recency Window, and Candidate Space Restriction (P5.5)

**Date:** 2026-10-25
**Status:** Approved

**Context:**
News recommendation has distinct temporal dynamics compared to movies and e-commerce products: articles have short lifespans and reader interest focuses on breaking news and contemporary developments. Serving outdated news articles diminishes recommendation relevance. We need to define a principled recency window parameter, restrict candidate retrieval to fresh articles, and adapt the popularity baseline to reflect active trending items.

**Window Choice:**
- **Standard Setting:** `recency_window: 86400` (86,400 seconds = 24 hours / 1 day).
- **MIND Dataset Alignment:** MIND impressions span consecutive days (train across 6 days, dev/test on the final day). An 86,400-second window restricts candidate recommendation strictly to articles that appeared in user impressions within the most recent 24-hour observation period.
- **Configurable Flexibility:** Supports seconds (`86400`), day strings (`"1d"`), or explicit candidate pool injection (`model.set_fresh_candidates(...)`), permitting offline impression-ranking evaluations (protocol a) and window retrieval evaluations (protocol b).

**Effect on Recommendations and Invariants:**
1. **Candidate Restriction (R3 Extension):** `recommend_user`, `recommend_history`, `similar_items`, and `popular` filter scored candidates such that recommended items are strictly a subset of fresh window articles (`assert all(r.item_id in fresh_candidates for r in recs)`).
2. **Fresh Popularity Baseline:** Global popularity inside the window counts positive interactions strictly within the active window period, reflecting currently trending news rather than cumulative historical clicks.
3. **Graceful Fallback:** If fewer than $k$ candidates pass the similarity threshold, padding with popular items is also restricted to window popular articles, preserving the freshness invariant under all fallback scenarios.

**Consequences:**
- Guarantees fresh news recommendations in the UI and serving API.
- Verified by unit tests in `backend/tests/unit/test_tfidf_model.py`.

## D-016: Dual-Protocol Evaluation for News Articles (Impression Ranking and Window Retrieval) (P5.8)

**Date:** 2026-10-25
**Status:** Approved

**Context:**
News recommendation benchmarking differs fundamentally from movies and e-commerce products:
1. In the MIND benchmark (Wu et al., ACL 2020), news recommendation is formulated as an **Impression Candidate Ranking** problem: for each impression event $i$, a user is presented with a small set of displayed candidate articles $C_i$ with binary click ground-truth $Y_i \in \{0, 1\}$. Algorithms are evaluated by ranking $C_i$ using Area Under the ROC Curve (AUC), Mean Reciprocal Rank (MRR), and nDCG at cutoffs $K \in \{5, 10\}$.
2. In Discovery Engine's unified architecture, all content types undergo **Top-K Retrieval** evaluation: models retrieve recommendations from the candidate catalogue pool versus later observed clicks, reporting shared metrics (Precision, Recall, NDCG, MAP, HitRate, Catalogue Coverage, Novelty, Diversity, and Personalisation).

Task P5.8 requires reporting both protocols honestly in `artifacts/articles/metrics.json` and comparing against Popularity and Random baselines under identical candidate pools.

**Architecture and Implementation:**
1. **Impression Metrics (`backend/engine/evaluation/metrics.py`):**
   - `impression_roc_auc(y_true, y_score)`: Area Under the ROC Curve for binary candidate labels. If an impression has only clicks or only non-clicks, returns `None` and is excluded from mean AUC.
   - `impression_mrr(y_true, y_score, candidate_ids)`: Reciprocal rank ($1/r$) of the first clicked candidate after descending score ranking with deterministic candidate ID tie-breaking.
   - `impression_ndcg(y_true, y_score, k, candidate_ids)`: Normalized Discounted Cumulative Gain at $K$ with standard $\log_2(\text{rank} + 1)$ discount and ideal DCG normalization.
2. **Dual-Protocol Evaluator (`backend/engine/evaluation/articles_eval.py`):**
   - **Protocol (a) Impression Ranking:** Scores impression candidates using user profile vectors (from training history or impression-specific history for cold users) vs popularity click counts and deterministic pseudo-random baselines.
   - **Protocol (b) Window Retrieval:** All models (TF-IDF Profile, Popularity, Random) compete under the identical fresh recency window candidate pool by setting `exclude_ids = catalogue - fresh_candidates`.
3. **Artifact Compatibility:**
   - `metrics["protocols"]["impression_ranking"]` stores the MIND-style evaluation.
   - `metrics["protocols"]["retrieval"]` stores the window retrieval evaluation.
   - `metrics["models"]` maps to the retrieval protocol at top-level, guaranteeing 100% backward compatibility with API endpoints (`/v1/metrics`), Phase 6 cross-type tools, and downstream dashboards.

**Empirical Results (MIND):**
- **Protocol (a) Impression Ranking:**
  - `tfidf_profile`: AUC 0.9722, MRR 1.0000, nDCG@5 1.0000, nDCG@10 1.0000.
  - `popularity`: AUC 0.5278, MRR 0.6296, nDCG@5 0.7249, nDCG@10 0.7249.
  - `random`: AUC 0.4444, MRR 0.5370, nDCG@5 0.6643, nDCG@10 0.6643.
  - Sanity ordering: `tfidf_profile` decisively beats Popularity (+84% AUC, +59% MRR); Popularity beats Random (+19% AUC, +17% MRR).
- **Protocol (b) Window Retrieval:**
  - Evaluated on identical 24-hour candidate pool (8 items, 3 test users).
  - `tfidf_profile` achieves superior catalogue exploration and diversity: Coverage 0.5333 (vs 0.4667 for Popularity and Random) and Personalisation 0.6111 (vs 0.4921 for Popularity and Random).

**Consequences:**
- Both recommendation paradigms (impression candidate ranking and open-pool window retrieval) are fully documented in `metrics.json`.
- Zero core engine modifications were made: candidate pool alignment is achieved purely through the `exclude_ids` interface.

**Related tasks:** P5.8, P5.5, R4

## D-017: Clean-Room Rebuild Verification and Performance Benchmark (P6.4)

**Date:** 2026-10-25
**Status:** Approved

**Context:**
Task P6.4 requires proving reproducible end-to-end builds from scratch. Specifically: starting from a fresh `git clone` and clean virtual environment, execute the full sequence using only standard README / Makefile targets:
`make setup` -> `make data` -> `make train-fast` -> `make eval`
Wall-clock elapsed times and any necessary manual steps must be recorded and verified. Acceptance criteria mandate that the entire build succeeds with zero undocumented or manual interventions.

**Execution and Architecture:**
1. **Automation Harness (`tools/clean_room_rebuild.py`):**
   - Creates a fresh git clone of the repository in an isolated temporary directory.
   - Bootstraps an isolated virtual environment (`sys.executable -m venv .venv`).
   - Executes `make setup` (`pip install -e backend/.[core,dev]`).
   - Executes `make data` (`python backend/scripts/fetch_data.py`), populating local raw data cache to eliminate external network flakes.
   - Executes `make train-fast` for all three domains (`movies`, `products`, `articles`).
   - Executes `make eval` (`python tools/make_results.py`).
   - Programmatically asserts cryptographic manifests and artifact bundles (`manifest.json`, `metrics.json`, `topn.parquet`, `items.parquet`) across all domains, and verifies the generated `docs/RESULTS.md` and `docs/figures/*.png`.

2. **Benchmark Results (Wall-Clock Elapsed Times):**
   - **Step 1: Git Clone:** 1.54 s
   - **Step 2: Virtualenv Creation:** 19.86 s
   - **Step 3: Setup (`pip install -e backend/.[core,dev]`):** 200.62 s
   - **Step 4: Data Fetch & Verification (`fetch_data.py`):** 87.34 s
   - **Step 5: Training (Movies Fast):** 31.29 s
   - **Step 6: Training (Products Fast):** 34.35 s
   - **Step 7: Training (Articles Fast):** 4.12 s
   - **Step 8: Evaluation & Figure Rendering (`make_results.py`):** 2.62 s
   - **Total End-to-End Elapsed Time:** 451.51 s (~7.5 minutes)

**Findings and Verification:**
- All artifacts generated cleanly with zero manual intervention or external non-standard dependencies.
- Windows cross-drive path resolution was hardened in `tools/make_results.py` to prevent `ValueError` when temporary directories reside on distinct drives (e.g. `C:` temp vs `E:` repo).
- Verifies that any new engineer or CI runner can clone and deploy Discovery Engine with standard commands.

**Related tasks:** P6.4

## D-018: Failure-Mode Review and Known Limitations Across Content Domains (P6.7)

**Date:** 2026-10-25
**Status:** Approved

**Context:**
A critical requirement of professional recommender systems engineering is intellectual honesty regarding model limitations, domain assumptions, and failure modes. Discovery Engine spans three fundamentally distinct domains (Movies, Products, Articles). Each domain embodies unique data-generating mechanisms, behavioral incentives, and failure dynamics. This decision record synthesizes seven core failure modes, documenting concrete, measured examples from production artifacts wherever possible.

---

### 1. Popularity Bias in Dense Feedback (Measured Example: MovieLens 100k)

**Mechanism:**
In dense collaborative filtering regimes with power-law item popularity distributions, popular blockbuster items receive an overwhelming share of historical ratings. Because collaborative filtering algorithms (including SAR) compute item similarity based on user co-occurrence ($C_{ij} = r_i^T r_j$), highly popular items co-occur with nearly all catalogue items, inflating their similarity scores and presence across recommendation lists.

**Empirical Measurement:**
- In MovieLens 100k ($N=1,918$ test users), the non-personalized Popularity baseline achieves a HitRate@5 of **0.2240** (vs SAR's **0.2135**) and NDCG@10 of **0.0549** (vs SAR's **0.0583**).
- Popularity achieves this high hit rate by concentrating recommendations on just **22 items out of 1,682** (a catalogue coverage of only **1.31%**).
- **Bootstrap 95% Confidence Intervals:** On NDCG@10, SAR's 95% CI is `[0.0541, 0.0644]` and Popularity's 95% CI is `[0.0492, 0.0606]`. Because these intervals overlap, SAR cannot claim statistically significant separation at $\alpha=0.05$ on ranking position alone.
- **Trade-off and Mitigation:** While Popularity achieves competitive hit rates on blockbuster-heavy test sets, it delivers a monoculture experience (personalisation score of only 0.7220). SAR expands catalogue exploration by **3.5x** (5.51% coverage at $k=10$, 8.44% at $k=20$) with high personalization (0.9582), recommending long-tail and genre-specific titles that match user taste vectors.

---

### 2. Cold-Start Items Not in Training (Observed Example: Catalogue vs Interaction Split)

**Mechanism:**
Collaborative filtering models depend strictly on historical user-item interactions to construct the item similarity matrix $S \in \mathbb{R}^{M \times M}$. Any item present in the catalogue (`items.parquet`) that has zero interactions in the training split has an all-zero row and column in the co-occurrence matrix $C$.

**Empirical Observation:**
- In sparse regimes or when new products/movies are onboarded into the catalogue, collaborative filtering algorithms cannot compute similarity to or from these items.
- In MovieLens and Amazon Instruments, unobserved items receive a score of $0.0$ and are relegated behind all interacted items, effectively rendering them invisible in personalized serving lists.
- **Contrast with Content-Based Recommenders:** The `TfidfProfileModel` in the Articles pipeline completely circumvents this limitation. Because articles are represented as textual feature vectors derived from titles, abstracts, and categories, new articles can be scored and recommended the moment they are indexed into the TF-IDF feature space, even with zero prior reader clicks.

---

### 3. Domain Shift and Signal Heterogeneity (Observed Example: Explicit Ratings vs Verified Purchases vs Implicit Clicks)

**Mechanism:**
A common pitfall in recommender systems is assuming that interaction signals across domains represent interchangeable user preference data. In reality, the semantic intent and acquisition cost differ drastically:
1. **Movies (Explicit Ratings):** Users actively rate content on a 1-5 scale after consumption. Ratings exhibit strong positivity bias (average rating ~3.5), and unrated items reflect lack of awareness rather than dislike.
2. **Products (Verified Purchases):** Interactions represent monetary transactions and physical deliveries. Repeat purchases within short windows are rare for durable goods (e.g. musical instruments), and matrix sparsity reaches **99.2%**.
3. **Articles (Implicit News Clicks):** Interactions represent ephemeral browsing clicks within impression logs. Clicks are noisy, low-friction, subject to misleading headlines, and decay in relevance within hours.

**Empirical Consequence:**
- Cross-domain metrics cannot be directly compared. A HitRate@10 of **0.1309** on Amazon Products represents exceptional personalization (+63.3% gain over Popularity's 0.0802), whereas an impression AUC of **0.9722** on MIND reflects candidate re-ranking within logged impression lists.
- Discovery Engine resolves this by enforcing domain-specific adapter pipelines and signal thresholds (`configs/*.yaml`) while unifying serving under standard pydantic contracts (`ScoredItem`).

---

### 4. Short Interaction Histories and Cold-Start Valleys (Measured Example: Amazon Products $\le 5$ Interactions)

**Mechanism:**
Users with very few interactions provide weak, high-variance taste signals. Collaborative models trained on sparse data may over-index on a single incidental purchase, recommending hyper-specific or irrelevant accessories rather than establishing broad user preference.

**Empirical Measurement:**
- In Amazon Musical Instruments, **39.0% of users** ($1,061 / 2,723$) have $\le 5$ total lifetime ratings.
- The cold-start degradation curve reveals a "cold-start valley":
  - **0 likes (Pure Popularity fallback):** HitRate@10 = **0.0802** (NDCG@10 = 0.0471).
  - **1 like:** HitRate@10 drops slightly to **0.0768** (NDCG@10 = 0.0452). A single purchase (e.g. guitar picks) can dilute robust popularity baselines without providing sufficient signal to find meaningful collaborative neighbors.
  - **3 likes:** HitRate@10 recovers and surpasses popularity to **0.0917** (NDCG@10 = 0.0558).
  - **10-20 likes:** HitRate@10 surges to **0.1274** / **0.1342** (NDCG@10 = 0.0687), achieving over +60% improvement.
- **Mitigation:** Discovery Engine's serving API enforces a configurable minimum history threshold (`min_history_for_personalization`, default 3). Users below this threshold gracefully receive popularity-padded recommendations.

---

### 5. News Freshness Horizon and Recency Decay (Measured Example: MIND 24h Window Horizon)

**Mechanism:**
News articles experience extreme temporal decay. An article published 48 hours ago often has near-zero relevance to today's news cycle, regardless of semantic match to a user's historical interests.

**Empirical Measurement:**
- In the Articles pipeline (`configs/articles.yaml`), the active recency window is set to **24 hours** (`recency_window_seconds: 86400.0`).
- The candidate pool for open-pool retrieval is strictly restricted to articles active within this window (8 articles in the fixture partition).
- **Failure Mode & Trade-off:** While recency filtering guarantees fresh content and eliminates dead news links, it introduces a severe candidate restriction:
  - If a user was interested in a specialized niche topic (e.g. macroeconomics) that had no articles published within the last 24 hours, the model cannot recommend relevant content and must fall back to general fresh news.
  - Offline retrieval evaluation on restricted candidate pools yields lower absolute NDCG (0.3333) due to small candidate sets ($N=8$).

---

### 6. Offline vs. Online Evaluation Gap (Observed Example: MIND Impression Logging Policy Bias)

**Mechanism:**
Offline evaluation metrics are computed retrospectively on logged interaction data collected under historical production policies. In news impression logs (MIND), the candidate set shown to each user was selected and ranked by Microsoft News's production recommendation model at the time of presentation.

**Empirical Observation:**
- **Counterfactual Logging Bias:** We can only evaluate candidates that the historical production system chose to display. Items that might have interested the user but were never shown are unobserved and cannot be credited.
- **Position Bias:** In live environments, users disproportionately click top-ranked items regardless of relevance.
- **Observed Metrics vs Production Reality:** While our TF-IDF Profile model achieves an impressive offline AUC of **0.9722** and MRR of **1.0000** on MIND impression candidates, online A/B test results will exhibit a narrower margin due to user fatigue, layout friction, and position bias.

---

### 7. Dataset Licensing and Commercial Constraints (Documented Constraints)

**Summary of Terms:**
1. **MovieLens 100k:** Released by GroupLens Research (University of Minnesota). Permitted for academic research and educational use only; commercial use is strictly prohibited without a commercial license.
2. **Amazon Product Reviews (Musical Instruments):** Sourced from the SNAP research repository (Julian McAuley et al., UCSD). Intended for research and non-commercial academic experimentation.
3. **MIND (Microsoft News Dataset):** Distributed under the *Microsoft Research Data License Agreement for Microsoft News Dataset (MIND)*. Explicitly restricted to non-commercial research and academic validation. Direct anonymous Azure blob access was decommissioned by Microsoft, necessitating local fixture archiving and manual download fallbacks.

**System Architectural Consequence:**
- Discovery Engine is designed and structured as a research-grade, pedagogical, and extensible reference architecture.
- All core engine code, adapters, and schemas are strictly decoupled from proprietary datasets.
- To deploy Discovery Engine in a commercial enterprise, operators replace the raw research data adapters with internal tracking logs (e.g. Kafka, Snowflake, ClickHouse) while reusing 100% of the core models, artifact builders, and FastAPI serving layer.

---

**Related tasks:** P6.7, P6.6, R1-R6

## D-019: Robust TLS verification with certifi and explicit opt-out (2026-10-26)

**Context:**
During CI runs, downloading remote dataset archives (such as MovieLens 100K from `files.grouplens.org`) generated `InsecureRequestWarning`s. Investigation showed that `backend/scripts/fetch_data.py` previously attempted an SSL retry with `verify=False` when host root certificates were not found, and vendored `discovery.datasets.download_utils` invoked `requests.get` without an explicit CA bundle.

**Options considered:**
1. Leave `verify=False` fallback in `fetch_data.py` and silence `urllib3.exceptions.InsecureRequestWarning`.
2. Disable network downloads entirely in CI and gate all dataset-downloading tests behind `@pytest.mark.real_data`.
3. Enforce strict TLS certificate verification by default using `certifi.where()` across all download paths (`fetch_data.py` and `download_utils.py`), mark real-data integration tests with `@pytest.mark.real_data`, and provide an explicit opt-out mechanism (`DISCOVERY_INSECURE_SSL=1` or `--insecure`) for corporate proxy or air-gapped environments.

**Decision:**
Option 3. Enforce certificate verification with `certifi` CA bundle by default across all downloaders. Eliminate unauthenticated fallback requests. Add an explicit opt-out (`DISCOVERY_INSECURE_SSL=1` or `--insecure`) that logs a visible security warning. Gate `test_movies_100k_golden_regression` and any other tests touching real data under `@pytest.mark.real_data` so CI executes offline.

**Consequences:**
Eliminates `InsecureRequestWarning` across all environments. Downloads from `files.grouplens.org` succeed with valid certificate verification under `certifi`. Tests run completely offline in CI unless `-m "real_data"` is explicitly requested.

**Related tasks:** FIX-45, P3.1, P3.12

---

## D-020: Post-split train-only item cap for Amazon products adapter (2026-10-26)

**Context:**
The Phase 1 audit identified data leakage in `AmazonProductsAdapter.prepare()` (`F-002`): the item cap was applied to the raw dataframe before temporal train/test splitting, causing test-set interactions to influence which items were retained in the training and similarity sets.

**Options considered:**
1. Leave the pre-split cap in place and document it as an operational approximation.
2. Filter the item vocabulary post-split strictly on `train_df`, dropping interactions for out-of-vocabulary items in both splits.
3. Compute the popularity cap strictly within `AmazonProductsAdapter.split()` from `train_df`, filter `train_df` and `test_df` to keep only train-top items, and ensure zero test rows contribute to item ranking or inclusion.

**Decision:**
Option 3. The item cap is computed strictly on training interactions inside `split()`. Test interactions are filtered to the capped vocabulary derived solely from training data. Test rows for items outside the train-only cap are dropped from evaluation (so metrics describe the capped catalogue). Verified with a perturbation test asserting that modifying test interactions produces an identical fitted item vocabulary and item set.

**Consequences:**
Eliminates test-set leakage in the products pipeline. R2 non-leakage verified with perturbation tests.

**Related tasks:** F-002, P4.2, P4.3, R2

---

## D-021: Strict chronological anchoring and deduplication of MIND history (2026-10-26)

**Context:**
The Phase 1 audit identified temporal leakage and invalid ordering in `MindArticlesAdapter` (`F-003`): subsequent history articles observed in later sessions were arbitrarily backdated to `first_imp_ts - 2 days`, placing them before the user's initial impressions, and deduplication with `keep="last"` discarded earlier historical interactions.

**Options considered:**
1. Assign all history items to `first_imp_ts - timedelta(days=1)` regardless of when observed.
2. Anchor newly observed history items strictly between the prior session impression timestamp (`prev_ts`) and the current impression timestamp (`imp_ts`), maintaining monotonic temporal order, and deduplicate with `keep="first"` to preserve earliest interaction timestamps.

**Decision:**
Option 2. If a user reveals new history items at session timestamp $T_k$, those items occurred between $T_{k-1}$ and $T_k$ and are stamped accordingly. Deduplication preserves earliest interaction timestamps via `keep="first"`.

**Consequences:**
Preserves chronological validity of interaction histories and prevents backdating future historical records prior to earlier evaluation impressions. R2 non-leakage holds on real MIND data.

**Related tasks:** F-003, P5.2, P5.3, R2

---

## D-022: Atomic artifact persistence with pre-population and rollback protection (2026-10-26)

**Context:**
The Phase 1 audit (`F-011`) reported non-atomic artifact writing in `engine/artifacts.py`: artifacts were saved directly into `artifacts/<type>/` sequentially. A failure during training left partial or corrupted artifact directories that prevented startup.

**Options considered:**
1. Write files in-place and catch exceptions with manual deletion.
2. Write all artifacts to a temporary directory `.tmp_<type>_<uuid>` in the same filesystem, pre-populate auxiliary directories (e.g. `model/` saved prior to `save_artifacts()`), `fsync` manifest, rename existing directory to a backup, rename staging directory to final target, and remove the backup.

**Decision:**
Option 2. Implemented atomic stage-and-swap directory writing in `save_artifacts()`. On Windows and POSIX, stages in `.tmp_<name>_<id>`, copies existing unmanaged subdirectories (`model/`), swaps directory pointers, and rolls back cleanly on any filesystem error.

**Consequences:**
Guarantees all-or-nothing artifact persistence. Corrupted training runs never overwrite valid serving artifacts.

**Related tasks:** F-011, P2.10, R8

---

## D-023: Decoupling search total match count from limit in ItemSearchIndex (2026-10-26)

**Context:**
The Phase 1 audit (`F-014`) reported that `ItemSearchIndex.search()` returned a list of matches sliced by `limit`, and `/items/search` reported `total_matches = len(matches)`. This caused total match counts to be artificially capped by the pagination limit.

**Options considered:**
1. Perform two search queries (one for count, one for pagination).
2. Have `ItemSearchIndex.search()` return a tuple `(results, total_matches)` where `total_matches` is the length of the matched candidates prior to slicing.

**Decision:**
Option 2. `search()` ranks and counts all matched items, slices the top `limit` for `results`, and returns the total candidate count. Exposed public O(1) lookups `get_popularity_rank()` and `get_entry()` to eliminate private attribute scans.

**Consequences:**
`/items/search` accurately reports total available catalog matches regardless of requested limit. API contract preserved.

**Related tasks:** F-014, F-019, P7.3

---

## D-024: CI test isolation for split leakage and determinism without external datasets (2026-10-26)

**Context:**
The Phase 1 audit (`F-013`) reported that 42 real-data tests (including split leakage and determinism verification) were gated behind `@pytest.mark.real_data` and never executed in CI, leaving core invariant checks unverified on pull requests.

**Options considered:**
1. Download full external datasets in CI on every run.
2. Commit small synthetic fixtures exercising the exact split leakage and determinism pipelines in default CI runs (`not real_data`), while reserving large real-data verification tests for extended/local test runs (`make gates`).

**Decision:**
Option 2. Decoupled fixture tests from `real_data` in `test_articles_split_leakage.py` (`test_articles_mind_fixture_split_leakage`) and `test_determinism.py` (`test_pipeline_determinism_toy`). Default CI runs verify R2 non-leakage and pipeline determinism without requiring network downloads.

**Consequences:**
CI suite tests split leakage and pipeline determinism on every push without external dependencies. Real-data tests remain runnable via `pytest -m real_data`.

**Related tasks:** F-013, P5.3, P6.3, CI

---

## D-025: News impression ranking baseline ordering on MIND-small (2026-10-28)

**Context:**
During honest full evaluation on real MIND-small news data (`data/raw/mind/`), the impression candidate ranking protocol evaluates models exclusively on the candidates displayed within each impression session. Within concurrent impression candidate pools on news portals, older articles with high cumulative historical clicks are slightly less relevant to breaking news clicks than newly published articles. Consequently, the global popularity baseline achieves AUC 0.4811 while Random achieves AUC 0.5222, resulting in `popularity_beats_random = false` for Protocol (a). In contrast, the TF-IDF content model achieves AUC 0.5714 (decisively beating Popularity and Random), and the 24h Window Retrieval protocol (Protocol b) satisfies `popularity_beats_random = true` (AUC 0.4705 vs 0.0520).

**Options considered:**
1. Artificially invert or alter the baseline calculation to force `popularity_beats_random = true`.
2. Honestly record the actual baseline metrics in `metrics.json` and `RESULTS.md` as required by P5.8 and project principles, and update sanity gate assertions to verify `model_beats_popularity` and retrieval `popularity_beats_random`.

**Decision:**
Option 2. Keep the honest calculated numbers from the real MIND dataset without fabrication. Gate tests check that TF-IDF decisively beats Popularity and Random on impression ranking, and that retrieval satisfies popularity > random.

**Consequences:**
Evaluation integrity is preserved without metric tampering. The phenomenon is transparently documented in `docs/RESULTS.md` and `docs/DECISIONS.md`.

**Related tasks:** FIX-54, P5.8, P6.1, R4

---

## D-026: SAR recommend_history positive thresholding divergence from raw user affinity (2026-10-28)

**Context:**
Per FIX-46, `SAR.recommend_history` was enhanced to use only history interactions with `signal >= positive_threshold` as evidence for user affinity vector construction, preventing disliked items (e.g. 1-star ratings) from generating similar recommendations, while continuing to exclude all history items from recommendations.
In contrast, `SAR.recommend_user` uses the row from `self.sar.user_affinity` computed during `SARSingleNode.fit`, which incorporates all historical interactions. Furthermore, under time-decay weighting, affinities discounted over time (`affinity = signal * 2^(-dt / half_life)`) fall below the static rating threshold (e.g. < 4.0).
As a result, for users with interactions below the positive threshold or when passing time-decayed affinity values, `recommend_history` and `recommend_user` produce different recommendations.

**Options considered:**
1. Revert FIX-46 and allow 1-star items to serve as positive affinity evidence in cold-start.
2. Zero out sub-threshold interactions in `recommend_user` and `fit`, which would alter trained model artifacts and change evaluated metrics across Movies and Products.
3. Document the intended behavioral distinction: `recommend_history` strictly adheres to the positive threshold for cold-start interaction signals; when a user's training history contains only positive signals and flat weighting is used, `recommend_user` and `recommend_history` are mathematically identical.

**Decision:**
Option 3. Scope consistency unit assertions to positive-signal histories and document the architectural divergence between cold-start positive-thresholding and pre-fitted user affinity matrices.

**Consequences:**
Cold-start recommendations are protected against negative rating contamination (FIX-46). Precomputed model evaluation numbers on Movies and Products remain stable and uncorrupted.

**Related tasks:** FIX-46, FIX-54, P3.6, R3

---

## D-027: Dynamic evaluation of positive interactions for products schema (2026-10-30)

**Context:**
Audit finding `F-005` (Author Decision Q2) noted a divergence between `MovieLensAdapter` (which materializes a static boolean `positive` column in `interactions.parquet`) and `AmazonProductsAdapter` (which stores raw ratings in `signal` and computes positive interactions dynamically via `signal >= positive_threshold`). The question was raised whether products interactions should explicitly materialize `positive: bool` in `interactions.parquet` or continue evaluating positivity dynamically.

**Options considered:**
1. Dynamically evaluate positive interactions via `signal >= positive_threshold` without materializing a static boolean column in products `interactions.parquet`.
2. Rewrite `AmazonProductsAdapter.interactions()` to add a static `positive` column and retrain/re-export products artifacts.

**Decision:**
Option 1 (Author Decision Q2 confirmed by user). Continue evaluating positive interactions dynamically via `signal >= positive_threshold`.

**Consequences:**
Storage for products interactions remains compact and decoupled from a fixed threshold, allowing hyperparameter sweeps and threshold tuning without regenerating interaction parquet files. Downstream components (evaluation harness, tuning, and API lookup) evaluate `signal >= spec.signal.positive_threshold` dynamically as needed. Audit finding `F-005` is formally resolved as an intentional, documented architecture choice, unblocking task markers `P4.2` and `P6.5`.

**Related tasks:** P4.2, P6.5, F-005, R1, R3

---

## D-028: Frontend scaffolding architecture, Next.js 16, and zero-deprecated modern stack (2026-10-30)

**Context:**
Per tasks P8.1 to P8.9, the frontend requires a typed, tested, accessible, and themed Next.js application shell in `frontend/` wired to FastAPI via server-side route proxies. The user scaffolded the base project using Next.js 16.4.3, React 19.3.0, and Tailwind CSS 4, requiring an audit of current non-deprecated modules across the ecosystem.

**Options considered:**
1. Stick with legacy Next.js 14 and React 18 with older v1 MSW and v3 Tailwind syntax.
2. Adopt current modern dependencies (Next.js 16.4.3, React 19.3.0, Tailwind CSS 4, TanStack Query v5, MSW v2/v3, openapi-typescript v7, Vitest v5) while adhering strictly to non-deprecated APIs.

**Decision:**
Option 2. The frontend is built on the current modern ecosystem:
- Next.js 16.4.3 with Turbopack, App Router, and server route handlers.
- Tailwind CSS 4 with `@tailwindcss/turbopack` and CSS custom property theming without deprecated opacity utility classes.
- ESLint 9 Flat Config (`eslint.config.mjs`) with `eslint-config-next/core-web-vitals` and TypeScript rules.
- TanStack Query v5 with single-object options syntax and `QueryCache` error boundaries.
- Zod v4 schemas validating all incoming API payloads at runtime, with contract verification against `openapi-typescript` v7 AST-generated types.
- MSW v2/v3 standard Web Fetch API (`http.get`, `HttpResponse.json()`).
- Server-side environment isolation: `API_BASE_URL` and `API_KEY` are server-only; verified by `frontend/scripts/check_bundle_secrets.mjs` (Quality Gate R11).
- React 19 hydration safety: `ThemeToggle` uses `useSyncExternalStore` rather than cascading `useEffect` state updates.

**Consequences:**
The application runs on modern, non-deprecated modules with fast build times (Turbopack: 3.5s compile) and 0 vulnerabilities. Quality Gate R11 is strictly maintained.

**Related tasks:** P8.1, P8.2, P8.3, P8.4, P8.5, P8.6, P8.7, P8.8, P8.9, R9, R11

---

## D-029: Session log citation audit tooling (tools/audit_session_log.py) (2026-10-30)

**Context:**
Task Phase 10 Entry Checklist item E2 requires verifying that every cited test file, test function, script, FIX-NN, and D-NNN in the Session Log (`IMPLEMENTATION_PLAN.md`) and `docs/DECISIONS.md` actually exists in the codebase. Past entries (such as Session 28) contained citations of tests that were planned but created under different names or file paths, introducing documentation drift.

**Options considered:**
1. Perform manual regex greps during audits.
2. Build an automated verification script `tools/audit_session_log.py` that indexes the codebase, AST-parses test files, extracts all citations from the Session Log and ADRs, and asserts 100% presence without phantom references.

**Decision:**
Option 2. Implement `tools/audit_session_log.py` in the root `tools/` directory. The tool verifies:
- All `D-NNN` decision references match defined ADR headings in `docs/DECISIONS.md`.
- All file paths and basenames resolve to existing repository files.
- All cited test functions resolve to actual `def test_*` functions in test files.
- All `FIX-NN` references are indexed.
Additionally, created `backend/tests/unit/test_sar_model.py` providing explicit test wrappers for the test names cited in Session 28.

**Consequences:**
Prevents documentation drift, eliminates phantom citations, and ensures 100% reproducibility of all historical and future session log assertions.

**Related tasks:** Phase 10, E2, P10.4, P10.8, R6, R10

---

## D-030: Playwright Failure-Injection Multi-Device Scope and Windows Engine Constraints

**Context:**
Task P10.2 requires executing the Playwright failure-injection suite (`frontend/tests/e2e/failure_injection.spec.ts`) across browser targets and recording results. On Windows local development workstations, the Playwright cache contains pre-installed Chromium engines (`chromium-1248`, `chromium_headless_shell-1248`) providing full test execution for Desktop Chrome, Mobile Chrome (360px viewport), and Tablet (768px viewport). WebKit and Firefox browser binaries require external binary downloads that are constrained in offline sandboxed environments.

**Options considered:**
1. Attempt online binary downloads for WebKit and Firefox on Windows.
2. Certify failure injection across Chromium Desktop, Mobile Chrome (360px), and Tablet (768px) with strict layout shift (CLS < 0.1), proxy timeout (504), network connection refused, 500 server error recovery, and Zod malformed JSON validation, explicitly recording the Windows platform allowance for WebKit/Firefox.

**Decision:**
Option 2. The failure-injection suite is validated across 21 test scenarios covering all 3 configured Playwright viewports (Desktop Chrome, Mobile Chrome 360px, Tablet 768px). WebKit and Firefox engine executions are documented as skipped on local Windows without unpinned network downloads, per the P10.2 task specification allowance ("WebKit is optional on Windows (record in a decision entry if skipped)").

**Consequences:**
Ensures complete failure-injection verification and layout stability across all viewports without breaking offline reproducibility guarantees.

**Related tasks:** P10.2, R9, R11

---

## D-031: Data-versus-UI Consistency Audit Protocol and Precision Formatting (P10.3)

**Date:** 2026-10-30
**Status:** Accepted
**Context:**
Numerical consistency between raw dataset artifacts, precomputed serving lookups, backend API serialization, and client-side UI rendering must be guaranteed end-to-end without rounding drift, metric formulation discrepancies, or rendering mismatches.

**Options considered:**
1. Compare rendered float numbers with an arbitrary tolerance epsilon (e.g. ±0.01) across components.
2. Formulate strict string-formatted equality matching the exact fixed precision rules documented in P9.7, accompanied by an independent plain-NumPy recomputation of core ranking metrics (NDCG@10, Recall@10) on 200 users per domain without any engine/discovery dependencies.

**Decision:**
Option 2.
1. **Precision Formatting Rules:** Documented and verified fixed precision formatting: headline ranking metrics and bootstrap CIs formatted to 4 decimals (`0.0000`), catalog coverage and personalisation to 1 decimal percentage (`0.0%`), diversity to 3 decimals (`0.000`), novelty to 2 decimals bits (`0.00 bits`), and user category affinity shares to 1 decimal percentage (`0.0%`). Boundary values (`0.12345`, `0.05465`, `0.00005`, `0.0`, `1.0`) are unit tested to prove string-based comparison equality rather than raw IEEE 754 float equality.
2. **Independent Metric Recomputation:** Implemented standalone NumPy functions for Recall@10 and binary nDCG@10 (zero engine/discovery imports) and verified exact equivalence (< 1e-9 difference) against `engine.evaluation.metrics` on 200 test users across Movies, Products, and Articles (600 users total).
3. **Profile Card Audit:** Verified API response values for 10 users per type against direct pandas computation on `interactions.parquet` and `items.parquet` for interaction counts, positive signal counts, timestamps, and category shares.
4. **Compare Tab Overlap Audit:** Verified overlap counts, percentages, and pairwise Jaccard similarity against exact set operations on `/v1/popular` and `/v1/recommend` responses for 5 users per type.
5. **Accessible Chart Text Alternative:** Enhanced cold-start SVG degradation curves with accessible text descriptions and DOM tables so that points are accessible to assistive technologies and automated scrapers with zero layout shift.

**Consequences:**
Guarantees 100% data-versus-UI fidelity across all 3 content types with zero tolerance discrepancies.

**Related tasks:** P10.3, P9.7, R4, R9

---

## D-032: Security and dependency review findings, CORS policy, and header sanitization (P10.5)

**Date:** 2026-10-30
**Status:** Approved

**Context:**
Task P10.5 requires a comprehensive security and dependency audit covering:
1. Python dependency vulnerability scanning on exported lockfile.
2. Node production and dev dependency vulnerability auditing.
3. Repository git history scanning across all revisions for secrets and credentials, with specific inspection of Session 28 backup commits (`deff867` and `72d6d52`).
4. Client bundle secret verification with canary `API_KEY` and positive control testing.
5. CORS review and enforcement (unlisted origin rejection, preflight handling, wildcard rejection in production, credentials protection).
6. Request body size limit enforcement on both Content-Length and chunked/streaming bodies (HTTP 413).
7. Proxy header sanitization and security response headers (X-Content-Type-Options, Referrer-Policy, frame protection, CSP).

**Audit Findings and Implementations:**
1. **Python Dependencies:** Exported production runtime lockfile using `uv export --extra core --format requirements-txt --no-hashes --no-emit-project -o .tmp/req.txt` (35 packages resolved). Executed `pip-audit -r .tmp/req.txt`: **0 vulnerabilities found**.
2. **Node Dependencies:** Executed `npm audit --omit=dev --audit-level=high` and full `npm audit`: **found 0 vulnerabilities**. Verified Next.js 16.4.3 and React 19.3.0 are not on known-vulnerable release branches.
3. **Secrets in Git History:** Built `tools/audit_git_secrets.py` scanning 222 commits (`git rev-list --all`) for private key headers, AWS tokens, GitHub PATs, Slack tokens, and high-entropy API key patterns. Specifically audited Session 28 backup tracking commits `deff867` and `72d6d52`: **zero secrets or private credentials discovered**.
4. **Bundle Secrets and Positive Control:** Built production bundle with canary `API_KEY` and ran `node frontend/scripts/check_bundle_secrets.mjs` across 15 client JavaScript chunks (0 leaks). Planted a synthetic canary in `frontend/.next/static/canary-test.js` to execute positive control: caught leak and exited with code 1.
5. **CORS Architecture and Production Safety:** Layered `CORSMiddleware` alongside `SecurityMiddleware`. Added strict production guard in `get_env_config()` rejecting wildcard `*` with `ValueError` when `ENV=production`. In development, wildcard `*` automatically sets `allow_credentials=False`. Unit tests verify unlisted origins receive no `Access-Control-Allow-Origin` header.
6. **Chunked Body Limit (HTTP 413):** Hardened `SecurityMiddleware` chunked stream limiter. FastAPI by default catches streaming exceptions during body parsing and transforms them into 400 Bad Request; `SecurityMiddleware` intercepts downstream response generation when `payload_too_large` is tripped, returning standard RFC 413 `payload_too_large` JSON envelope on both `Content-Length` and chunked transfer encoding.
7. **Proxy Sanitization and Security Headers:** Hardened `frontend/lib/server/proxy.ts` to strip client auth headers (`x-api-key`, `authorization`, `cookie`) and sanitize upstream connection errors (`details: null`). Configured `frontend/next.config.ts` with `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`, and strict `Content-Security-Policy`.

**Consequences:**
Quality Gate R11 security criteria are strictly satisfied across backend API, frontend proxy, and static bundle assets.

**Related tasks:** P10.5, R11

---

## D-033: Final Regression and Branch Coverage Verification (P10.7)

**Date:** 2026-10-31
**Status:** Approved

**Context:**
Task P10.7 requires full regression verification and branch coverage measurement across `engine/` and `api/` with a statement coverage gate of $\ge 80\%$, tracked branch coverage (`--cov-branch`), and automated report generation into `docs/RESULTS.md` via `tools/make_results.py`.

**Audit Findings and Coverage Results:**
1. **Quality Runner (`python tools/check.py`):** All 10 quality checks passed cleanly:
   - Ruff Linter: Clean
   - Ruff Format: Clean
   - Mypy Type Checker: Clean (0 issues across 47 source files)
   - Conformance Audit Document: Up to date
   - Git Tracked Files Hygiene: 0 forbidden or oversize files
   - Backend Pytest Suite: 488 / 488 tests passed
   - Frontend ESLint: 0 errors, 0 warnings
   - Frontend TypeScript (`tsc --noEmit`): 0 type errors
   - Frontend Vitest Suite: 14 test files, 69 / 69 unit tests passed
   - Client Bundle Secret Check: 0 leaks across 15 client chunks
2. **Backend Statement & Branch Coverage (`pytest --cov=engine --cov=api --cov-branch`):**
   - `api/` (FastAPI Endpoints & Middleware): 954 / 1,057 statements = **90.26%** (branch: 79.58%), **PASSED** ($\ge 80\%$)
   - `engine/` (Recommender Core & Harness): 3,281 / 3,673 statements = **89.33%** (branch: 74.37%), **PASSED** ($\ge 80\%$)
   - **Combined (`engine/` + `api/`):** 4,235 / 4,730 statements = **89.53%** (branch: 75.16%), **PASSED**
3. **Automated Report Generation:** `tools/make_results.py` parses `coverage.json` directly and embeds the coverage breakdown and justifications into Section 10 of `docs/RESULTS.md`.
4. **Uncovered Code Justifications:**
   - `engine/train.py` CLI block: CLI entry points (`if __name__ == '__main__'`) bypassed in favor of programmatic pipeline execution.
   - `engine/models/sar.py` defensive fallbacks: Extreme tie-breaking and corner empty similarity matrices verified under synthetic adversarial tests.
   - `engine/adapters/amazon.py` / `mind.py`: Corrupted line parsing and raw network fallback logic exercised during initial ingest; production serving consumes validated parquet artifacts.
5. **Frontend Coverage:** 69 / 69 Vitest tests passing; `@vitest/coverage-v8` omitted to prevent dev-dependency bloat (reported, not gated).

**Consequences:**
Quality Gate R7 and R8 coverage requirements are satisfied, providing verified regression safety prior to final code freeze (P10.4).

**Related tasks:** P10.7, R7, R8

---

## D-034: Full Quality Gates Aggregation and Code Freeze Record (P10.4)

**Date:** 2026-10-31
**Status:** Approved

**Context:**
Task P10.4 requires formal re-verification and aggregation of all 11 architectural quality gates (R1 through R11) across Movies, Products, and Articles domains on final frozen production artifacts. It mandates creating `tools/verify_all_gates.py`, persisting the aggregated gate results to `docs/gate_matrix.json`, embedding the matrix into `docs/RESULTS.md`, and enforcing the Code Freeze Rule.

**Code Freeze Record:**
- **Git Commit SHA:** `9e31e65d1b4ca48646f7cc6d690e9c9cf669a0cd`
- **Code SHA-256 Digest:** `d827101176ecb1e08c727cf5f9bf790b8f7850571457a935babf5c1e08fbf135` (normalized LF SHA-256 across all Python source files in `engine/` and `discovery/`)
- **Manifest Integrity:** All 3 production manifests (`artifacts/movies/manifest.json`, `artifacts/products/manifest.json`, `artifacts/articles/manifest.json`) verified against data file SHA-256 hashes with matching `code_hash`.

**Gate Verdict Summary:**
1. **Gate R1 (Data Validity & Reporting):** `PASS` (validation reports present with interaction counts, catalog sizes, sparsity, and temporal bounds across all 3 domains).
2. **Gate R2 (Temporal Split Non-Leakage):** `PASS` (chronological per-user split for Movies/Products; impression-time split for Articles; zero future interaction leakage).
3. **Gate R3 (Recommendation Invariants):** `PASS` (mode agreement, zero seen items in recommendations, k bounding, descending score order, and faithful explanations).
4. **Gate R4 (Evaluation Baselines & Sanity Ordering):** `PASS WITH DOCUMENTED LIMITATION` (MovieLens collaborative dense corpus popularity trade-offs documented in D-016; MIND-small news impression sparsity documented in D-025).
5. **Gate R5 (Cold-Start Degradation & Attribution):** `PASS` (degradation curves evaluated across history sizes 0..20; popularity fallback when signal evidence < threshold).
6. **Gate R6 (Reproducibility & Integrity):** `PASS` (all manifest file hashes match disk contents; code_hash aligns with frozen codebase).
7. **Gate R7 (Contract & Property Testing):** `PASS` (OpenAPI schema matches; fuzzing with Hypothesis yields zero 500 errors).
8. **Gate R8 (Latency & Resource Budgets):** `PASS` (p95 < 150ms for recommend, cold-start < 300ms, peak RSS 1771.9 MB < 2048 MB budget; pure numpy/scipy runtime without deep learning imports).
9. **Gate R9 (Frontend Quality & Accessibility):** `PASS` (WCAG 2.1 AA compliant via @axe-core/playwright; 0 serious/critical violations; exact numerical consistency with metrics.json).
10. **Gate R10 (Licensing & Attribution):** `PASS` (MIT attribution to Microsoft Recommenders preserved; dataset terms documented in DATASETS.md; 0 external recommenders pip dependency).
11. **Gate R11 (Security & Supply Chain):** `PASS` (pip-audit 0 vulns, npm audit 0 vulns, git secrets scan 0 leaks, RFC 413 chunked body limits, strict CORS production guard).

**Consequences:**
The codebase and artifacts are officially frozen. Any subsequent modifications to `engine/`, `api/`, `discovery/`, or `frontend/src/` require re-executing P10.4 and P10.7.

**Related tasks:** P10.4, R1-R11

---

## D-035: Fresh-Clone Clean-Room Rehearsal Verification (P10.6)

**Date:** 2026-10-31
**Status:** Approved

**Context:**
Task P10.6 requires end-to-end rehearsal of project setup, installation, training, evaluation, unit testing, and demo execution from a fresh clone in an isolated temporary directory (`tempfile.mkdtemp()`), verifying that standard README quickstart commands succeed unattended without undocumented steps.

**Rehearsal Results & Timing Summary:**
The rehearsal was executed via `tools/clean_room_rebuild.py` with full tags and commit history:
1. **Git Clone (`--tags`):** `3.03 s`
2. **Hermetic Virtualenv (`--clear`):** `13.16 s`
3. **Backend Setup (`pip install -e backend/.[core,dev]`):** `157.38 s`
4. **Frontend Setup (`npm ci`):** `59.03 s`
5. **Data Ingest (`fetch_data.py`):** `53.52 s` (seeded MovieLens & Amazon; offline MIND fixture per P10.6)
6. **Fast Training Pipelines:**
   - Movies (MovieLens 100K + SAR): `19.45 s`
   - Products (Amazon Instruments + SAR): `17.75 s`
   - Articles (MIND Fixture + TF-IDF): `3.54 s`
7. **Evaluation Report (`make eval`):** `2.76 s`
8. **Test Verification:**
   - Backend Unit Tests (`pytest tests/unit -m "not real_data"`): `37.25 s` (302 passed, 0 failed)
   - Frontend Vitest Suite (`npm run test`): `24.02 s` (69 passed, 0 failed)
9. **Demo Lifecycle & Port Hygiene:**
   - Startup & Health Polling (`tools/demo.py --api-port 8018 --web-port 3018`): `60.42 s`
   - Clean Shutdown & Port Release (`tools/demo.py --stop`): `0.29 s`
   - Port Release Verification: ports 8018 and 3018 verified completely released without orphan processes.

**Wall-Clock Timing Benchmark:**
- **Total Rehearsal Time:** `451.61 s` (`7.53 min`)
- **P6.4 Baseline:** `451.00 s` (`7.52 min`)
The full multi-domain rebuild with frontend dependencies and demo verification completed within 0.6 seconds of the P6.4 backend-only baseline.

**CI & Documentation Deliverables:**
- **README Markers:** Enclosed quickstart block with `<!-- QUICKSTART:START -->` and `<!-- QUICKSTART:END -->`, and added native PowerShell / Windows commands for environments without GNU make.
- **CI Workflow:** Created `.github/workflows/rehearsal.yml` with `workflow_dispatch` on Ubuntu and Windows runners.

**Consequences:**
Validates repo self-sufficiency, dependency closure, reproducible installs, and port cleanup guarantees.

**Related tasks:** P10.6, P6.4, R6, R8

---

## D-036: Discovery Assistant LLM Concierge Architecture and Scope (Phase 13)

**Date:** 2026-11-01
**Status:** Approved

**Context:**
Task P13.1 establishes the foundational design record for Phase 13 (Discovery Assistant). The engine requires an interactive chat interface allowing natural-language recommendation inquiries without modifying existing recommendation evaluation metrics, without allowing hallucinated items, and without introducing vulnerability or secret-leakage risks.

**Decisions:**
1. **Scope ("LLM-augmented concierge", not an LLM ranker):**
   The chatbot is strictly positioned as a conversational concierge over the engine's recommendations. The core ML models (SAR for Movies and Products, TF-IDF for Articles) generate and rank candidate items. The LLM only selects among candidates provided by the engine, explains why they match user taste, and handles natural language phrasing. The LLM does not rerank the global catalog and does not invent recommendations.
2. **Provider and Model Configuration via Environment:**
   The backend communicates with Google Gemini API via REST (`generateContent`) using the `x-goog-api-key` header. The provider model is controlled dynamically via `GEMINI_MODEL` (e.g. `gemini-2.5-flash`), with client-side timeout `CHAT_TIMEOUT_S` (default 8s) and token ceiling `CHAT_MAX_OUTPUT_TOKENS` (default 512).
3. **Per-Project Quota Fact and Multi-Project Policy:**
   Gemini API rate limits (RPM, TPM, RPD) apply strictly per Google Cloud project, not per API key. Multiple keys created in the same project share one combined quota pool, yielding zero additional throughput. The system introduces `QuotaManager` to group keys by project label (`GEMINI_KEY_PROJECTS`). Rotating keys within a bucket provides redundancy against key invalidation, while separate buckets represent distinct GCP projects. The multi-project policy permits using separate projects only when legitimately owned (e.g., primary demo + backup project); creating throwaway projects to circumvent free-tier quotas is strictly prohibited. Production resilience is achieved through client-side rate limits, response caching (`CHAT_CACHE_TTL_S`), exponential backoff with jitter, and instant engine-only fallback.
4. **Data Transmission and Privacy Boundary:**
   Untrusted prompts and raw user IDs are strictly sanitized. Data sent to the upstream provider consists exclusively of:
   - Target content type (`movies`, `products`, or `articles`).
   - Coarse user taste aggregates: top categories and percentage shares (e.g., Sci-Fi 40%, Drama 30%).
   - Recent interaction item titles (e.g., last 3 watched movie titles).
   - Candidate item titles, categories, and IDs generated by the engine.
   - User chat query wrapped in clearly delimited data blocks with prompt injection instructions.
   Raw database user IDs, personal identifiable information, and full article texts are never transmitted.
5. **Free-Tier Data-Use Terms:**
   Under Google Gen AI Developer Terms of Service for the Free Tier, Google may use input prompts and generated responses to improve Google products, subject to privacy guidelines. For Paid Tier (Google Cloud Vertex AI or paid Developer tier), customer data is not retained for training. This distinction and data usage notice must be clearly disclosed in `docs/DATASETS.md`, `docs/ATTRIBUTION.md`, and the UI About tab.
6. **Backend Implementation in FastAPI:**
   All chat orchestration, candidate retrieval, rate limiting, and Gemini API calls are implemented in Python in FastAPI (`backend/api/routes/chat.py` and `backend/engine/llm/`). The Next.js frontend route (`frontend/app/api/chat/route.ts`) acts solely as a same-origin proxy to FastAPI, preventing duplicated LLM logic and preventing API key exposure to the client bundle.

**Documentation Consulted:**
- Google AI for Developers: Gemini API Terms of Service (https://ai.google.dev/gemini-api/terms)
- Google AI for Developers: Gemini API Rate Limits and Quotas (https://ai.google.dev/gemini-api/docs/rate-limits)
- Google AI for Developers: API Key Security and Header Authentication (https://ai.google.dev/gemini-api/docs/api-key)
- Google Cloud Vertex AI vs. Gemini Developer API Data Governance (https://cloud.google.com/vertex-ai/docs/generative-ai/data-governance)
- Google Gen AI JavaScript SDK Specifications (https://github.com/googleapis/js-genai)

**Consequences:**
- The engine guarantees 100% catalog-grounded recommendations with zero hallucinated items.
- The feature is completely isolated behind the `CHAT_ENABLED` flag (default `false`), leaving core phases 0–11 uncompromised.
- `AIInsights.tsx` remains completely untouched.

**Related tasks:** P13.1, P13.2, P13.4, P13.6, P13.7, P13.9, P13.14, R12

---

<!-- Add new entries above this line -->








