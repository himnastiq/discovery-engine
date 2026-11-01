# Datasets

## MovieLens

- **Provider:** GroupLens Research, Department of Computer Science and Engineering, University of Minnesota
- **URL:** https://grouplens.org/datasets/movielens/
- **Variants used:**
  - **MovieLens 100K (`ml-100k`):** 100,000 ratings (scale 1–5) from 943 users across 1,682 movies; each user has rated at least 20 movies; released 1998. Used for `--fast` development mode and unit/integration tests.
  - **MovieLens 1M (`ml-1m`):** 1,000,209 ratings (scale 1–5) from 6,040 users across 3,706 movies; released 2003. Used for final benchmark results, hyperparameter selection, and production artifacts.
- **License:** Research and educational use only; non-commercial.
- **Citation:**
  > Harper, F.M. and Konstan, J.A. (2015). The MovieLens Datasets: History and Context. ACM Transactions on Interactive Intelligent Systems (TiiS), 5(4), Article 19. https://doi.org/10.1145/2827872
- **Terms:**
  - The University of Minnesota and its researchers provide the data without warranty of correctness or fitness for any purpose.
  - Users may not redistribute or make available any portion of the dataset without express permission.
  - Commercial use is strictly prohibited.
  - GroupLens and the ACM reference above must be acknowledged and cited in all publications, reports, or demo presentations.
- **Data location:** `data/raw/movielens/` (contains `ml-100k/` and `ml-1m/`).
- **Files per variant:**
  - `ml-100k/`: `u.data` (tab-separated: user id, item id, rating, timestamp), `u.item` (pipe-separated: movie id, title with year, release date, IMDb URL, 19 genre flags).
  - `ml-1m/`: `ratings.dat` (`::`-separated: UserID, MovieID, Rating, Timestamp), `movies.dat` (`::`-separated: MovieID, Title with year, Genres separated by `|`).

## Amazon Reviews
 
- **Provider:** Stanford SNAP / UCSD (Julian McAuley)
- **URL:** https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/ / http://snap.stanford.edu/data/amazon/productGraph/
- **Variants used:**
  - **Video Games (`video_games`):** 231,780 reviews across 24,309 users and 50,256 items (5-core subset). Contains gaming accessories, consoles, PC/console titles, and peripherals with rich item metadata (title, price, brand, image URL, categories). Used as standard production variant.
  - **Musical Instruments (`instruments`):** 10,261 reviews across 1,429 users and 900 items (5-core subset). Lightweight dataset with complete item metadata used for fast developer mode (`--fast`) and CI regression testing.
- **License:** Non-commercial academic research and educational use only.
- **Citation:**
  > R. He, J. McAuley. (2016). Upselling and Cross-selling: Modeling Item Relationships with Recommendation Networks. Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '16), 865–874. https://doi.org/10.1145/2939672.2939747
  > J. McAuley, C. Targett, J. Shi, A. van den Hengel. (2015). Image-based Recommendations on Styles and Substitutes. Proceedings of the 38th International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR '15), 43–52. https://doi.org/10.1145/2766462.2767755
- **Terms:**
  - Provided strictly for research and academic experimentation.
  - Commercial use and redistribution of raw data files without attribution are prohibited.
  - Citations to the SIGKDD 2016 and SIGIR 2015 papers above must be retained.
- **Data location:** `data/raw/amazon/` (contains `video_games/` and `instruments/`).
- **Files per variant:**
  - `reviews_<category>_5.json.gz`: JSON-lines gzip archive containing `reviewerID`, `asin`, `overall`, `unixReviewTime`, and review summary.
  - `meta_<category>.json.gz`: JSON-lines gzip archive containing `asin`, `title`, `price`, `imUrl`, `brand`, and `categories`.

## MIND (Microsoft News Dataset)

- **Provider:** Microsoft Research
- **URL:** https://msnews.github.io/
- **Variant used:** MIND-small (`small`, train + dev splits)
- **License:** Microsoft Research License Agreement (MSR-LA for Data, research and educational use only)
- **Citation:**
  > Wu, F., Qiao, Y., Chen, J.-H., Wu, C., Qi, T., Lian, J., Liu, D., Xie, X., Gao, J., Wu, W., & Zhou, M. (2020). MIND: A Large-scale Dataset for News Recommendation. Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics (ACL), 3597–3606. https://aclanthology.org/2020.acl-main.331/
- **Terms:**
  - Intended strictly for non-commercial academic research and benchmarking.
  - Direct anonymous download from legacy Azure Blob Storage is restricted by Microsoft.
  - Dataset requires agreeing to Microsoft Research license terms via Hugging Face (`yjw1029/MIND`) or Kaggle (`swiftQuiet/mind-microsoft-news-dataset`).
  - Redistribution of raw news content is prohibited.
- **Data location:** `data/raw/mind/` (contains `train/` and `dev/` subfolders).
- **Files per split:**
  - `news.tsv`: Tab-separated 8-column table without header:
    `[NewsID, Category, SubCategory, Title, Abstract, URL, TitleEntities, AbstractEntities]`.
  - `behaviors.tsv`: Tab-separated 5-column table without header:
    `[ImpressionID, UserID, Time, History, Impressions]`
    where `History` contains space-separated clicked news IDs and `Impressions` contains candidate news IDs with click labels `NewsID-0` or `NewsID-1`.

### Synthetic Offline Fixture (not MIND)

