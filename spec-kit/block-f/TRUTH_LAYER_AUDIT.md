# Block F V2.0 — Truth-Layer Audit

> Status of every Block F dependency in the current codebase as of 2026-05-13.
> EXISTS = production-ready and reusable as-is. PARTIAL = present but needs
> extension/migration. MISSING = no code today.

---

## Audit method

Direct grep against `app/db/models.py`, `app/workers/tasks/ai_generation.py`,
`app/api/v1/listings.py`, `app/api/v1/buyer.py`, and frontend route maps.
Cross-checked against Block D's shipped surface so F's dependency on
Block D services is grounded in the production state, not memory.

All path/line references are absolute facts from the current `dev`
branch (HEAD: commit `752e369`, migration HEAD: `prn_autopost`).

---

## 1. F1 — AI generation + two-step publish

### Already exists

- **Worker**: `backend/app/workers/tasks/ai_generation.py` (300 LOC).
  - `_build_prompt(listing)` at line 79 — assembles structured params +
    raw_text block.
  - `_call_openai(prompt)` at line 146 — single OpenAI call with
    `model="gpt-4o-mini"`.
  - `_template_fallback(listing, lang)` at line 106 — used when
    OPENAI_API_KEY missing or generation fails.
  - `generate_listing_description` Celery task at line 197 with
    `bind=True, max_retries=3, default_retry_delay=60`.
  - On success: writes all three `ai_description_*` columns, flips
    status to ACTIVE, calls `_notify_sellers_after_generation` (A4
    hook) and `_enqueue_autopost` (D4 hook).
- **Listing columns**:
  - `Listing.raw_text` at `db/models.py:532`
  - `Listing.ai_description_ru / _uz / _uz_cyrl` at lines 535-537
  - `Listing.ai_generation_attempted_at` at line 540
- **Status enum**: `ListingStatus.PENDING_GENERATION` (line 82) and
  `GENERATION_FAILED` (line 83) already in `listingstatus`.
- **Source-text retention** (parser side):
  - `TelegramListing.raw_text` at line 1757
  - `OLXListing.raw_text` at line 1876
- **Block D hook integration** — `ai_generation.py:_enqueue_autopost`
  (line 274) already fires for PENDING_GENERATION → ACTIVE. F1's
  manual regeneration will reuse this verbatim. D4's
  `bot_channel_posts.uq_bot_channel_posts_listing_channel` unique
  constraint provides idempotency.

### Missing

- **`ListingStatus.DRAFT` enum value**. Required for Stage 1's commit.
  Added via `ALTER TYPE listingstatus ADD VALUE 'draft'` inside
  `autocommit_block()` (precedent: Block A PR-G, Block C
  `prj_wallet_billing`).
- **`Listing.last_ai_param_snapshot`** — JSONB column to detect
  param drift between Stage 1 and Stage 2.
- **Frontend two-step UX**. Current `seller/pages/create-listing/`
  is a single page. F1 splits into Stage 1 / Stage 2.
- **`POST /listings/draft`**, **`GET /listings/{id}/draft-preview`**,
  **`POST /listings/{id}/regenerate`**, **`GET /listings/{id}/source-text`**
  endpoints.
- **DRAFT→ACTIVE PATCH guard**: existing PATCH on `/listings/{id}`
  does not validate `ai_description_ru IS NOT NULL`.
- **B2B "Показать исходный текст" expander** on Master-record detail.
- **`purge_abandoned_drafts` Celery beat task** — clean DRAFT listings
  older than 7 days.

### Partial

- **PII scrubbing**. Worker reads `raw_text` directly into the prompt
  with no phone/email redaction. F1 must add a scrubber pass before
  `_build_prompt` constructs its raw_text block.
- **`raw_text` truncation**. Worker passes full raw_text to the LLM
  with no length cap. At ~5000 chars from some Telegram posts this
  burns tokens unpredictably. F1 caps at 1500 chars (head 700 +
  " […] " + tail 700).
