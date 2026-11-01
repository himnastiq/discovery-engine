# Discovery Engine

An adaptive consumer recommendation engine that personalizes content discovery across Movies, Products, and News through a unified CPU-optimized pipeline.

![Discovery Engine Dashboard]


https://github.com/user-attachments/assets/0bf935b3-5a58-4d38-b8b9-f4b8743b6711


## How One Engine Adapts Across Three Domains

Consumer recommendation requires fundamentally different signal semantics across content verticals:
- **Movies:** Collaborative filtering over explicit star ratings (1.0 to 5.0 stars), predicting long-tail affinities via Simple Algorithm for Recommendation (SAR).
- **Products:** Item-to-item co-occurrence over sparse e-commerce transaction histories with a bounded catalog budget.
- **Articles:** Content-based TF-IDF token modeling with exponential recency decay, overcoming extreme cold-start dynamics within a 24h freshness window.

A detailed architectural breakdown and data flow diagram are provided in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Quick Start

### Prerequisites
- **Python:** 3.11 (tested on Python 3.11.7)
- **Node.js:** v22 (tested on Node v22.19.0, npm 11.12.1)
- **uv / pip:** Standard virtual environment tooling

<!-- rehearsal:start -->
<!-- QUICKSTART:START -->
```bash
# 1. Set up virtual environment and install dependencies
make setup

# 2. Fetch dataset caches (MovieLens 1M and Amazon Video Games)
make data

# 3. Train models (fast mode uses fixtures for quick verification)
make train-fast

# 4. Evaluate models and generate results report
make eval

# 5. Launch unified demo supervisor (API + frontend)
make demo
```
<!-- QUICKSTART:END -->
<!-- rehearsal:end -->

### PowerShell / Windows (Without Make)

```powershell
# 1. Virtual environment and dependencies
python -m venv .venv
.venv\Scripts\pip install -e backend/.[core,dev]
cd frontend; npm ci; cd ..

# 2. Fetch raw datasets
python backend/scripts/fetch_data.py

# 3. Train fast variants
python -m engine.train --type movies --fast
python -m engine.train --type products --fast
python -m engine.train --type articles --fast

# 4. Generate results report
python tools/make_results.py

# 5. Launch demo
python tools/demo.py
# (Stop running demo at any time with: python tools/demo.py --stop)
```

## Dataset Setup

The engine is evaluated across three standardized benchmark datasets:
- **Movies:** MovieLens 1M explicit rating benchmark.
- **Products:** Amazon Video Games 5-core transaction records (capped to an 8,000 item budget for memory isolation).
- **Articles:** MIND News Dataset (`MIND-small`).

Due to licensing terms, raw dataset archives are not redistributed in the repository. As detailed in [`docs/DATASETS.md`](docs/DATASETS.md), MovieLens and Amazon datasets download automatically via `backend/scripts/fetch_data.py`, while MIND requires an explicit agreement download. In `--fast` development mode, synthetic fixtures in `backend/tests/fixtures/` are used automatically.

<!-- GENERATED:dataset_table:START -->
| Content Type | Dataset | Variant | Items | Users | Interactions | Sparsity | Code Hash |
|---|---|---|---|---|---|---|---|
| **Movies** | MovieLens 1M | `1m` | 3,416 | 6,040 | 999,611 | 0.9516 | `d8271011` |
| **Products** | Amazon Video Games | `video_games` | 10,672 | 24,303 | 231,780 | 0.9991 | `d8271011` |
| **Articles** | MIND | `small` | 52,875 | 92,456 | 2,353,960 | 0.9995 | `d8271011` |
<!-- GENERATED:dataset_table:END -->

## Results Summary

<!-- GENERATED:results_summary:START -->
| Domain | Model | HitRate@10 (95% CI) | NDCG@10 (95% CI) | Popularity NDCG@10 | Benchmark Verdict |
|---|---|---|---|---|---|
| **Movies** | SAR (Jaccard) | 0.2826 [0.2625, 0.3011] | 0.0592 [0.0541, 0.0644] | 0.0546 | Model lower than Popularity (documented limitation D-016) |
| **Products** | SAR (Jaccard) | 0.0938 [0.0794, 0.1096] | 0.0510 [0.0420, 0.0602] | 0.0163 | Model higher than Popularity (CI separated) |
| **Articles** | TF-IDF Profile | 0.0100 [0.0000, 0.0250] | 0.0027 [0.0000, 0.0082] | 0.0000 | Model higher on retrieval; impression CI overlaps Popularity (D-025) |

