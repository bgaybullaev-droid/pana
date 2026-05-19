# Block F — Implementation Package

> Engineering-ready PR + ticket decomposition. Directly usable for GitHub PR creation and Jira ticket import.
>
> Source-of-truth specs: `README.md` (frozen architecture), `EXECUTION_PLAN.md` (PR sequence + tests).
> This document **does not redesign** — it decomposes.

---

## PR breakdown

### Overview

| PR | Title | Days | Engineer profile | Blocks |
|---|---|---|---|---|
| **PR-F5a** | Logging + prompt_templates tables + worker prompt-from-DB | 1.5 | Backend | F1a |
| **PR-F1a** | Two-step publish backend (DRAFT, endpoints, hooks) | 2 | Backend | F1b, F2, F3*, F4* |
| **PR-F1b** | Two-step publish frontend (Stage1 / Stage2 split, polling) | 3 | Frontend | F2 (UI), F4b (mount) |
| **PR-F5b** | Feedback API + admin AI page + quality alerts | 2.5 | Full-stack | — |
| **PR-F2** | Synonym matcher (BE + admin + Stage2 UI) | 3 | Full-stack | — |
| **PR-F4a** | Cabinet exports backend (templates, service, endpoints) | 2 | Backend | F4b |
| **PR-F4b** | Cabinet exports frontend (buttons, paywall, settings) | 2 | Frontend | — |
| **PR-F3a** | SSR services + Jinja2 templates | 5 | Backend | F3b |
| **PR-F3b** | SSR routes + main.py mount + UA bounce | 3 | Backend | F3c |
| **PR-F3c** | Ops: DNS, cert, reverse proxy, Lighthouse, sitemap submission | 2 | DevOps | — |

---

### PR-F5a — Logging + prompt_templates backbone

| Field | Value |
|---|---|
| **Goal** | Provide DB infrastructure for prompt versioning + generation logging so F1 can read prompts from the registry. Zero user-visible change. |
| **Branch** | `feature/f5a-logging-prompts` |
| **Backend split** | 100% backend |
| **DB migrations** | `pro_block_f_ai_foundation` — adds tables `ai_generations`, `prompt_templates`, `ai_generation_feedback`; adds column `listings.last_ai_param_snapshot`; enum `listingstatus` += `draft` (autocommit_block). |
| **API changes** | None |
| **Files to modify** | `backend/alembic/versions/<date>_pro_block_f_ai_foundation.py` (NEW), `backend/app/db/models.py`, `backend/app/services/prompt_registry.py` (NEW), `backend/app/workers/tasks/ai_generation.py`, `backend/app/core/config.py` |
| **Dependencies** | Block D HEAD (`prn_autopost`) |
| **Test scope** | Existing parser-import flow regression; `ai_generations` row appears per generation; partial unique index enforces 1 active prompt/kind |

---

### PR-F1a — Two-step publish backend

| Field | Value |
|---|---|
| **Goal** | Backend support for DRAFT → ACTIVE flow with manual + auto regeneration. |
| **Branch** | `feature/f1a-draft-publish-backend` |
| **Backend split** | 100% backend |
| **DB migrations** | None (uses `last_ai_param_snapshot` from PR-F5a) |
| **API changes** | Adds 4 endpoints; modifies PATCH guard on existing `/listings/{id}` |
| **Files to modify** | `backend/app/api/v1/listings.py`, `backend/app/api/v1/buyer.py` (DRAFT filter), `backend/app/schemas/listings.py`, `backend/app/workers/tasks/maintenance.py`, `backend/app/workers/celery_app.py` (beat schedule) |
| **Dependencies** | PR-F5a |
| **Test scope** | Flow A integration test (draft → publish → autopost); PATCH regression; 409 on DRAFT→ACTIVE without AI text; `purge_abandoned_drafts` removes 7-day-old DRAFT |

---

### PR-F1b — Two-step publish frontend

| Field | Value |
|---|---|
| **Goal** | Frontend Stage1/Stage2 split with polling, language tabs, edit state, param-change detection. |
| **Branch** | `feature/f1b-draft-publish-frontend` |
| **Backend split** | 100% frontend |
| **DB migrations** | None |
| **API changes** | None (consumes PR-F1a endpoints) |
| **Files to modify** | `frontend/src/modules/seller/pages/create-listing/ui/page/` (rename Page→Stage1, add Stage2, new Page wrapper), `frontend/src/modules/seller/pages/create-listing/model/{effects,stores}/index.ts` (NEW), `frontend/src/modules/seller/pages/listings/ui/main/` (source-text expander), `frontend/src/shared/i18n/locales/{ru,uz,uz-cyrl}/seller.json` |
| **Dependencies** | PR-F1a deployed to staging |
| **Test scope** | Manual UAT (3-seller cohort): create draft → polish → publish → back-edit → regenerate → publish |

---

### PR-F5b — Feedback + admin AI page + quality alerts

| Field | Value |
|---|---|
| **Goal** | In-product feedback button + admin AI-quality surface + prune cron + threshold alerts. |
| **Branch** | `feature/f5b-quality-management` |
| **Backend split** | ~50/50 BE/FE |
| **DB migrations** | None |
| **API changes** | Adds `POST /ai-feedback`, 7 admin endpoints under `/admin/ai/*` |
| **Files to modify** | `backend/app/api/v1/ai_feedback.py` (NEW), `backend/app/api/v1/admin_ai.py` (NEW), `backend/app/api/v1/__init__.py`, `backend/app/services/quality_alerts.py` (NEW), `backend/app/workers/tasks/maintenance.py`, `backend/app/workers/celery_app.py`, `frontend/src/modules/seller/feature/ai-feedback/` (NEW), `frontend/src/modules/admin/pages/ai-quality/` (NEW), `frontend/src/modules/admin/app/router/Router.tsx` |
| **Dependencies** | PR-F1a (so feedback can attach to real generations; also Stage2 mounts the link) |
| **Test scope** | Flow F (feedback → alert), Flow I (prompt activation), atomicity test |

---

### PR-F2 — Synonym matcher