- **Prompt source**. Currently hard-coded in `_build_prompt`. F5
  moves prompts to a DB table; F1 reads via `prompt_registry`.

---

## 2. F2 — Synonym matcher

### Already exists

- **`core/regions.py`** dictionary pattern (used by D5 query parser
  for districts). Same pattern applies to F2 — small in-memory
  dict-based lookup, no fuzzy library, deletable in one file.
- **Frontend FSD pattern for admin pages** —
  `modules/admin/pages/sources/` (Block A8) is the cleanest
  precedent for an admin CRUD surface.

### Missing

- **`synonym_entries` table** with columns: `parameter_key`,
  `parameter_value`, `surface_form`, `language`, `polarity`.
- **`services/synonym_matcher.py`** — pure function
  `match_text_to_params(text, lang, current_params)` returning
  matches with `add` / `contradict` / `ok` outcomes.
- **`POST /listings/{id}/analyse-text`** endpoint — debounced
  call site on Stage 2.
- **Hint UI** on Stage 2 — non-blocking suggestion cards.
- **Admin CRUD** for synonym entries (`modules/admin/pages/synonyms/`).
- **Negation heuristic** — scan 5 tokens preceding the surface
  form for `["не", "без", "no", "yo'q"]`.

---

## 3. F3 — SEO infrastructure

### Already exists

- **FastAPI app** at `backend/app/main.py`. Currently mounts
  `/uploads` static and `/api/v1` router. Has Jinja2 capability via
  `fastapi.templating` (not yet imported — single-line install).
- **D3a `services/deeplink.build_listing_link`** — the public web
  pages will mint these for "Открыть в UcharMarket" CTA.
- **`Listing.ai_description_*`** columns to render the indexable
  content.
- **`core/regions.py:_DISTRICT_ALIASES`** — bilingual district
  spellings power slug generation and 301 redirects.
- **Frontend Vite SPA at `frontend/`** — stays as-is for TWA.

### Missing

- **`api/v1/seo.py` router** mounted at root (not under `/api/v1`)
  — Jinja2-rendered HTML routes.
- **`services/seo_meta.py`** — title / description / og / JSON-LD
  builders.
- **`services/sitemap.py`** — sitemap-index + per-language sitemaps,
  paginated 50k urls/file (Google limit).
- **`templates/seo/`** directory — `listing.html`, `filter.html`,
  `gone.html`, `empty.html`, `sitemap_index.xml`,
  `sitemap_listings.xml`, `sitemap_filters.xml`, `robots.txt`.
- **Read-only Postgres pool** dedicated to SEO routes (crawler
  bursts must not starve the API pool).
- **`F3_PUBLIC_WEB_HOST` env var** and DNS for `ucharmarket.uz`.
- **Reverse-proxy config** routing `/{lang}/...`, `/sitemap*.xml`,
  `/robots.txt` to FastAPI; everything else to the Vite SPA bundle.
- **User-Agent based TWA redirect**: SSR routes that detect
  TelegramWebApp / tdesktop bounce to deep link.

### Partial

- **`Listing.deleted_at` + `status`** drive 410 Gone responses —
  fields exist, but SEO router needs the resolution logic.
- **Slug generation**: title + UUID-prefix combination needs a
  deterministic helper. Some `core/regions.py` aliases already map
  Russian district names to Latin slugs we can reuse.

---

## 4. F4 — Cabinet exports

### Already exists

- **`services/subscriptions.check_active_subscription(db, user_id, CABINET)`**
  — Block D D4 helper, the paywall gate.
- **`SubscriptionType.CABINET`** enum value.
- **`services/deeplink.build_listing_link`** — Telegram export
  template references this URL.
- **Frontend seller cabinet FSD modules** — `seller/pages/tariffs/`,
  `seller/pages/phones/`, `seller/pages/autoposting/` (Block D D4)
  are clean precedents for `seller/feature/text-export/`.
