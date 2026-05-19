# Block F — Implementation Roadmap

> Turn-by-turn execution blueprint with zero remaining architectural
> ambiguity. After the user approves [DECISION_MATRIX.md](DECISION_MATRIX.md)
> (already frozen), development starts the same day.
>
> **Audit ground truth**: [../TRUTH_LAYER_AUDIT.md](../TRUTH_LAYER_AUDIT.md)
> **Status snapshot**: [../READINESS_REPORT.md](../READINESS_REPORT.md)
> **Decisions frozen**: [DECISION_MATRIX.md](DECISION_MATRIX.md)

---

## Table of contents

1. [Scope & 30-second summary](#scope--30-second-summary)
2. [Reuse inventory — what already exists](#reuse-inventory--what-already-exists)
3. [New infrastructure inventory](#new-infrastructure-inventory)
4. [Migrations — exact DDL](#migrations--exact-ddl)
5. [API contracts — every new endpoint](#api-contracts--every-new-endpoint)
6. [Telegram + OpenAI constraints — hard limits](#telegram--openai-constraints--hard-limits)
7. [Architecture impact — code touch map](#architecture-impact--code-touch-map)
8. [PR sequence with critical path](#pr-sequence-with-critical-path)
9. [Per-task deep dives (F1–F5)](#per-task-deep-dives)
10. [Risk register](#risk-register)
11. [What can ship today vs deferred](#what-can-ship-today-vs-deferred)

---

## Scope & 30-second summary

Block F = AI-generated descriptions as platform infrastructure + the
SEO foundation that converts that content into organic search traffic.

| ID | Concrete change | Net new LOC (est) | Calendar days |
|----|---|---|---|
| F1 | Two-step DRAFT publish + AI-text-on-every-listing in 3 locales | ~1100 | 5 |
| F2 | Synonym matcher + non-blocking editor hints + admin CRUD | ~600 | 3 |
| F3 | SSR routes + sitemap + schema.org + hreflang + canonical | ~1500 | 10 |
| F4 | Per-platform formatted exports gated by Cabinet subscription | ~900 | 4 |
| F5 | Generation logging + feedback + admin review + prompt versioning | ~800 | 4 (split 1.5 + 2.5) |

Total **~26 calendar days serial**, ~17 with parallel F2/F4/F3 after
F1 ships. Three Alembic migrations. Eleven new service modules. ~22
new HTTP endpoints. Five new frontend modules.

The work is **not** evenly distributed: F3 alone is ~40% of effort.
PR-F1 is the user-visible win that all other F tasks build on; ship it
first.

---

## Reuse inventory — what already exists

Verified directly against source (see TRUTH_LAYER_AUDIT for citations).
**Do not rebuild these; import or extend.**

### Backend services
| Asset | Path | Reused by |
|---|---|---|
| `ai_generation.py` Celery worker | `backend/app/workers/tasks/ai_generation.py` | F1 (extended); F5 (logging hook) |
| `Listing.ai_description_{ru,uz,uz_cyrl}` | `db/models.py:535-537` | F1, F3, F4 |
| `Listing.raw_text` | `db/models.py:532` | F1 (B2B expander) |
| `Listing.ai_generation_attempted_at` | `db/models.py:540` | F1 |
| `ListingStatus.PENDING_GENERATION` / `GENERATION_FAILED` | `db/models.py:82-83` | F1 |
| `TelegramListing.raw_text`, `OLXListing.raw_text` | `db/models.py:1757, 1876` | F1 source-text retention |
| `services.subscriptions.check_active_subscription` | (Block D D4) | F4 paywall |
| `services.deeplink.build_listing_link` | (Block D D3) | F3 CTA, F4 Telegram template |
| `services.deeplink.build_filter_link` | (Block D D3) | F3 shareable filter pages |
| `services.autopost._enqueue_autopost` | (Block D D4) | F1 PENDING→ACTIVE hook |
| `services.autopost._dispatch_autopost_for_status_change` | (Block D D4) | F1 regeneration → D4 stale-badge |
| `bot/i18n.t` | (Block D D1) | F1 disclaimer, F4 templates, F5 feedback copy |
| Celery beat schedule infra | `workers/celery_app.py` | F1 (`purge_abandoned_drafts`), F5 (`prune_ai_generations`, `check_quality_thresholds`) |
| `workers/tasks/maintenance.prune_behavioral_signals` pattern | (Block D D2) | F5 `prune_ai_generations` (verbatim pattern) |
| `bot/notifications.notify_admins_*` | (Block A) | F5 quality alerts |
| `core/regions._DISTRICT_ALIASES` | `core/regions.py:263-334` | F3 slug generation |

### Frontend modules
| Asset | Path | Reused by |
|---|---|---|
| FSD module pattern (`tariffs/`, `phones/`, `autoposting/`) | `modules/seller/pages/*` | F4 `text-export/`, F5 `ai-quality/`, F2 admin pages |
| Admin FSD pattern | `modules/admin/pages/sources/` (Block A8) | F2 synonym CRUD, F4 export-template CRUD, F5 AI review |
| Effector store + effects + connections + lib pattern | `modules/seller/pages/autoposting/` | F1 Stage1/Stage2 store; F4 export-state store |

### Existing patterns to mirror
| Pattern | Source | Apply to |
|---|---|---|
| Alembic enum-add inside `autocommit_block` | `alembic/versions/20260502_prj_wallet_billing.py` | `pro_block_f_ai_foundation` adds `'draft'` |
| Partial unique index on `is_active` | Block D D4 `bot_channel_posts.uq_*` | `prompt_templates` per-kind active enforcement |
| 90/180-day pruning Celery beat | Block D D2 `prune_behavioral_signals` | F5 `prune_ai_generations` |
| Domain-service + Telegram-adapter split | Block D D4 `autopost.py` + `channel_publisher.py` | F3 `seo_meta.py` (domain) + Jinja2 templates (transport) |
| FSD effects-stores-connections-lib | Block D D4 `seller/pages/autoposting/` | F1 `create-listing/Stage1.tsx + Stage2.tsx`, F4 `text-export/` |

---

## New infrastructure inventory

### New backend modules (services)
| File | Purpose | Used by |
|---|---|---|
| `app/services/prompt_registry.py` | Read active prompt; record generation log | F1, F5 |
| `app/services/synonym_matcher.py` | Pure-function keyword + negation matching | F2 |
| `app/services/text_export.py` | Sandbox-Jinja2 platform renderer | F4 |
| `app/services/seo_meta.py` | Title / description / og / JSON-LD builders | F3 |
| `app/services/sitemap.py` | Sitemap-index + per-language paginated | F3 |
| `app/services/quality_alerts.py` | Threshold checks for F5 alerts | F5 (Celery beat) |
| `app/workers/tasks/maintenance.prune_ai_generations` | 90-day retention | F5 (Celery beat) |
| `app/workers/tasks/maintenance.purge_abandoned_drafts` | 7-day DRAFT TTL | F1 (Celery beat) |
| `app/templates/seo/*.html` + `*.xml` | Jinja2 templates | F3 |

### Backend new endpoints (HTTP)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/v1/listings/draft` | bearer (seller) | F1 Stage 1 commit |
| GET | `/api/v1/listings/{id}/draft-preview` | bearer (owner) | F1 Stage 2 poll |
| POST | `/api/v1/listings/{id}/regenerate` | bearer (owner) | F1 manual re-gen |
| GET | `/api/v1/listings/{id}/source-text` | bearer (owner, B2B) | F1 raw_text expander |
| POST | `/api/v1/listings/{id}/analyse-text` | bearer (owner) | F2 hint computation |
| GET | `/{lang}/listing/{id}/{slug}` | none | F3 SSR HTML |
| GET | `/{lang}/tashkent/{district}` | none | F3 district landing |
| GET | `/{lang}/{deal}/{type}` / variants | none | F3 filter landing pages |
| GET | `/sitemap.xml` + `/sitemap-{lang}-*.xml` | none | F3 sitemap |
| GET | `/robots.txt` | none | F3 robots |
| GET | `/api/v1/seller/exports/{listing_id}/{platform}` | bearer + Cabinet sub | F4 export |
| GET / PATCH | `/api/v1/seller/exports/settings` | bearer | F4 signature/CTA/hashtags |
| POST | `/api/v1/ai-feedback` | bearer | F5 feedback |
| GET / POST / PATCH | `/api/v1/admin/ai/*` (8 endpoints) | admin | F5 admin review + prompt CRUD |
| GET / POST / DELETE | `/api/v1/admin/synonyms` | admin | F2 dictionary CRUD |
| GET / PATCH | `/api/v1/admin/export-templates/*` | admin | F4 template CRUD |

### New Celery beat tasks
| Task | Schedule | Module |
|---|---|---|
| `purge_abandoned_drafts` | daily 05:00 | F1 |
| `prune_ai_generations` | daily 04:45 | F5 |
| `check_quality_thresholds` | hourly :15 | F5 |
| `rebuild_sitemap` | every 15 min | F3 (or on-demand on listing PATCH) |

### New frontend modules
| Path | Purpose | PR |
|---|---|---|
| `modules/seller/pages/create-listing/ui/page/Stage1.tsx` (rename existing) + `Stage2.tsx` (new) | F1 two-step flow | F1 |
| `modules/seller/feature/text-export/` | F4 export buttons + paywall + settings | F4 |
| `modules/seller/feature/ai-feedback/` | F5 "не нравится" button + modal | F5b |
| `modules/admin/pages/ai-quality/` | F5 admin review surface | F5b |
| `modules/admin/pages/synonyms/` | F2 dictionary CRUD | F2 |
| `modules/admin/pages/export-templates/` | F4 template body editor | F4 |

---

## Migrations — exact DDL

Three Alembic revisions, in order. File naming pattern matches Block D
(`YYYYMMDD_pr<letter>_<short_name>.py`); enum additions wrapped in
`autocommit_block` per Block A PR-G precedent.

### Migration 1 — `pro_block_f_ai_foundation` (PR-F5a)

```python
"""pro_block_f_ai_foundation — F1 + F5 infrastructure"""

revision = "pro_block_f_ai_foundation"
down_revision = "prn_autopost"

def upgrade():
    # ── (1) DRAFT enum value — autocommit so available to later DDL
    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumlabel = 'draft'
                      AND enumtypid = 'listingstatus'::regtype
                ) THEN
                    ALTER TYPE listingstatus ADD VALUE 'draft';
                END IF;
            END $$;
            """
        )

    # ── (2) Listing snapshot column
    op.execute(
        """
        ALTER TABLE listings
            ADD COLUMN IF NOT EXISTS last_ai_param_snapshot JSONB;
        """
    )

    # ── (3) prompt_templates
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            kind VARCHAR(48) NOT NULL,
            version INTEGER NOT NULL,
            body TEXT NOT NULL,
            model_hint VARCHAR(64) NULL,
            is_active BOOLEAN NOT NULL DEFAULT false,
            notes TEXT NULL,
            created_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_prompt_active_per_kind
            ON prompt_templates (kind) WHERE is_active;
        CREATE INDEX IF NOT EXISTS idx_prompt_kind_version
            ON prompt_templates (kind, version DESC);
        """
    )

    # ── (4) ai_generations
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_generations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            listing_id UUID NULL REFERENCES listings(id) ON DELETE SET NULL,
            prompt_template_id UUID NULL REFERENCES prompt_templates(id) ON DELETE SET NULL,
            model VARCHAR(64) NOT NULL,
            prompt_text TEXT NOT NULL,
            response_text TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            input_tokens INTEGER NULL,
            output_tokens INTEGER NULL,
            cost_usd_micros BIGINT NULL,
            triggered_by VARCHAR(32) NOT NULL,
            outcome VARCHAR(32) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_ai_gen_listing_created
            ON ai_generations (listing_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_ai_gen_outcome_created
            ON ai_generations (outcome, created_at DESC) WHERE outcome != 'ok';
        """
    )

    # ── (5) ai_generation_feedback
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_generation_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            generation_id UUID NULL REFERENCES ai_generations(id) ON DELETE SET NULL,
            listing_id UUID NULL REFERENCES listings(id) ON DELETE SET NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            category VARCHAR(32) NOT NULL,
            comment TEXT NULL,
            handled BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_ai_fb_handled_created
            ON ai_generation_feedback (handled, created_at DESC);
        """
    )

def downgrade():
    op.execute("DROP TABLE IF EXISTS ai_generation_feedback CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_generations CASCADE;")
    op.execute("DROP TABLE IF EXISTS prompt_templates CASCADE;")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS last_ai_param_snapshot;")
    # NOTE: enum value 'draft' is non-reversible in Postgres; harmless residual.
```

### Migration 2 — `prp_block_f_synonyms` (PR-F2)

```python
"""prp_block_f_synonyms — F2 dictionary table"""

revision = "prp_block_f_synonyms"
down_revision = "pro_block_f_ai_foundation"

def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS synonym_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            parameter_key VARCHAR(64) NOT NULL,
            parameter_value VARCHAR(64) NULL,
            surface_form VARCHAR(128) NOT NULL,
            language VARCHAR(8) NOT NULL,
            polarity VARCHAR(8) NOT NULL DEFAULT 'positive',
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_synonym_param_lang
            ON synonym_entries (parameter_key, language);
        CREATE INDEX IF NOT EXISTS idx_synonym_surface_lang
            ON synonym_entries (surface_form, language);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_synonym_uniq
            ON synonym_entries (parameter_key, COALESCE(parameter_value, ''),
                                surface_form, language);
        """
    )

def downgrade():
    op.execute("DROP TABLE IF EXISTS synonym_entries CASCADE;")
```

### Migration 3 — `prq_block_f_exports` (PR-F4)

```python
"""prq_block_f_exports — F4 export-template table + seller columns"""

revision = "prq_block_f_exports"
down_revision = "prp_block_f_synonyms"

def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS export_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            platform VARCHAR(32) NOT NULL,
            language VARCHAR(8) NOT NULL,
            template_body TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_export_template_active
            ON export_templates (platform, language) WHERE is_active;
        """
    )
    op.execute(
        """
        ALTER TABLE sellers
            ADD COLUMN IF NOT EXISTS export_signature TEXT,
            ADD COLUMN IF NOT EXISTS export_cta TEXT,
            ADD COLUMN IF NOT EXISTS export_extra_hashtags VARCHAR(500);
        """
    )

def downgrade():
    op.execute(
        """
        ALTER TABLE sellers
            DROP COLUMN IF EXISTS export_extra_hashtags,
            DROP COLUMN IF EXISTS export_cta,
            DROP COLUMN IF EXISTS export_signature;
        DROP TABLE IF EXISTS export_templates CASCADE;
        """
    )
```

---

## API contracts — every new endpoint

### F1

#### `POST /api/v1/listings/draft`
Request body: same as existing listing-create payload (params + image refs).
Response 201:
```json
{ "id": "uuid", "status": "draft" }
```

#### `GET /api/v1/listings/{id}/draft-preview`
Auth: owner only. Returns 403 if not owner.
Response 200:
```json
{
  "id": "uuid",
  "status": "draft" | "active" | "generation_failed",
  "ai_description_ru": "...",
  "ai_description_uz": "...",
  "ai_description_uz_cyrl": "...",
  "last_ai_param_snapshot": {...},
  "generation_attempted_at": "ISO timestamp"
}
```

#### `POST /api/v1/listings/{id}/regenerate`
Body: `{ "language": "ru" | "uz" | "uz_cyrl" | null }` (null = all three).
Response 202: `{ "status": "queued" }`

#### `GET /api/v1/listings/{id}/source-text`
Auth: owner + listing must be claimed/owned by current seller.
Response 200: `{ "raw_text": "...", "source": "telegram" | "olx" | null }`
404 if no raw_text or not eligible.

#### `PATCH /api/v1/listings/{id}` (existing — guard extended)
On `status: "active"` from current `draft`, returns 409 if
`ai_description_ru IS NULL`: `{ "error": "ai_generation_pending" }`.

### F2

#### `POST /api/v1/listings/{id}/analyse-text`
Body:
```json
{ "text": "...", "language": "ru" | "uz" | "uz_cyrl",
  "current_params": { "air_conditioner": true, ... } }
```
Response 200:
```json
{ "matches": [
    { "parameter_key": "air_conditioner",
      "parameter_value": null,
      "surface_form": "кондиционер",
      "action": "add" | "contradict" | "ok",
      "position": 42 }
  ]
}
```

### F3 (HTML, not JSON)

All routes return text/html, cache `public, max-age=300` for content;
sitemap routes cache `max-age=900`; robots.txt cache `max-age=3600`.

`/{lang}/listing/{id}/{slug}`:
- 200 HTML — listing detail with full meta/JSON-LD
- 301 if `slug` drifted (redirect to canonical)
- 410 Gone if `deleted_at IS NOT NULL` or status `∉ {ACTIVE, GENERATION_FAILED}`

`/{lang}/...filter pages...`: 200 HTML; 200 with `noindex,follow` if 0 results.

`/sitemap.xml`: 200 XML index pointing at per-language sitemaps.

`/robots.txt`: 200 plain text, allow `/ru/ /uz/ /uz-latn/ /sitemap*`; disallow `/api /admin /seller /uploads`.

### F4

#### `GET /api/v1/seller/exports/{listing_id}/{platform}?lang={lang}`
`platform ∈ {olx, telegram_channel, instagram, pack}`. `lang ∈ {ru, uz, uz_cyrl}`.
Response 200: `{ "text": "...", "title": "...", "truncated": false }`
Response 402: `{ "error": "subscription_required" }` for free users.
Response 422: `{ "error": "ai_text_not_ready" }` for listings missing AI text.

#### `GET /api/v1/seller/exports/settings`
Response 200: `{ "signature": "...", "cta": "...", "extra_hashtags": "..." }`

#### `PATCH /api/v1/seller/exports/settings`
Body: any subset of the three fields.
Response 200: same shape as GET.

### F5

#### `POST /api/v1/ai-feedback`
Body:
```json
{ "generation_id": "uuid",
  "listing_id": "uuid",
  "category": "grammar" | "unnatural" | "factual" | "too_long" | "too_short" | "other",
  "comment": "..." }
```
Response 201: `{ "id": "uuid" }`

#### `GET /api/v1/admin/ai/generations?date_from=&lang=&model=&outcome=&page=`
Admin auth. Returns paginated list with metadata only (no prompt body
in list view).

#### `GET /api/v1/admin/ai/generations/{id}`
Admin auth. Returns full row including prompt_text + response_text.

#### `GET /api/v1/admin/ai/feedback?handled={bool}&page=`
Admin auth. Paginated.

#### `POST /api/v1/admin/ai/feedback/{id}/handle`
Admin auth. Marks as `handled=true`.

#### `GET /api/v1/admin/ai/prompts?kind=`
Admin auth. Versions list per kind.

#### `POST /api/v1/admin/ai/prompts`
Admin auth. Body: `{ "kind": "...", "body": "...", "model_hint": "...", "notes": "..." }`. Creates new version with `is_active=false`.

#### `POST /api/v1/admin/ai/prompts/{id}/activate`
Admin auth. Atomically flips active flag (partial unique index enforces).

#### Admin synonym + export-template CRUD
Standard list/create/delete/patch. Specs identical to admin pattern
from Block A8.

---

## Telegram + OpenAI constraints — hard limits

| Constraint | Limit | Affects | Mitigation in this roadmap |
|---|---|---|---|
| Telegram caption | 1024 chars | F1 AI text consumed by D4 | D4's existing `_AI_TEXT_MAX=700` truncation; unchanged |
| Telegram sitemap | 50k urls/file | F3 sitemap | Paginated per-language; sitemap-index file |
| OpenAI rate limit | model-specific TPM/RPM | F1 worker | Celery concurrency cap 10; backoff retry |
| OpenAI single response token cap | 4096 default | F1 generation | `_call_openai` requests <= 1500 output tokens / 3 locales |
| OpenAI prompt cost | input tokens | F1 cost | `raw_text` capped at 1500 chars (head+tail); structured params kept compact |
| PostgreSQL `ALTER TYPE ... ADD VALUE` | non-reversible, non-transactional | F1 DRAFT enum | wrapped in `autocommit_block`; downgrade leaves harmless residual |
| Google sitemap freshness | minutes-to-hours crawl latency | F3 indexation | 15-minute rebuild; `lastmod` per URL |
| Google indexing limit per sitemap | 50k urls | F3 | paginated index |
| Telegram WebApp `start_param` | 64 chars | F3 deep-link CTAs via D3 | already enforced by D3 helpers |

---

## Architecture impact — code touch map

```
┌────────────────────────────────────────────────────────────────────────┐
│                    PUBLIC WEB (Google bot, mobile/desktop)             │
│                            HTML over the wire                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ FastAPI Jinja2 SSR — api/v1/seo.py mounted at root              │  │
│  │   /{lang}/listing/{id}/{slug}                                    │  │
│  │   /{lang}/tashkent/{district}                                    │  │
│  │   /{lang}/{deal}/{type}[...]                                     │  │
│  │   /sitemap*.xml /robots.txt                                      │  │
│  └─────────────────────────┬────────────────────────────────────────┘  │
└────────────────────────────┼───────────────────────────────────────────┘
                             │
                ┌────────────┴───────────────┐
                ▼                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│              DOMAIN SERVICES (transport-agnostic)                    │
│   services/prompt_registry  │  services/synonym_matcher              │
│   services/text_export      │  services/seo_meta                     │
│   services/sitemap          │  services/quality_alerts               │
│                                                                      │
│   reused from Block D (unchanged):                                   │
│   services/subscriptions    │  services/deeplink                     │
│   services/autopost         │  bot/i18n                              │
└──────────────────────────────────────────────────────────────────────┘
                ▲                            ▲
                │                            │
┌───────────────┴────────────┐   ┌───────────┴──────────────────────┐
│   FastAPI JSON API         │   │   TWA SPA (Vite, unchanged)      │
│   /api/v1/listings/draft   │   │   seller/pages/create-listing/   │
│   /api/v1/listings/{id}/   │   │     Stage1.tsx / Stage2.tsx      │
│      draft-preview /       │   │   seller/feature/text-export/    │
│      regenerate /          │   │   seller/feature/ai-feedback/    │
│      source-text /         │   │   admin/pages/ai-quality/        │
│      analyse-text          │   │   admin/pages/synonyms/          │
│   /api/v1/seller/exports/* │   │   admin/pages/export-templates/  │
│   /api/v1/ai-feedback      │   └──────────────────────────────────┘
│   /api/v1/admin/ai/*       │
│   /api/v1/admin/synonyms   │
│   /api/v1/admin/export-*   │
└────────────────────────────┘
```

---

## PR sequence with critical path

```
PR-F5a  (1.5d)  ─┐
                 │  tables ready
PR-F1   (5d)    ◀┘  reads prompts from F5a
                 │
                 ├──────┬──────┬──────┐
PR-F5b  (2.5d) ◀┤      │      │      │
PR-F2   (3d)   ─┘      │      │      │
PR-F4   (4d)   ────────┘      │      │
PR-F3   (10d)  ───────────────┘      │
                                     │
Total serial:     26d                │
Total parallel:   17d  (after F1)    │
```

**Critical path**: F5a (tables) → F1 (user flow) → parallel rest.

---

## Per-task deep dives

### F1 — AI generation + two-step publish

**Why**: every other F task depends on AI text being on every listing.
Today, manual cabinet listings start ACTIVE without AI text;
crawler-imported listings have AI text generated post-hoc. F1
unifies the flow: every listing (manual or crawler) gets AI text
generated as part of its creation, and sellers see/edit it before
publication.

**How**:
- New `Listing.status = DRAFT` for Stage 1; existing
  `PENDING_GENERATION` continues for crawler listings.
- Stage 2 polls until `ai_description_ru IS NOT NULL`, then renders
  three-tab editor with disclaimer + F2 hints + F5 feedback link.
- "Опубликовать" → PATCH to ACTIVE, validates AI text present.
- Param change between stages → banner with manual "Обновить" choice.
- Regeneration reuses existing Celery task; idempotent against D4.

**Where it integrates**:
- `app/api/v1/listings.py`: new draft endpoints + PATCH guard.
- `app/workers/tasks/ai_generation.py`: read prompt from registry +
  PII scrub + raw_text truncation + log to `ai_generations`.
- `app/workers/tasks/maintenance.py`: `purge_abandoned_drafts`.
- `app/db/models.py`: `Listing.last_ai_param_snapshot`; new
  `ListingStatus.DRAFT`.
- Frontend: `seller/pages/create-listing/ui/page/Stage1.tsx +
  Stage2.tsx`, store, polling effect.

**Reuse**:
- Existing `ai_generation.py` worker (extended, not rewritten).
- Existing `_enqueue_autopost` hook fires on PENDING/DRAFT → ACTIVE.
- Existing `Listing.raw_text` + `Listing.ai_description_*` columns.

### F2 — Synonym matcher

**Why**: when sellers add free-form text on Stage 2 ("с кондиционером,
встроенная кухня"), they often forget to tick the corresponding
checkboxes. Filters/search miss these listings later. F2 closes the
loop with non-blocking hints — no forced auto-add, no validation
modal.

**How**:
- Curated dictionary in `synonym_entries` table (parameter_key,
  surface_form, language, polarity).
- `synonym_matcher.match_text_to_params(text, lang, current_params)`
  scans text against dictionary; checks 5-token negation window;
  returns matches with `add` / `contradict` / `ok` outcomes.
- Frontend debounces 1s after typing; renders cards below editor.
- Click "Добавить" → updates Stage 1 state (visible on back-navigation).
- "Оставить как есть" dismisses for the session.

**Where it integrates**:
- `app/services/synonym_matcher.py` (new, pure function).
- `app/api/v1/listings.py`: `POST /{id}/analyse-text`.
- `app/api/v1/admin.py` (or new `admin_synonyms.py`): CRUD.
- Frontend: hint UI on Stage 2; admin CRUD page.

**Reuse**:
- `core/regions._DISTRICT_ALIASES` pattern — same kind of
  in-memory dict.
- Block D D5 query parser is a parallel pattern (rule-based,
  no LLM).

### F3 — SEO infrastructure

**Why**: the Vite SPA is invisible to Google. Every active listing
+ filter combo is a long-tail SEO asset. Twelve-month compounding
gain if launched correctly.

**How**:
- FastAPI mounts Jinja2 templates; new `api/v1/seo.py` router
  serves HTML at root paths (`/{lang}/...`).
- Templates render `Listing.ai_description_*` directly (no extra
  data layer needed).
- JSON-LD `RealEstateListing` schema injected in `<head>`.
- Three-language hreflang + canonical URLs.
- Sitemap-index + per-language paginated sitemaps regenerated
  every 15 minutes.
- Soft-deleted listings → 410 Gone.
- Slug drift → 301.
- TWA user-agent → 302 to deep link.

**Where it integrates**:
- `app/api/v1/seo.py` — new router, mounted at root in `main.py`.
- `app/services/seo_meta.py` — title/description/JSON-LD builders.
- `app/services/sitemap.py` — sitemap-index + paginated sitemaps.
- `app/templates/seo/` — Jinja2 templates.
- `app/main.py` — mount with priority below `/api`, `/uploads`.
- Reverse proxy / ingress config (ops task).
- DNS + TLS for `ucharmarket.uz` (ops task).

**Reuse**:
- `services.deeplink.build_listing_link` — "Открыть в UcharMarket"
  CTA.
- `services.deeplink.build_filter_link` — shareable filter URLs.
- `core/regions._DISTRICT_ALIASES` — slug generation.
- `Listing.ai_description_*` — page content.

### F4 — Cabinet exports

**Why**: Cabinet subscription needs a concrete deliverable. AI text
is free; export of that text to other platforms (OLX, Telegram,
Instagram) saves sellers 5–10 minutes per listing. F4 is the
anchor feature behind the 99 000 sum/month paywall.

**How**:
- `services.subscriptions.check_active_subscription(CABINET)` gates
  every `/seller/exports/*` endpoint.
- `services/text_export.py` reads active `export_templates` row by
  (platform, language); sandbox-Jinja2 renders allowlisted
  placeholders + seller's custom signature/CTA/hashtags.
- Per-platform truncation (OLX title 70, Instagram 2200 chars).
- Frontend: buttons in cabinet → API → clipboard + toast.
- Paywall modal for free users → CTA to `/seller/tariffs`.

**Where it integrates**:
- `app/services/text_export.py` (new).
- `app/api/v1/seller_exports.py` (new router).
- `app/api/v1/admin.py` (or new `admin_export_templates.py`): CRUD.
- `app/db/models.py`: `ExportTemplate`; `Seller.export_*` columns.
- Frontend: `seller/feature/text-export/`; admin
  `pages/export-templates/`.

**Reuse**:
- `services.subscriptions.check_active_subscription` (D4) — exact
  helper.
- `services.deeplink.build_listing_link` (D3) — Telegram-template
  URL.
- Block D D4 cabinet FSD pattern — paywall modal, tariff link.

### F5 — Quality management

**Why**: AI generation is operational infrastructure. Without
logging, feedback, and prompt versioning, quality silently
degrades. F5 makes the AI pipeline observable and improvable
without redeploys.

**How**:
- Every generation logs full prompt + response + duration + cost +
  outcome to `ai_generations`.
- Sellers click "Не нравится текст" → `ai_generation_feedback` row
  with 6-category radio + optional comment.
- Admin reviews queue, marks handled, iterates prompts.
- Prompts stored in `prompt_templates` table with version + is_active.
- Activation atomically flips old + new via partial unique index.
- Worker reads active prompt at task start (no service restart).
- Hourly Celery beat checks bad-feedback rate, duration p95, daily
  cost, OpenAI 5xx rate; alerts admin via existing `notify_admins_*`.
- Daily prune at 04:45 enforces 90-day retention.

**Where it integrates**:
- `app/services/prompt_registry.py` (new).
- `app/services/quality_alerts.py` (new).
- `app/workers/tasks/maintenance.py`: `prune_ai_generations`.
- `app/workers/tasks/ai_generation.py`: read prompt + log generation
  (extended).
- `app/api/v1/ai_feedback.py` (new).
- `app/api/v1/admin_ai.py` (new).
- Frontend: `seller/feature/ai-feedback/`; admin `pages/ai-quality/`.

**Reuse**:
- Block D D2 `maintenance.prune_behavioral_signals` — verbatim
  pattern for retention.
- `bot/notifications.notify_admins_*` — alert delivery.
- Block A admin page FSD pattern.

---

## Risk register

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| OpenAI cost spike on burst parser import | Medium | High | Worker concurrency cap (10); daily budget alert; hard daily cap env var |
| Two-step publish friction → seller drop-off | Medium | High | Stage 2 p95 ~3s; manual "Обновить" after 30s; abandoned drafts auto-purged |
| AI text drifts from structured params | High | Medium | F2 hints close known-param gap; product accepts dual-channel truth |
| SSR Postgres pool exhaustion under crawler burst | Medium | Medium | Dedicated read-only pool; 5min HTTP cache; reverse-proxy rate limit |
| Sitemap stale for new listings | Low | Medium | 15-min rebuild; `lastmod` on PATCH |
| Regeneration thrashes D4 channel posts | Low | Medium | `bot_channel_posts.uq_*`; D4 stale-badge UX |
| Prompt activation race | Low | Low | Partial unique index `WHERE is_active` |
| Seller can't find Stage 2 after closing tab | Medium | Medium | DRAFT visible in cabinet "Мои объявления" with continue CTA |
| LLM returns malformed JSON | Low | Medium | Worker `_template_fallback`; logged `outcome=invalid_response` |
| PII leaks into ai_generations.prompt_text | Low | High | Pre-prompt scrubber for phone+email; structured fields never enter prompts |
| DNS/TLS misconfig at F3 launch | Medium | High | Ops checklist with explicit verification step |
| Synonym false positives flood Stage 2 | Medium | Low | Conservative dictionary; negation check; session-scope dismissal |

---

## What can ship today vs deferred

### Ship in Phase-1 (this Block F)
- F5a (logging + prompt registry tables)
- F1 (two-step publish + AI text on every listing)
- F5b (admin review surface + feedback + alerts)
- F2 (synonym matcher + admin CRUD)
- F4 (Cabinet exports + paywall + admin template CRUD)
- F3 (SSR routes + sitemap + JSON-LD + hreflang + CTAs)

### Phase-2 / 1.5 (out of Block F)
- Lifetime regeneration quotas per seller
- Multiple-variant generation ("3 takes" UI)
- Tone control (neutral / business / warm)
- AI-generated separate title (currently derived from structured params)
- A/B testing of prompts in production (infra reserved via version)
- PDF export, bulk export of all listings
- Image rendering for social cards

### Never (explicit non-goals)
- Direct OLX / Instagram API publishing (TOS / legal risk)
- Personalised AI text per buyer (out of scope)
- AI image captioning / generation (out of scope)