| Field | Value |
|---|---|
| **Goal** | Pure-Python keyword matcher with admin dictionary + Stage2 hint UI. |
| **Branch** | `feature/f2-synonym-matcher` |
| **Backend split** | ~60/40 BE/FE |
| **DB migrations** | `prp_block_f_synonyms` — adds `synonym_entries` table. |
| **API changes** | Adds `POST /listings/{id}/analyse-text`, 3 admin endpoints |
| **Files to modify** | `backend/alembic/versions/<date>_prp_block_f_synonyms.py` (NEW), `backend/app/db/models.py`, `backend/app/services/synonym_matcher.py` (NEW), `backend/app/api/v1/listings.py`, `backend/app/api/v1/admin.py`, `frontend/src/modules/seller/pages/create-listing/ui/page/Stage2.tsx` (hint cards), `frontend/src/modules/admin/pages/synonyms/` (NEW) |
| **Dependencies** | PR-F1b (Stage2 must exist to mount hints) |
| **Test scope** | Flow H (synonym hint); unit-test matrix (present/absent/contradicts/negation); admin CSV bulk import |

---

### PR-F4a — Cabinet exports backend

| Field | Value |
|---|---|
| **Goal** | Per-platform formatted text export gated by Block D Cabinet subscription. |
| **Branch** | `feature/f4a-exports-backend` |
| **Backend split** | 100% backend |
| **DB migrations** | `prq_block_f_exports` — adds `export_templates` table; adds 3 nullable columns on `sellers`. |
| **API changes** | Adds 3 seller endpoints, 1 admin endpoint |
| **Files to modify** | `backend/alembic/versions/<date>_prq_block_f_exports.py` (NEW), `backend/app/db/models.py`, `backend/app/services/text_export.py` (NEW), `backend/app/api/v1/seller_exports.py` (NEW), `backend/app/api/v1/admin.py`, `backend/app/api/v1/__init__.py` |
| **Dependencies** | PR-F1a (consumes `ai_description_*`), Block D `services/subscriptions.check_active_subscription` (consumed, not modified) |
| **Test scope** | Flow D (subscriber 200), Flow E (free 402), 422 when AI text missing, Instagram truncation flag |

---

### PR-F4b — Cabinet exports frontend

| Field | Value |
|---|---|
| **Goal** | Export buttons block + paywall modal + seller signature/CTA/hashtags settings. |
| **Branch** | `feature/f4b-exports-frontend` |
| **Backend split** | 100% frontend |
| **DB migrations** | None |
| **API changes** | None (consumes PR-F4a) |
| **Files to modify** | `frontend/src/modules/seller/feature/text-export/` (NEW), `frontend/src/modules/seller/pages/listings/ui/main/` (mount buttons), `frontend/src/modules/seller/pages/create-listing/ui/page/Stage2.tsx` (mount buttons after publish), `frontend/src/modules/seller/pages/profile/` (extension), `frontend/src/modules/admin/pages/export-templates/` (NEW), `frontend/src/shared/i18n/locales/{ru,uz,uz-cyrl}/seller.json` |
| **Dependencies** | PR-F4a, PR-F1b |
| **Test scope** | Manual UAT (paste to real Telegram chat), paywall modal CTA, settings persistence |

---

### PR-F3a — SSR services + Jinja2 templates

| Field | Value |
|---|---|
| **Goal** | Pure services + templates layer for SSR. No routes yet — purely consumable libraries. |
| **Branch** | `feature/f3a-ssr-services` |
| **Backend split** | 100% backend |
| **DB migrations** | None |
| **API changes** | None (services not yet wired) |
| **Files to modify** | `backend/app/services/seo_meta.py` (NEW), `backend/app/services/sitemap.py` (NEW), `backend/app/db/session.py` (extend with read-only pool), `backend/app/templates/seo/{listing,filter,gone,empty}.html` (NEW), `backend/app/templates/seo/{sitemap_index,sitemap_listings,sitemap_filters}.xml` (NEW), `backend/app/templates/seo/robots.txt` (NEW) |
| **Dependencies** | PR-F1a (AI text in DB to render) |
| **Test scope** | Unit: `slug_for_listing` URL-safety; meta length limits; sitemap pagination at 50k; template snapshot tests |

---

### PR-F3b — SSR routes + main.py mount + UA bounce

| Field | Value |
|---|---|
| **Goal** | Wire SSR routes to the services from F3a; ensure no collision with API. |
| **Branch** | `feature/f3b-ssr-routes` |
| **Backend split** | 100% backend |
| **DB migrations** | None |
| **API changes** | Adds 9 HTML routes at root prefix |
| **Files to modify** | `backend/app/api/v1/seo.py` (NEW; mounted at root, not `/api/v1`), `backend/app/main.py` (Jinja2 mount, include_router order) |
| **Dependencies** | PR-F3a |
| **Test scope** | Flow G (HTML render with schema.org), Flow J (TWA UA → 302); regression: existing `/api/v1/*`, `/uploads/*`, `/admin/*` unaffected |

---

### PR-F3c — Ops: DNS, cert, proxy, Lighthouse, sitemap submission

| Field | Value |
|---|---|
| **Goal** | Production cutover for SEO domain + performance polish + search-console registration. |
| **Branch** | `chore/f3c-seo-ops` (config only) |
| **Backend split** | 0% code; 100% ops |
| **DB migrations** | None |
| **API changes** | None |
| **Files to modify** | reverse-proxy config (nginx/ingress); DNS provider zone; cert manager config; (no app code) |
| **Dependencies** | PR-F3b deployed |
| **Test scope** | Google Rich Results Test pass; Lighthouse Performance ≥ 75, SEO 100; sitemap accepted by Search Console |

---

## Jira tickets

Format: `<PR-ID>-<LAYER>-<SEQ>`. Layers: **DB**, **MODEL**, **SVC**, **API**, **WORKER**, **MAINT**, **CFG**, **ADMIN**, **FE**, **SSR**, **TMPL**, **OPS**, **QA**.

> CSV-importable. Copy each table into Jira CSV import; the column order matches a clean Jira template (`Summary, Description, Acceptance Criteria, Dependencies, Risk`).