- **Seller profile edit UI** — extends easily to accept signature
  / CTA / extra hashtags.

### Missing

- **`export_templates` table** keyed by (platform, language) with
  `is_active` partial unique index.
- **`sellers.export_signature`, `export_cta`, `export_extra_hashtags`**
  columns (nullable).
- **`services/text_export.py`** — sandbox-Jinja2 renderer with
  allowlisted placeholders.
- **`api/v1/seller_exports.py`** router with GET per platform
  endpoint + settings GET/PATCH.
- **Frontend export-buttons module** + paywall modal linking to
  `/seller/tariffs` (Block C C1).
- **Admin CRUD** for export templates.

---

## 5. F5 — Quality management

### Already exists

- **Celery beat schedule infrastructure**
  (`workers/celery_app.py:beat_schedule`) — F5 adds two hourly /
  daily entries.
- **Admin Telegram notification helper**
  `bot/notifications.notify_admins_*` — used by `quality_alerts`
  thresholds.
- **`bot/translations`** trilingual loader for feedback modal copy.
- **Existing Celery `prune_*` task pattern**
  (`workers/tasks/maintenance.prune_behavioral_signals` from Block
  D D2) — F5 mirrors it for `ai_generations` retention.

### Missing

- **`ai_generations` table** with full prompt/response/duration/cost
  metadata.
- **`prompt_templates` table** with `is_active` partial unique
  index per kind.
- **`ai_generation_feedback` table**.
- **`services/prompt_registry.py`** — `get_active_prompt(kind)`,
  `record_generation(...)`.
- **`services/quality_alerts.py`** — hourly threshold checks
  (bad-feedback rate, duration p95, daily cost, OpenAI 5xx rate).
- **`workers/tasks/maintenance.prune_ai_generations`** — daily,
  90-day retention.
- **`api/v1/ai_feedback.py`** — POST endpoint.
- **`api/v1/admin_ai.py`** — generation review, feedback queue,
  prompt CRUD/activate.
- **Frontend feedback button** on Stage 2 and Master-record detail.
- **Frontend admin AI-quality page**.

---

## Cross-cutting: Block D consumption points

The Block F surface consumes — never modifies — these stable Block D
interfaces:

| Block D asset | F's consumer |
|---|---|
| `services/subscriptions.check_active_subscription(db, user_id, CABINET)` | F4 paywall on every `/seller/exports/*` endpoint |
| `services/deeplink.build_listing_link(listing_id)` | F3 "Открыть в UcharMarket" CTA + F4 Telegram-export template |
| `services/deeplink.build_filter_link(filters, db, user_id)` | F3 filter-page deep links for shared landing URLs |
| `services/autopost._dispatch_autopost_for_status_change` (from `api/v1/listings.py`) | F1 regeneration bumps `listing.version`; D4 cabinet auto-shows "stale" badge |
| `services/autopost._enqueue_autopost` (from `ai_generation.py`) | F1 PENDING→ACTIVE flow already triggers this; unchanged |
| `bot/i18n.t(lang, key)` | F1 disclaimer + F4 export templates + F5 feedback modal copy |
| `BotChannelPost.uq_bot_channel_posts_listing_channel` | F1 regeneration is idempotent against D4 — no double-publish risk |
| `behavioral_signals` (D2) | F5 admin dashboards may JOIN to correlate text quality with engagement |

No Block D interface changes. No Block D migration revisited. No
Block D service refactored.

---

## Block F dependency satisfaction matrix