- **Purpose:** Enables end-to-end testing, invariant verification (R1–R6), and architectural demonstration without requiring external network connectivity or manual dataset placement.
- **Location:** `backend/tests/fixtures/mind/` (contains synthetic `train/` and `dev/` splits with `news.tsv` and `behaviors.tsv`).
- **Generation Method:**
  - **Articles (`news.tsv`):** Curated 15 synthetic news items spanning finance, technology, sports, and lifestyle categories with distinct titles, abstracts, subcategories, and Wikipedia entity IDs matching the official MIND 8-column schema.
  - **Behaviors (`behaviors.tsv`):** Synthesized user impression sessions with timestamps, user IDs, interaction history lists, and impression candidates (1 positive click, 4 unclicked negative impressions per session). Timestamps are ordered chronologically to enforce the R2 temporal split invariant ($t_{max}^{train} \le t_{min}^{test}$).
- **Provenance & Quality Notice:** Artifacts in `artifacts/articles/` produced from this data are labelled `"SYNTHETIC FIXTURE (not MIND)"`. **Results evaluated on this fixture are not evidence of real-world recommendation quality.**
- **Production Switch:** When genuine MIND-small dataset files are placed in `data/raw/mind/train/` and `data/raw/mind/dev/`, running `cd backend && python -m engine.train --type articles` (or `make train TYPE=articles`) automatically trains on real MIND data.

---

## Redistribution Audit

Per Phase 11 Task P11.3 specification, every tracked repository asset potentially containing dataset-derived content has been formally audited against dataset license terms:

| Tracked Asset / File Pattern | Content Classification | Basis for Inclusion / Legal Compliance |
|---|---|---|
| `backend/tests/fixtures/artifacts_mini/movies/*` | **100% Synthetic** | Auto-generated mock tables via `scripts/make_mini_artifacts.py`. Zero real MovieLens rows or user IDs. |
| `backend/tests/fixtures/artifacts_mini/products/*` | **100% Synthetic** | Auto-generated mock tables via `scripts/make_mini_artifacts.py`. Zero real Amazon review texts or ASINs. |
| `backend/tests/fixtures/artifacts_mini/articles/*` | **100% Synthetic** | Auto-generated mock tables via `scripts/make_mini_artifacts.py`. Zero real MSN article rows or clicks. |
| `backend/tests/fixtures/mind/train/*` | **100% Synthetic** | Hand-authored mock news articles (15 items) and synthesized impression logs. Zero real Microsoft News text. |
| `backend/tests/fixtures/mind/dev/*` | **100% Synthetic** | Hand-authored mock news articles and synthesized impression logs. Zero real Microsoft News text. |
| `backend/tests/fixtures/golden_movies_100k.json` | **Aggregate Statistics** | Offline validation metric summaries (NDCG, Recall, MAP) computed on ml-100k; contains no raw records or PII. |
| `docs/figures/*.png` | **Aggregate Visualizations** | Plot charts depicting offline metric curves and CI whiskers. Zero raw dataset rows exposed. |
| `docs/figures/architecture.svg` | **Original Architecture** | Vector diagram illustrating system components. Zero dataset content. |
| `docs/screenshots/*.png` | **UI Showcase** | Captured browser views of the interactive dashboard. |
| `data/raw/*` | **Not Tracked** | Completely gitignored. Raw datasets are never committed to git. |

**Audit Conclusion:** Zero raw or copyrighted dataset records are redistributed in the repository. All committed test fixtures are 100% synthetic.

---

## License Terms Re-Check

The terms and access conditions for all three external dataset providers were actively re-checked on **2026-10-31**:

1. **MovieLens (GroupLens Research):**
   - **URL Checked:** https://grouplens.org/datasets/movielens/
   - **Verification Date:** 2026-10-31
   - **Status:** Active. License permits non-commercial research and educational use. Redistribution prohibited. Attribution required and satisfied.
2. **Amazon Reviews (UCSD / Julian McAuley):**
   - **URL Checked:** https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/
   - **Verification Date:** 2026-10-31
   - **Status:** Active. License permits non-commercial academic research. Redistribution prohibited without attribution. Attribution required and satisfied.
3. **Microsoft News Dataset (MIND):**
   - **URL Checked:** https://msnews.github.io/
   - **Verification Date:** 2026-10-31
   - **Status:** Active. MSR-LA for Data restricts usage to non-commercial academic research. Direct blob download deprecated; access instructions via Hugging Face documented in `docs/DATASETS.md`. Attribution required and satisfied.

---

## General Notes

- Raw datasets are **not committed** to the repository (listed in `.gitignore`).
- Use `make data` or `python backend/scripts/fetch_data.py` to download.
- If automatic download fails, `fetch_data.py` prints manual download instructions.

---

## Third-Party Provider Data Disclosure (Discovery Assistant Chatbot)

When the optional Discovery Assistant chatbot is enabled (`CHAT_ENABLED=true`), natural-language recommendation inquiries are processed via the Google Gemini API (`gemini-2.5-flash`). To safeguard privacy and adhere strictly to dataset research licenses:
- **Data Transmitted:** Non-sensitive aggregate category affinities and shares (e.g. Action 40%, Sci-Fi 30%), titles and categories of candidate items generated by the engine's offline models, the last few interacted item titles, and user chat queries.
- **Data NOT Transmitted:** Raw database user IDs, personal identifiers (PII), interaction ratings matrices, raw review texts, and full news article bodies are never transmitted.
- **Provider Data-Use Terms:** Under the Google Gen AI Developer Terms of Service (Free Tier), prompts and responses may be processed by Google to improve products. Paid tier configurations (e.g., Google Cloud Vertex AI) do not retain customer data for model training.