### PR-F5a — 12 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F5A-DB-001** | Create alembic migration `pro_block_f_ai_foundation` | Migration file created; `alembic upgrade head` succeeds; `alembic downgrade prn_autopost` succeeds; `downgrade()` drops 3 tables + 1 column | — | Medium |
| **F5A-DB-002** | Add `'draft'` to `listingstatus` enum via `autocommit_block` | `SELECT unnest(enum_range(NULL::listingstatus))` returns `draft`; migration uses `autocommit_block()` per Block A PR-G precedent | F5A-DB-001 | Medium |
| **F5A-MODEL-003** | Add SQLAlchemy classes `AIGeneration`, `PromptTemplate`, `AIGenerationFeedback` to `app/db/models.py` | All three classes import cleanly; `Base.metadata.tables` contains all three table names | F5A-DB-001 | Low |
| **F5A-MODEL-004** | Add `Listing.last_ai_param_snapshot: Mapped[Optional[dict]]` JSONB column | Listing model imports clean; column queryable via SQLAlchemy | F5A-DB-001 | Low |
| **F5A-SVC-005** | Create `app/services/prompt_registry.py` with `get_active_prompt` + `record_generation` | `get_active_prompt('listing_description')` returns active row; raises `PromptNotConfigured` if none; `record_generation` writes a row with all required fields | F5A-MODEL-003 | Low |
| **F5A-CFG-006** | Add config flags to `app/core/config.py`: `f1_draft_lifetime_days=7`, `f5_openai_daily_budget_usd=50`, `f5_alert_bad_feedback_rate=0.10`, `f5_alert_p95_duration_ms=8000`, `f3_public_web_host="https://ucharmarket.uz"` | All five settings readable via `settings.<name>`; env override works | — | Low |
| **F5A-WORKER-007** | Modify `ai_generation.py` worker to read prompt body from `prompt_registry.get_active_prompt` instead of hard-coded `_build_prompt` template | Worker runs end-to-end against a fresh prompt_templates row; on `PromptNotConfigured` falls back to existing hard-coded prompt | F5A-SVC-005 | High |
| **F5A-WORKER-008** | Add `_scrub_pii(text)` and `_truncate_raw_text(text, max_chars=1500)` helpers in worker; apply both before prompt assembly | Phone regex `\+?9?98\d{9}|\d{9}` and email regex replaced with `[contact]`; text > 1500 chars truncated head 700 + ` […] ` + tail 700 | F5A-WORKER-007 | Low |
| **F5A-WORKER-009** | Call `prompt_registry.record_generation` on every generation outcome (ok / fallback_template / timeout / rate_limit / invalid_response) | One `ai_generations` row per worker invocation; outcome string matches enum | F5A-SVC-005 | Low |
| **F5A-OPS-010** | One-time SQL seed for `prompt_templates` v1 (kind='listing_description', is_active=true, body=current hard-coded prompt) | Seed runs idempotently; `SELECT * FROM prompt_templates WHERE is_active` returns exactly 1 row | F5A-DB-001 | Medium |
| **F5A-QA-011** | Integration test: parser-import flow still produces ACTIVE listing with AI text | A test `TelegramListing` inserted → conversion path → resulting `Listing.status=ACTIVE`, `ai_description_ru` non-null | F5A-WORKER-009 | High |
| **F5A-QA-012** | Unit tests for `prompt_registry` (happy/missing/active swap), `_scrub_pii` (3 phone formats, 2 email formats), `_truncate_raw_text` (boundary cases) | Tests in `backend/tests/test_prompt_registry.py` and `test_ai_generation_helpers.py`; 100% coverage of new helpers | F5A-WORKER-008 | Low |

---

### PR-F1a — 12 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F1A-API-001** | Implement `POST /api/v1/listings/draft` — accepts existing `ListingCreate` body, creates `Listing(status=DRAFT)`, enqueues `generate_listing_description.delay(id, triggered_by="manual")` | 201 returned with `{id, status: "draft"}`; image rows attached; Celery task visible in worker logs | F5A-WORKER-009 | Medium |
| **F1A-API-002** | Implement `GET /api/v1/listings/{id}/draft-preview` — owner-only; returns listing fields + 3 AI descriptions + last_ai_param_snapshot | 200 for owner; 403 for non-owner; AI descriptions are nullable in response | F1A-API-001 | Low |
| **F1A-API-003** | Implement `POST /api/v1/listings/{id}/regenerate` — body `{language: "ru"|"uz"|"uz_cyrl"|null}`; enqueues task with `triggered_by="param_change"` or `"manual_retry"` | 202 returned; new `ai_generations` row appears within 10s | F1A-API-001 | Medium |
| **F1A-API-004** | Implement `GET /api/v1/listings/{id}/source-text` — owner-only AND `source_type IN (CLAIMED, PARSED)` | 200 with `{raw_text, source}`; 403 for non-owner; 404 if `source_type=MANUAL` | F1A-API-001 | Low |
| **F1A-API-005** | Add guard to existing `PATCH /api/v1/listings/{id}` — reject DRAFT→ACTIVE flip when `ai_description_ru IS NULL` with 409 `{error: "ai_generation_pending"}` | Test transition w/o AI → 409; transition with AI → 200 | F1A-API-001 | Medium |
| **F1A-API-006** | Update B2C filter in `api/v1/buyer.py` to exclude `status='draft'` rows | DRAFT listings invisible in `/buyer/feed`, `/buyer/search`, all public-facing endpoints | F5A-DB-002 | Medium |
| **F1A-SCHEMA-007** | Add Pydantic schemas: `DraftCreateRequest`, `DraftPreviewResponse`, `RegenerateRequest`, `SourceTextResponse` in `app/schemas/listings.py` | All schemas validate the documented field types | F1A-API-001 | Low |
| **F1A-WORKER-008** | Modify `generate_listing_description` task to accept `triggered_by` arg (default `"auto_parser"`) and pass to `record_generation` | `ai_generations.triggered_by` reflects the call site | F5A-WORKER-009 | Low |
| **F1A-WORKER-009** | Worker writes `listing.last_ai_param_snapshot = {type, district, price, area, rooms}` on successful generation | After AI completion, `SELECT last_ai_param_snapshot FROM listings WHERE id=…` returns the 5 fields | F5A-MODEL-004 | Low |
| **F1A-MAINT-010** | Add `purge_abandoned_drafts` Celery task in `app/workers/tasks/maintenance.py` + beat schedule (daily 05:00) | Task deletes rows WHERE `status='draft' AND updated_at < now() - INTERVAL '<F1_DRAFT_LIFETIME_DAYS> days'`; row count logged | F5A-CFG-006 | Low |
| **F1A-QA-011** | Integration test Flow A: draft → preview poll → publish → assert D4 autopost task enqueued | E2E test in `backend/tests/integration/test_flow_a_draft_publish.py` passes | F1A-API-005 | Medium |
| **F1A-QA-012** | Integration test 409 on premature publish | PATCH DRAFT→ACTIVE w/o AI text returns 409 with expected error body | F1A-API-005 | Low |