| ID | Description | Status |
|----|---|---|
| **F1** | `ai_description_{ru,uz,uz_cyrl}` columns | EXISTS |
| F1 | AI generation Celery worker | EXISTS |
| F1 | `PENDING_GENERATION`/`GENERATION_FAILED` enum values | EXISTS |
| F1 | `DRAFT` enum value | MISSING — added in `pro_block_f_ai_foundation` |
| F1 | `last_ai_param_snapshot` column | MISSING |
| F1 | Stage-1 / Stage-2 frontend split | MISSING |
| F1 | PATCH DRAFT→ACTIVE guard | MISSING |
| F1 | PII scrubbing on `raw_text` | PARTIAL — worker reads raw_text without redaction |
| F1 | raw_text truncation | PARTIAL — no length cap |
| F1 | B2B "show original" expander | MISSING |
| F1 | `purge_abandoned_drafts` Celery beat | MISSING |
| **F2** | `synonym_entries` table | MISSING |
| F2 | `services/synonym_matcher.py` | MISSING |
| F2 | `POST /listings/{id}/analyse-text` | MISSING |
| F2 | Hint UI on Stage 2 | MISSING |
| F2 | Admin synonym CRUD | MISSING |
| **F3** | SSR router + Jinja2 templates | MISSING |
| F3 | `services/seo_meta.py` | MISSING |
| F3 | `services/sitemap.py` | MISSING |
| F3 | Read-only DB pool | MISSING |
| F3 | `ucharmarket.uz` DNS + cert | MISSING — ops task |
| F3 | Reverse-proxy routing | MISSING — ops task |
| F3 | TWA User-Agent bounce | MISSING |
| **F4** | Subscription gate helper | EXISTS (D4) |
| F4 | `export_templates` table | MISSING |
| F4 | `sellers.export_*` columns | MISSING |
| F4 | `services/text_export.py` | MISSING |
| F4 | `api/v1/seller_exports.py` router | MISSING |
| F4 | Frontend export module | MISSING |
| F4 | Admin template CRUD | MISSING |
| **F5** | `ai_generations` table | MISSING |
| F5 | `prompt_templates` table | MISSING |
| F5 | `ai_generation_feedback` table | MISSING |
| F5 | `services/prompt_registry.py` | MISSING |
| F5 | `services/quality_alerts.py` | MISSING |
| F5 | `workers/tasks/maintenance.prune_ai_generations` | MISSING |
| F5 | `api/v1/ai_feedback.py` | MISSING |
| F5 | `api/v1/admin_ai.py` | MISSING |
| F5 | Feedback button (frontend) | MISSING |
| F5 | Admin AI-quality page | MISSING |

---

## Hard constraints discovered (not in spec)

1. **`ALTER TYPE listingstatus ADD VALUE` is non-reversible in Postgres.**
   Adding `'draft'` is permanent; downgrading leaves a harmless
   residual value. Same precedent as Block A V2.0 enum additions —
   no operational concern.
2. **OpenAI cost at burst-import scale.** Parser can capture 500
   listings in a single run × 3 locales = 1500 LLM calls. Worker
   concurrency cap (10) + retry backoff prevent quota exhaustion.
3. **Telegram's 1024-char caption limit** applies to D4 channel
   posts that consume F1's AI text. Existing D4 truncation logic
   (`_AI_TEXT_MAX = 700` in `services/autopost.py`) handles this;
   F1 changes nothing about that path.
4. **Google's 50k URLs per sitemap** — paginated index required at
   F3 launch volume. `services/sitemap.py` builds index +
   per-language files.
5. **Vite SPA build pipeline does not pre-render.** F3 needs SSR
   on a separate front door (FastAPI + Jinja2). The SPA bundle
   continues to serve the TWA.

---

## Confidence

- §1 (F1) — High. Direct code citations against current backend.
- §2 (F2) — High on missing surfaces; medium on exact synonym
  dictionary curation (operational artefact, refined post-launch).
- §3 (F3) — High on what's missing; medium on the reverse-proxy
  config detail (DevOps-side).
- §4 (F4) — High. Block D D4's `services/subscriptions` is the
  primary reuse and is verified stable.
- §5 (F5) — High. Pattern is parallel to Block D D2
  `behavioral_signals` retention.