> **Note:** Offline evaluation results do not constitute a prediction of online production performance.
<!-- GENERATED:results_summary:END -->

Offline evaluation results serve as comparative algorithmic indicators and are not a prediction of online production performance.

Detailed metric breakdowns, cold-start degradation curves, and coverage charts are compiled in [`docs/RESULTS.md`](docs/RESULTS.md).

## Testing and Verification Gates

System stability and algorithmic integrity are validated through 11 Conformance Gates (R1 to R11):
- **Continuous Integrity Check:** `python tools/check.py` runs formatting, linting, type checks, unit tests, and secret leakage audits.
- **Comprehensive Gate Audit:** `python tools/verify_all_gates.py` verifies all gates against final artifacts.
- **Conformance Documentation:** Documented status and evidence mapping are maintained in [`docs/CONFORMANCE.md`](docs/CONFORMANCE.md).

## Repository Map

<!-- GENERATED:repo_map:START -->
```
discover/
├── backend/
│   ├── engine/          # Original modular recommender engine (adapters, models, configs, splits, metrics)
│   ├── api/             # Original FastAPI serving service (routes, security, search, lookups)
│   ├── discovery/       # Vendored, trimmed CPU library (MIT License)
│   └── tests/           # Comprehensive backend test suite (unit, contract, integration, fuzzing)
├── frontend/
│   ├── src/             # Next.js App Router application (React 19, TypeScript strict, Tailwind CSS)
│   ├── components/      # UI component library and domain recommendation feeds
│   └── tests/           # Frontend testing suites (Vitest unit tests, Playwright E2E)
├── data/
│   └── raw/             # Raw dataset cache (MovieLens, Amazon Reviews, MIND)
├── artifacts/           # Frozen multi-domain serving artifacts (Parquet tables, serialized models, metrics)
├── tools/               # Repository management, verification, audit, and clean-room rebuild scripts
├── docs/                # Architectural records, evaluation results, figures, and conformance documentation
└── .github/workflows/   # Continuous integration and clean-room rehearsal workflows
```
<!-- GENERATED:repo_map:END -->

## Limitations

As documented in [`docs/DECISIONS.md`](docs/DECISIONS.md) (D-018), key boundaries include:
- **Absence of Dislike Signals:** Sub-threshold ratings (<4.0 stars) are treated as non-interactions; negative sentiment is not explicitly modeled.
- **Fixed Seed & Single Split:** Evaluations use deterministic temporal or stratified holdouts without cross-validation fold variance.
- **Catalog Capping:** Product candidate generation is restricted to an 8,000 item budget.
- **Sample Constraints:** News modeling uses the MIND-small sample rather than the full production scale corpus.

## Citations

- **Upstream Project:**

- **MovieLens 1M:**
  > Harper, F.M. and Konstan, J.A. (2015). The MovieLens Datasets: History and Context. ACM Transactions on Interactive Intelligent Systems (TiiS), 5(4), Article 19. https://doi.org/10.1145/2827872
- **Amazon Review Data:**
  > R. He, J. McAuley. (2016). Upselling and Cross-selling: Modeling Item Relationships with Recommendation Networks. Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '16), 865-874. https://doi.org/10.1145/2939672.2939747
  > J. McAuley, C. Targett, J. Shi, A. van den Hengel. (2015). Image-based Recommendations on Styles and Substitutes. Proceedings of the 38th International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR '15), 43-52. https://doi.org/10.1145/2766462.2767755
- **MIND Dataset:**
  > Wu, F., Qiao, Y., Chen, J.-H., Wu, C., Qi, T., Lian, J., Liu, D., Xie, X., Gao, J., Wu, W., & Zhou, M. (2020). MIND: A Large-scale Dataset for News Recommendation. Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics (ACL), 3597-3606. https://aclanthology.org/2020.acl-main.331/

## License & Notices

This project is licensed under the [MIT License](LICENSE) for educational and non-commercial use.

Derived reference code in `backend/discovery/` retains its original [MIT License](backend/discovery/LICENSE) from upstream contributors. See [`backend/discovery/NOTICE.md`](backend/discovery/NOTICE.md) for adaptation history.