---

### PR-F1b — 13 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F1B-FE-001** | Rename `frontend/src/modules/seller/pages/create-listing/ui/page/Page.tsx` → `Stage1.tsx`; create new `Page.tsx` wrapper that renders Stage1 or Stage2 based on Effector store | Wrapper conditionally renders correct stage; no UI regression on Stage 1 | PR-F1a deployed | Medium |
| **F1B-FE-002** | Create Effector store at `frontend/src/modules/seller/pages/create-listing/model/stores/index.ts` with `$stage`, `$draftId`, `$paramSnapshot`, `$editedDescriptions`, `$pollingError` | Stores import; default values applied; reset on unmount | F1B-FE-001 | Low |
| **F1B-FE-003** | Stage 1 "Сгенерировать объявление" button — disabled until {type, district, rooms, area, price} all present; pulse animation on activation | Button disabled with tooltip; pulse triggered exactly once on transition false→true | F1B-FE-001 | Low |
| **F1B-FE-004** | Effector effect `createDraftFx` calling `POST /listings/draft`; on success sets `$draftId` + `$stage=2` | Network call observable in DevTools; success path navigates to Stage 2 | F1B-FE-002 | Low |
| **F1B-FE-005** | Effector effect `fetchDraftPreviewFx` polling `GET /listings/{id}/draft-preview` at 2s × ≤15 iterations; stops when `ai_description_ru` non-null or 15 iterations elapsed | Poll interval visible in DevTools; manual "Обновить" button appears after timeout | F1B-FE-004 | Medium |
| **F1B-FE-006** | Stage 2 three-tab language switcher (RU / UZ / ЎЗ) using Mantine `Tabs` | Switching tabs updates the editor to the selected language version; current edit preserved across tab switches | F1B-FE-005 | Low |
| **F1B-FE-007** | Stage 2 editable `Textarea` per language; on edit writes to `$editedDescriptions[lang]` | Edits persist across tab switches; debounce 300ms before store update | F1B-FE-006 | Low |
| **F1B-FE-008** | Stage 2 disclaimer block below editor — info-icon + text from i18n key `create.stage2.disclaimer` | Disclaimer renders; styling matches existing info-block pattern | F1B-FE-007 | Low |
| **F1B-FE-009** | Param-change banner (Stage 2 mount) — compare `$paramSnapshot` to current Stage 1 params; show banner with "Обновить" / "Оставить как есть" buttons when {type, district, price, area, rooms} differ | Banner appears only when key param differs; "Обновить" calls `regenerateDraftFx` and refreshes preview | F1B-FE-005 | Medium |
| **F1B-FE-010** | "Опубликовать" button — calls `publishDraftFx` (PATCH `/listings/{id}` with edited description + status=active); on 200 navigates to `/seller/listings` | Successful publish navigates; 409 shows toast "Текст ещё генерируется" | F1B-FE-007 | Medium |
| **F1B-FE-011** | Master-record detail page — expandable "Показать исходный текст из источника" block calling `GET /listings/{id}/source-text` | Expander only renders when `source_type ∈ {CLAIMED, PARSED}`; loading spinner; text rendered preformatted | PR-F1a deployed | Low |
| **F1B-FE-012** | i18n keys for Stage 1/2 + master-record expander × 3 locales in `seller.json` | All keys present in all 3 files; no missing-key warnings in console | F1B-FE-001 | Low |
| **F1B-QA-013** | Manual UAT script — 3 internal sellers run full flow on staging | UAT report attached; 0 P0 bugs | F1B-FE-012 | High |

---

### PR-F5b — 16 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F5B-API-001** | Implement `POST /api/v1/ai-feedback` (auth required) — body `{generation_id?, listing_id, category, comment?}`; inserts row in `ai_generation_feedback` | Row visible via SQL; 201 returned with `{id}`; rate-limit 30/min/user (Redis NX) | PR-F5a, PR-F1a | Low |
| **F5B-API-002** | Implement `GET /api/v1/admin/ai/generations` — paginated, filterable by `?date_from`, `?lang`, `?model`, `?outcome`, `?has_feedback` | Admin auth required; paginated response with `total`, `page`, `items` | PR-F5a | Low |
| **F5B-API-003** | Implement `GET /api/v1/admin/ai/generations/{id}` — full row including `prompt_text`, `response_text` | Returns full generation; admin auth required | F5B-API-002 | Low |
| **F5B-API-004** | Implement `GET /api/v1/admin/ai/feedback` — paginated, default `?handled=false` | Returns feedback queue; admin auth required | F5B-API-001 | Low |
| **F5B-API-005** | Implement `POST /api/v1/admin/ai/feedback/{id}/handle` — marks `handled=true` | Idempotent; 200 with updated row | F5B-API-004 | Low |
| **F5B-API-006** | Implement `GET /api/v1/admin/ai/prompts` — list versions per kind | Returns rows ordered by version DESC | PR-F5a | Low |
| **F5B-API-007** | Implement `POST /api/v1/admin/ai/prompts` — create new version (`is_active=false`, `version=max+1`) | Returns new row; partial unique index unaffected | F5B-API-006 | Low |
| **F5B-API-008** | Implement `POST /api/v1/admin/ai/prompts/{id}/activate` — atomic swap via single `UPDATE prompt_templates SET is_active=(id=:new_id) WHERE kind=:kind` | Partial unique index `(kind) WHERE is_active` enforces ≤1 active; concurrent activation safe | F5B-API-007 | Medium |
| **F5B-SVC-009** | Create `app/services/quality_alerts.py` with `evaluate_bad_feedback_rate`, `evaluate_duration_p95`, `evaluate_daily_cost_usd`, `check_thresholds`, `maybe_notify_admins` (uses Redis flag `alert:<metric>:active` for transition-only alerts) | Each evaluator returns expected value against test fixture data | PR-F5a | Medium |
| **F5B-WORKER-010** | Add `prune_ai_generations` Celery task — DELETE WHERE created_at < now() - 90 days; beat schedule daily 04:45 | Task deletes only rows older than 90d; row count logged | PR-F5a | Low |
| **F5B-WORKER-011** | Add `check_quality_thresholds` Celery task — hourly :15; calls service + sends admin alerts via existing `bot/notifications.notify_admins_custom` | Force breach with 11 negative feedbacks → exactly one alert delivered per breach (transition) | F5B-SVC-009 | High |
| **F5B-FE-012** | Create `seller/feature/ai-feedback/` — `FeedbackLink` + `FeedbackModal` components with 6 category radios + comment textarea | Modal opens on click; submission calls `submitFeedbackFx` (`POST /ai-feedback`) | F5B-API-001 | Low |
| **F5B-FE-013** | Mount feedback link on Stage 2 (PR-F1b coordination) and Master-record detail | Link present; modal flow works | F5B-FE-012, PR-F1b | Low |
| **F5B-FE-014** | Create `admin/pages/ai-quality/` FSD module with 4 tabs (Metrics / Generations / Feedback / Prompts) | All 4 tabs render; pagination works on each list; admin route registered | F5B-API-008 | Medium |
| **F5B-FE-015** | Prompt version side-by-side diff component (use existing diff lib or simple `<pre>` two-column layout) | Diff view shows added/removed lines; activation button per row | F5B-FE-014 | Low |
| **F5B-QA-016** | Integration tests: Flow F (feedback → alert), Flow I (prompt activation) | Both flows pass in CI; threshold simulation produces alert; activation atomic under concurrent requests | F5B-WORKER-011, F5B-API-008 | Medium |

---

### PR-F2 — 14 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F2-DB-001** | Create alembic migration `prp_block_f_synonyms` — table `synonym_entries` with indices `(parameter_key, language)`, `(surface_form, language)`, unique `(parameter_key, parameter_value, surface_form, language)` | Migration upgrades + downgrades cleanly; partial unique enforced | PR-F1a | Low |
| **F2-MODEL-002** | Add `SynonymEntry` SQLAlchemy class | Model imports; table reflected via `Base.metadata` | F2-DB-001 | Low |
| **F2-SVC-003** | Create `app/services/synonym_matcher.py` — `match_text_to_params(db, text, language, current_params) → list[SynonymMatch]` with negation (5-token window for `["не", "без", "no", "yo'q", "yo'k"]`) | Unit-test matrix passes (present/absent/contradicts/negation/multi-match dedup) | F2-MODEL-002 | Medium |
| **F2-API-004** | Implement `POST /api/v1/listings/{id}/analyse-text` — owner-only; body `{text, language, current_params}` | Returns `{matches: [...]}`; rate-limited 30/min/user | F2-SVC-003 | Low |
| **F2-ADMIN-005** | Implement `GET /api/v1/admin/synonyms` — filterable by `?parameter_key`, `?language` | Returns paginated rows; admin auth required | F2-MODEL-002 | Low |
| **F2-ADMIN-006** | Implement `POST /api/v1/admin/synonyms` — accepts a list of entries for bulk import | Returns inserted rows; conflict resolution `ON CONFLICT DO NOTHING` | F2-ADMIN-005 | Low |
| **F2-ADMIN-007** | Implement `DELETE /api/v1/admin/synonyms/{id}` | 204 returned; row removed | F2-ADMIN-005 | Low |
| **F2-FE-008** | Stage 2 hint cards below editor — Sequence 1 (`action="add"`) with "Да, добавить" / "Нет, оставить как есть" | Hint renders; "Да" updates `$editedParams` store | F2-API-004, PR-F1b | Medium |
| **F2-FE-009** | Stage 2 hint cards — Sequence 2 (`action="contradict"`) with orange accent + 3 buttons | Hint renders distinctly; "Изменить параметр" / "Исправить текст" / "Оставить как есть" all functional | F2-FE-008 | Medium |
| **F2-FE-010** | Stage 2 hint grouping — when >3 matches, render single "Найдено N упоминаний…" card with expandable list + "Добавить все" button | Group renders at threshold; expand toggles; bulk add works | F2-FE-009 | Low |
| **F2-FE-011** | Debounced `analyseTextFx` call — 1s after typing stops; cancel in-flight on new edit | DevTools shows max 1 active request; previous canceled | F2-FE-008 | Medium |
| **F2-FE-012** | Create `admin/pages/synonyms/` FSD module — list view + bulk CSV paste import | Table renders rows; CSV paste creates entries via bulk endpoint; delete works | F2-ADMIN-006 | Low |
| **F2-OPS-013** | Seed `synonym_entries` with curated launch list (~100 entries × 3 langs) — air_conditioner, balcony, furniture, parking, elevator, pets_allowed, repair_type | Idempotent seed script (`ON CONFLICT DO NOTHING`); SQL row count matches expected | F2-DB-001 | Medium |
| **F2-QA-014** | Integration test Flow H + unit-test matrix in `backend/tests/test_synonym_matcher.py` | All matrix cases pass; negation flips polarity; rate-limit returns 429 on 31st request | F2-SVC-003 | Medium |

---

### PR-F4a — 10 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F4A-DB-001** | Create alembic migration `prq_block_f_exports` — table `export_templates` (partial unique `(platform, language) WHERE is_active`), columns `sellers.export_signature`, `sellers.export_cta`, `sellers.export_extra_hashtags` | Upgrade + downgrade clean | PR-F1a | Low |
| **F4A-MODEL-002** | Add `ExportTemplate` SQLAlchemy class; extend `Seller` with 3 new columns | Models import; columns reflect | F4A-DB-001 | Low |
| **F4A-SVC-003** | Create `app/services/text_export.py` with `render_for_platform(db, listing, seller, platform, lang) → ExportPayload(text, title?, truncated)` using `jinja2.sandbox.SandboxedEnvironment` | Allowlist enforced; OLX title 70-char cap; Instagram 2200-char cap with `…` truncation flag | F4A-MODEL-002 | Medium |
| **F4A-API-004** | Implement `GET /api/v1/seller/exports/{listing_id}/{platform}?lang=…` — gated by `check_active_subscription(CABINET)`; 402 for free users; 422 when AI text missing | All three response codes verified in tests | F4A-SVC-003, Block D `services/subscriptions` | High |
| **F4A-API-005** | Implement `GET /api/v1/seller/exports/settings` + `PATCH /api/v1/seller/exports/settings` | Returns/updates signature/CTA/hashtags; values persisted across reload | F4A-MODEL-002 | Low |
| **F4A-ADMIN-006** | Implement `GET /api/v1/admin/export-templates` + `PATCH /api/v1/admin/export-templates/{id}` | Admin auth required; template body persists | F4A-MODEL-002 | Low |
| **F4A-ROUTE-007** | Register router in `backend/app/api/v1/__init__.py` with prefix `/seller/exports` tag `Exports (F4)` | OpenAPI shows new endpoints under correct tag | F4A-API-005 | Low |
| **F4A-OPS-008** | Seed 9 `export_templates` rows (3 platforms × 3 langs) with initial bodies | Seed idempotent; `SELECT * WHERE is_active` returns 9 distinct rows | F4A-DB-001 | Medium |
| **F4A-QA-009** | Integration tests Flow D (subscriber → 200) and Flow E (free user → 402) | Both flows pass in CI with `check_active_subscription` mocked True/False | F4A-API-004 | Medium |
| **F4A-QA-010** | Unit tests for `text_export.render_for_platform` — placeholder substitution, signature injection, length truncation, missing-AI-text rejection, sandboxed Jinja2 (no filesystem access) | All 5 cases pass | F4A-SVC-003 | Low |

---

### PR-F4b — 8 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F4B-FE-001** | Create `seller/feature/text-export/` module with `model/effects` (`fetchExportFx`, `fetchExportSettingsFx`, `updateExportSettingsFx`) | Effects callable; types correct | PR-F4a | Low |
| **F4B-FE-002** | Create `ui/ExportButtons.tsx` with 4 buttons (OLX / Telegram / Instagram / Пакет) | All 4 buttons render; click triggers correct effect | F4B-FE-001 | Low |
| **F4B-FE-003** | Clipboard write via `navigator.clipboard.writeText` + Mantine toast on success | Text reaches clipboard; toast appears for 3s | F4B-FE-002 | Low |
| **F4B-FE-004** | Paywall modal on 402 response — CTA "Подписаться" links to `/seller/tariffs` | Modal opens on 402; "Подписаться" navigates to tariffs page | F4B-FE-002 | Medium |
| **F4B-FE-005** | Extend `seller/pages/profile/` with 3 new fields (signature, CTA, extra hashtags) saved on blur via `updateExportSettingsFx` | Fields render in correct section; persist across reload | F4B-FE-001 | Low |
| **F4B-FE-006** | Create `admin/pages/export-templates/` FSD module — list templates × (platform, lang); body editor | All 9 templates listed; edit saves via `PATCH` | PR-F4a | Low |
| **F4B-FE-007** | i18n keys for export buttons, paywall modal, profile settings × 3 locales in `seller.json` | All keys present; no missing-key warnings | F4B-FE-002 | Low |
| **F4B-QA-008** | Manual UAT: paste exported text to real Telegram chat; verify formatting | UAT report; emoji + line breaks correct | F4B-FE-007 | Medium |

---

### PR-F3a — 10 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F3A-SVC-001** | Create `app/services/seo_meta.py` with `build_listing_meta`, `build_filter_meta`, `build_listing_jsonld`, `slug_for_listing` | All 4 functions return correct dataclasses/dicts; slug is URL-safe + Latin-only | PR-F1a | Medium |
| **F3A-SVC-002** | Create `app/services/sitemap.py` with `build_listings_sitemap`, `build_filters_sitemap`, `build_index` (paginated 50k urls) | XML output valid against sitemaps.org schema; paginates correctly at 50k boundary | F3A-SVC-001 | Medium |
| **F3A-DB-003** | Extend `app/db/session.py` with dedicated read-only async engine `seo_read_engine` (separate pool_size=10) | Pool isolation verified; API pool unaffected under simulated crawler burst | — | Medium |
| **F3A-TMPL-004** | Create `app/templates/seo/listing.html` — title/meta/og/twitter/canonical/hreflang/JSON-LD + body with description + structured params + "Открыть в UcharMarket" CTA | Snapshot test against fixture listing matches | F3A-SVC-001 | Medium |
| **F3A-TMPL-005** | Create `app/templates/seo/filter.html` — title/meta + list of listings + pagination | Snapshot test passes | F3A-SVC-001 | Low |
| **F3A-TMPL-006** | Create `app/templates/seo/gone.html` + `app/templates/seo/empty.html` | Both templates render; gone returns 410-friendly minimal body; empty returns noindex meta | — | Low |
| **F3A-TMPL-007** | Create `app/templates/seo/sitemap_index.xml`, `sitemap_listings.xml`, `sitemap_filters.xml` | XML validates; lastmod per entry; loc canonical | F3A-SVC-002 | Low |
| **F3A-TMPL-008** | Create `app/templates/seo/robots.txt` — allow `/`, `/ru/`, `/uz/`, `/uz-latn/`, `/sitemap*`; disallow `/api`, `/admin`, `/seller`, `/uploads` | Curl matches expected body | — | Low |
| **F3A-QA-009** | Unit tests: `slug_for_listing` URL-safety, meta length (`title`≤60, `description`≤160), sitemap pagination at exactly 50k boundary | All cases pass | F3A-SVC-002 | Low |
| **F3A-QA-010** | Snapshot tests for all 4 HTML templates against fixture data | Snapshots committed to repo; CI regenerates and compares | F3A-TMPL-006 | Low |

---

### PR-F3b — 9 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F3B-ROUTE-001** | Create `app/api/v1/seo.py` with 9 routes: `/{lang}/listing/{id}/{slug}`, `/{lang}/tashkent/{district}`, `/{lang}/{deal}/{type}`, `/{lang}/{deal}/{type}/{district}`, `/{lang}/{deal}/{type}/{rooms}-rooms/{district}`, `/sitemap.xml`, `/sitemap-{lang}-listings.xml`, `/sitemap-{lang}-filters.xml`, `/robots.txt` | All 9 routes return 200 against fixtures | PR-F3a | High |
| **F3B-ROUTE-002** | TWA UA bounce middleware — if `User-Agent` contains `TelegramWebApp` or `tdesktop` → 302 to `services.deeplink.build_listing_link` | UA fixture → 302; bot UA → 200 HTML | F3B-ROUTE-001, Block D `services/deeplink` | Medium |
| **F3B-ROUTE-003** | Set `Cache-Control: public, max-age=300` (listing/filter), 900 (sitemap), 3600 (robots) | curl headers match | F3B-ROUTE-001 | Low |
| **F3B-ROUTE-004** | 410 Gone for listings with `deleted_at IS NOT NULL` or `status NOT IN (ACTIVE, GENERATION_FAILED)` | Deleted listing returns 410 with `gone.html` | F3B-ROUTE-001 | Medium |
| **F3B-ROUTE-005** | 301 slug-drift redirect — if URL slug ≠ `slug_for_listing(listing)` → 301 to canonical | Drift → 301; canonical match → 200 | F3B-ROUTE-001 | Medium |
| **F3B-MAIN-006** | Modify `app/main.py` — `templates = Jinja2Templates(directory=str(BASE / "templates"))`; `app.include_router(seo_router)` mounted at root prefix; verified order so `/api/v1/*` matches first | `/api/v1/auth/me` smoke test still 200 after mount; `/ru/listing/<id>/<slug>` returns 200 | F3B-ROUTE-001 | High |
| **F3B-QA-007** | Regression smoke — all existing API endpoints (`/api/v1/auth/me`, `/api/v1/listings/...`, `/uploads/*`) unaffected | CI passes existing test suite | F3B-MAIN-006 | High |
| **F3B-QA-008** | Integration test Flow G — `curl /ru/listing/<id>/<slug>` parsed HTML contains title, og:*, JSON-LD with `RealEstateListing` type | Tests pass in CI | F3B-ROUTE-001 | Medium |
| **F3B-QA-009** | Integration test Flow J — TWA UA → 302 with deep-link URL | Test passes | F3B-ROUTE-002 | Low |

---

### PR-F3c — 8 tickets

| Ticket ID | Description | Acceptance criteria | Dependencies | Risk |
|---|---|---|---|---|
| **F3C-OPS-001** | Create DNS A record for `ucharmarket.uz` pointing to web host | `dig ucharmarket.uz` returns expected IP | — | Medium |
| **F3C-OPS-002** | Provision TLS cert (Let's Encrypt or equivalent) for `ucharmarket.uz` | `curl -I https://ucharmarket.uz` returns valid cert chain | F3C-OPS-001 | Medium |
| **F3C-OPS-003** | Update reverse proxy (nginx/ingress) — route `/api/v1/*` → API, `/uploads/*` → API static, `/admin/*` + `/seller/*` → SPA, `/ru/*` + `/uz/*` + `/uz-latn/*` + `/sitemap*` + `/robots.txt` → FastAPI SEO router, default → SPA | curl matrix tests pass; existing flows unaffected | F3C-OPS-002 | High |
| **F3C-PERF-004** | Image optimization — ensure existing `original_url` photos serve as WebP (existing infra or new middleware); lazy-load attribute in `listing.html` | Lighthouse Performance ≥ 75 on a real listing page | PR-F3b | Medium |
| **F3C-PERF-005** | Reduce CSS/JS footprint in SEO templates — strip TWA-only assets from SEO HTML | Lighthouse JS bytes < 50KB; CSS < 20KB | F3C-PERF-004 | Low |
| **F3C-OPS-006** | Submit `https://ucharmarket.uz/sitemap.xml` to Google Search Console | Sitemap status "Success" in GSC dashboard | F3C-OPS-003 | Low |
| **F3C-OPS-007** | Submit `https://ucharmarket.uz/sitemap.xml` to Yandex.Webmaster | Sitemap accepted in Yandex.Webmaster | F3C-OPS-003 | Low |
| **F3C-QA-008** | Google Rich Results Test pass — `RealEstateListing` schema validates on a sample listing URL | Public Rich Results Test URL shows green checks for all required RealEstateListing fields | F3C-OPS-006 | Medium |

---

## Critical path analysis

### Blocking chain

```
F5a (BE, 1.5d)
  ↓
F1a (BE, 2d)
  ├──────────────────────────────────────────────────────┐
  ↓                                                       ↓
F1b (FE, 3d)        F3a (BE, 5d)                       F5b (FS, 2.5d)        F4a (BE, 2d)
  ↓                  ↓                                                          ↓
F2 (FS, 3d)         F3b (BE, 3d)                                              F4b (FE, 2d)
                     ↓
                    F3c (Ops, 2d)
```

**Critical path** = F5a + F1a + max(F3a + F3b + F3c, F1b + F2, F5b, F4a + F4b)
= 1.5 + 2 + max(10, 6, 2.5, 4)
= **13.5 engineer-days serial on the critical path** (longest branch is F3a → F3b → F3c at 10 days, gated by F1a).

### Parallel execution groups

| After deploying | Can start in parallel |
|---|---|
| **PR-F5a** | PR-F1a only (everything else depends on F1a) |
| **PR-F1a** | PR-F1b, PR-F3a, PR-F4a, PR-F5b |
| **PR-F1b** | PR-F2, PR-F4b, PR-F5b FE (if not started) |
| **PR-F3b** | PR-F3c |
| **PR-F4a** | PR-F4b |

### Engineer assignment

| Engineer | Profile | Workload | Total days |
|---|---|---|---|
| **BE-1** | Backend lead | F5a → F1a → F2 backend → F4a backend | 8.5 |
| **BE-2** | Backend | F3a → F3b | 8 (starts day 1.5) |
| **FS-1** | Full-stack | F1b → F2 frontend → F5b frontend + backend | 6.5 (starts day 3.5) |
| **FS-2** | Full-stack | F4b → F5b admin pages → F4b polishing | 4 (starts day 5.5) |
| **DevOps** | Ops | F3c (DNS, cert, proxy, Lighthouse, sitemap submission) | 2 (starts day 12.5) |
| **QA** | Quality | Integration test fixtures, CI runs, UAT coordination throughout | continuous |

**Calendar timeline with 5 engineers**: 14–15 calendar days end-to-end (including 1-day staging soak between feature complete and prod rollout).

---

## Database + migration mapping

| PR | Migration | Schema diff | Rollback impact |
|---|---|---|---|
| **PR-F5a** | `pro_block_f_ai_foundation` | + 3 tables (`ai_generations`, `prompt_templates`, `ai_generation_feedback`) + 1 column (`listings.last_ai_param_snapshot` JSONB) + 1 enum value (`listingstatus.draft`) | Drops 3 tables + 1 column. Enum value stays (PG limitation — harmless if no rows reference). |
| **PR-F1a** | — | None (uses PR-F5a's schema) | N/A |
| **PR-F1b** | — | None | N/A |
| **PR-F5b** | — | None (consumes PR-F5a's tables) | N/A |
| **PR-F2** | `prp_block_f_synonyms` | + 1 table (`synonym_entries`) | Drops 1 table. |
| **PR-F4a** | `prq_block_f_exports` | + 1 table (`export_templates`) + 3 columns (`sellers.export_signature`, `sellers.export_cta`, `sellers.export_extra_hashtags`) | Drops 1 table + 3 columns. |
| **PR-F4b** | — | None | N/A |
| **PR-F3a** | — | None | N/A |
| **PR-F3b** | — | None | N/A |
| **PR-F3c** | — | None | N/A |

### Migration execution order

```
prn_autopost                       (Block D HEAD, pre-existing)
  ↓
pro_block_f_ai_foundation          (PR-F5a)
  ↓
prp_block_f_synonyms               (PR-F2)
  ↓
prq_block_f_exports                (PR-F4a)
```

Linear chain. Apply in this order; reverse to roll back.

---

## QA mapping

### Per-PR test coverage

| PR | Validating tests from Execution Plan | Staging validation |
|---|---|---|
| **PR-F5a** | Unit: F5A-QA-011 (parser-import regression), F5A-QA-012 (unit tests for helpers) | Manual: deploy → verify existing parser flow → check `ai_generations` row created |
| **PR-F1a** | Integration: Flow A (draft → publish → autopost) — F1A-QA-011, F1A-QA-012 | Manual: POST `/listings/draft` → poll → PATCH ACTIVE → verify D4 autopost task in worker logs |
| **PR-F1b** | Manual UAT: F1B-QA-013 (3-seller cohort) | UAT staging script in QA portal |
| **PR-F5b** | Integration: Flow F (feedback → alert), Flow I (prompt activation) — F5B-QA-016 | Force breach with 11 negative feedbacks → admin Telegram alert received |
| **PR-F2** | Integration: Flow H (synonym hint); unit: F2-QA-014 matrix | Type "с кондиционером" → hint appears within 1.5s → "Да, добавить" → AC checked |
| **PR-F4a** | Integration: Flow D (subscriber 200), Flow E (free 402) — F4A-QA-009, F4A-QA-010 | Subscriber + free user E2E |
| **PR-F4b** | Manual UAT: F4B-QA-008 (cross-post to Telegram) | UAT staging script |
| **PR-F3a** | Unit: F3A-QA-009 (slug, length, pagination), F3A-QA-010 (template snapshots) | N/A (services only, no routes) |
| **PR-F3b** | Integration: Flow G (SEO crawl), Flow J (TWA UA bounce) — F3B-QA-008, F3B-QA-009 | curl matrix from staging URL |
| **PR-F3c** | Lighthouse + Google Rich Results Test — F3C-QA-008 | Public Rich Results Test URL; Lighthouse run on production |

### Staging validation checklist per PR

| PR | Checklist item from `README.md` SAFE DEPLOY CHECKLIST |
|---|---|
| **PR-F5a** | "Apply migration `pro_block_f_ai_foundation`" + "Seed `prompt_templates` v1" + "Smoke: existing parser-import still produces ACTIVE listings" |
| **PR-F1a** | "POST /listings/draft → 201 status=draft" + "GET /listings/<id>/draft-preview → ai_description_ru populated" + "PATCH ACTIVE → 200" |
| **PR-F1b** | Internal UAT — 2-3 sellers create draft → publish; QA Stage 2 edits |
| **PR-F5b** | "Submit /ai-feedback → admin sees in /admin/ai/feedback" + "Force breach → alert delivered" |
| **PR-F2** | "POST /listings/<id>/analyse-text → matches:[...]" |
| **PR-F4a** | "Subscriber GET /seller/exports/<id>/olx → text returned" + "Free user same → 402" |
| **PR-F4b** | UAT — paste to real Telegram chat |
| **PR-F3a** | N/A (services only) |
| **PR-F3b** | "curl https://ucharmarket.uz/ru/listing/<id>/<slug> in incognito → HTML renders" + "curl /sitemap.xml" + "curl /robots.txt" |
| **PR-F3c** | "Validate JSON-LD with Google Rich Results Test" + "Submit sitemap.xml to Google Search Console + Yandex.Webmaster" |

---

## BLOCK F IMPLEMENTATION PACKAGE STATUS

**PR STRUCTURE COMPLETE: YES** — 10 PRs defined (F5a, F1a, F1b, F5b, F2, F4a, F4b, F3a, F3b, F3c) with goals, files, dependencies, test scope.

**JIRA TASKS COMPLETE: YES** — 112 atomic tickets across the 10 PRs:
- F5a: 12 | F1a: 12 | F1b: 13 | F5b: 16 | F2: 14 | F4a: 10 | F4b: 8 | F3a: 10 | F3b: 9 | F3c: 8

**READY FOR ENGINEERING SPRINT: YES** — critical path is 13.5 engineer-days serial; with 5 engineers in parallel (2 BE + 2 FS + 1 DevOps + continuous QA) the realistic calendar runtime is **14–15 days end-to-end** including a 1-day staging soak.

**BLOCKING ISSUES: NONE**
