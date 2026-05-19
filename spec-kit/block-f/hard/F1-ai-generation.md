# F1 — AI generation + two-step publish flow

**Difficulty**: hard (5 days)
**Spec source**: Block F V2.0, §F1
**Dependencies**: F5a (`prompt_templates`, `ai_generations` tables)
**Blocks**: F2 (Stage 2 UI), F3 (needs AI text on every listing),
F4 (exports operate on AI text)

---

## Goal

Every listing — manual cabinet creation or crawler import — gets
AI-generated descriptions on three locales (ru / uz / uz_cyrl) as
part of its lifecycle, free, automatically. Manual cabinet creation
becomes a two-step flow: Stage 1 captures params/photos and saves
as `DRAFT`; Stage 2 polls until AI text is ready, lets the seller
edit it, then publishes (`status → ACTIVE`).

---

## Existing infrastructure to reuse

(see TRUTH_LAYER_AUDIT §1 for citations)

- AI generation worker — `backend/app/workers/tasks/ai_generation.py`
  (300 LOC). Generates 3 locales in one batch, has template
  fallback, calls `_enqueue_autopost` (D4 hook) and
  `_notify_sellers_after_generation` (A4 hook) on success.
- `Listing.ai_description_{ru,uz,uz_cyrl}` columns at
  `db/models.py:535-537`.
- `Listing.raw_text` at `db/models.py:532` (for B2B expander).
- `Listing.ai_generation_attempted_at` at `db/models.py:540`.
- `ListingStatus.PENDING_GENERATION` / `GENERATION_FAILED` enum
  values at `db/models.py:82-83`.
- `TelegramListing.raw_text`, `OLXListing.raw_text` at lines 1757
  and 1876.
- Block D `services.autopost._enqueue_autopost` — fires
  automatically on `PENDING_GENERATION → ACTIVE`.
- Block D `services.autopost._dispatch_autopost_for_status_change`
  — fires on any status flip from `listings.py` PATCH; regeneration
  bumps `listing.version`, D4 cabinet auto-shows "stale" badge.
- Block D `bot/i18n.t` — F1 disclaimer key per locale.

---

## What changes

### Database

Migration `pro_block_f_ai_foundation`:
- `ALTER TYPE listingstatus ADD VALUE 'draft'` inside
  `op.get_context().autocommit_block()` per Block A PR-G pattern.
- `Listing.last_ai_param_snapshot` JSONB column (nullable).

### Backend

1. **`app/api/v1/listings.py`** — 4 new endpoints + PATCH guard:
   - `POST /listings/draft` — accepts existing listing-create body,
     creates `Listing(status=DRAFT, last_ai_param_snapshot=<json>)`,
     attaches `ListingImage` rows, enqueues
     `generate_listing_description.delay(listing_id,
     triggered_by="manual")`. Returns `{id, status: "draft"}`.
   - `GET /listings/{id}/draft-preview` — owner only. Returns
     listing + all three `ai_description_*` + snapshot +
     `generation_attempted_at`.
   - `POST /listings/{id}/regenerate` — body
     `{language?: "ru"|"uz"|"uz_cyrl"|null}` (null = all three);
     re-enqueues worker with `triggered_by="manual"`. Bumps
     `listing.version` (D4 cabinet sees stale-badge).
   - `GET /listings/{id}/source-text` — owner only + listing has
     `raw_text` OR is claimed-crawler. Returns
     `{raw_text, source: "telegram"|"olx"|null}`. 404 if not
     eligible.
   - PATCH guard: when transitioning from DRAFT to ACTIVE, validate
     `ai_description_ru IS NOT NULL`; otherwise 409
     `{error: "ai_generation_pending"}`.

2. **`app/workers/tasks/ai_generation.py`** — extended:
   - Read active prompt from `services.prompt_registry.get_active_prompt("listing_description")` (F5a).
   - Apply PII scrubber on `raw_text`: regex `\+?9?98\d{9}|\d{9}`
     for phones, standard email regex; replace with `[contact]`.
     Original `raw_text` in DB untouched.
   - Truncate `raw_text` to 1500 chars: head 700 + " […] " +
     tail 700.
   - On every invocation (success or failure), call
     `services.prompt_registry.record_generation(...)` to write a
     row in `ai_generations` (F5).
   - Existing `_template_fallback`, `_enqueue_autopost`,
     `_notify_sellers_after_generation` calls unchanged.

3. **`app/workers/tasks/maintenance.py`** — new
   `purge_abandoned_drafts()` task:
   - Query: `Listing.status = 'draft' AND updated_at < now() - INTERVAL '7 days'`.
   - Hard delete (CASCADE removes images and `bot_channel_posts`
     rows that never existed).
   - Schedule: daily 05:00 via Celery beat.

4. **`app/workers/celery_app.py`** — beat schedule entry for
   `purge_abandoned_drafts`.

5. **`app/db/models.py`** — `Listing.last_ai_param_snapshot` mapped
   column; no other ORM changes (status enum is extended at DDL
   level only — SQLAlchemy `Enum(ListingStatus, native_enum=True)`
   reads from Postgres).

### Frontend

1. **`modules/seller/pages/create-listing/ui/page/Stage1.tsx`**
   (rename current `Page.tsx`):
   - Same form as today, with a new "Сгенерировать объявление" CTA
     replacing the current "Опубликовать".
   - CTA disabled until minimum required params present (type,
     district, rooms, area, price).
   - CTA animation (short pulse, color change) when minimum
     params first become complete.
   - On submit: `POST /listings/draft` → navigate to
     `/seller/create-listing/{id}/preview`.

2. **`modules/seller/pages/create-listing/ui/page/Stage2.tsx`** (new):
   - On mount: read `?id={draftId}` and `last_ai_param_snapshot` from
     route state.
   - Poll `/listings/{id}/draft-preview` every 2s; max 15 attempts.
   - When `ai_description_ru` non-null → render editor.
   - Three-tab language switcher (Russian / O'zbekcha / Ўзбекча).
   - Edit textarea per language (initially populated with AI text;
     edits stored in Effector store, persist across tab switches
     and back-navigation to Stage 1).
   - Disclaimer block:
     `"AI создал черновик описания на основе ваших параметров. ..."`
     (key `f1_disclaimer` in trilingual bot/i18n).
   - Param-change banner (shown when current params differ from
     `last_ai_param_snapshot`): "Параметры изменились. Обновить
     текст?" with **Обновить** (calls `/regenerate`) /
     **Оставить как есть** (dismisses).
   - "Опубликовать" button → `PATCH /listings/{id} {status:
     "active", description: <ru tab value>, description_uz: ...,
     description_uz_cyrl: ...}`.
   - "Назад" button → preserves edits, navigates to Stage 1.
   - "Не нравится текст" link (F5 feedback button) below editor.
   - After successful publish: redirect to listing detail; F4 export
     buttons available on the next page.

3. **`modules/seller/pages/create-listing/model/`** Effector store:
   ```ts
   $createListing = {
     draftId: string | null,
     stage: 1 | 2,
     paramSnapshot: { type, district, rooms, area, price, ... },
     editedDescriptions: { ru, uz, uz_cyrl },
     generationStatus: 'pending' | 'ready' | 'failed' | 'timeout',
   }
   ```
   Effects: `submitDraftFx`, `fetchDraftPreviewFx`,
   `regenerateFx`, `publishDraftFx`. Polling implemented as a
   self-cancelling interval that ticks `fetchDraftPreviewFx`.

4. **`modules/seller/pages/listings/ui/main/ListingDetail.tsx`**
   (Master-record detail):
   - Add expandable "Показать исходный текст из источника" section
     (only if listing has `raw_text` and is owned by current seller).
   - Calls `GET /listings/{id}/source-text` on expand.
   - Read-only — no edit, no "use as description" button (B2C
     visual cleanliness).

### Translations (bot/i18n, F1 keys)

- `f1_disclaimer` — full disclaimer text per locale.
- `f1_stage2_publish_btn`, `f1_stage2_back_btn`,
  `f1_stage2_regenerate_btn`, `f1_stage2_param_changed_banner`,
  `f1_stage2_polling_message`, `f1_stage2_polling_timeout`,
  `f1_source_text_expander`.

---

## Failure handling

| Failure | Behaviour |
|---|---|
| OpenAI 5xx mid-generation | Celery retry × 3 with backoff. Final failure → `status=GENERATION_FAILED`; `_template_fallback` text written; B2C sees template; B2B Stage 2 shows "Сгенерировать ещё раз" button. |
| OpenAI returns invalid JSON | Treated as failure; logged with `outcome="invalid_response"` in `ai_generations`. |
| Stage 2 poll exceeds 30s | UI shows "Текст ещё генерируется…" with manual "Обновить" button. No status flip. |
| Seller abandons at Stage 2 | DRAFT auto-purged after 7 days by `purge_abandoned_drafts`. Photos GC'd by `uploads_gc.cleanup_orphan_uploads`. |
| PATCH DRAFT→ACTIVE without AI text | 409 `{error: "ai_generation_pending"}`. Frontend shouldn't see this if polling succeeded, but the guard catches racing edits. |
| Concurrent regeneration | Idempotent — last write wins on `ai_description_*` columns. |
| Seller's edits in Stage 2 lost on "Обновить" | Param-change banner explicitly warns: "Ваши правки будут потеряны". |
| Crawler listing has no `raw_text` | Worker generates from structured params alone; `_template_fallback` already handles this. |
| Seller closes tab on Stage 2 | DRAFT visible in cabinet's "Мои объявления" with `status=draft` badge and "Продолжить публикацию" CTA. |

---

## Observability

- `ai_generation.run kind=listing model=<m> listing=<id> duration_ms=<d> cost_usd_micros=<c>`
- `ai_generation.failure outcome=<o> listing=<id> retry_attempt=<n>`
- `ai_generation.pii_scrubbed listing=<id> phones_removed=<n> emails_removed=<n>`
- `listing.draft.created seller=<id> listing=<id>`
- `listing.draft.published seller=<id> listing=<id> attempts=<n>`
- `listing.draft.regenerated listing=<id> trigger=<param_change|manual>`
- `listing.draft.purged listing=<id> age_days=<n>`
- `listing.draft.patch_blocked_no_ai_text listing=<id>`

---

## Acceptance criteria

- New cabinet listing → Stage 1 commits as DRAFT → AI text appears
  within 10s p95 on Stage 2 → seller publishes → ACTIVE.
- D4 autopost fires on the resulting ACTIVE flip (verified via
  `bot_channel_posts` row).
- A4 saved-search push fires on the same transition.
- B2C feed never shows DRAFT listings or `raw_text`.
- B2B Master-record detail shows "Показать исходный текст"
  expander only for owned listings with `raw_text`.
- Stage 2 disclaimer present and visible.
- Param-change banner appears when key params differ; "Обновить"
  triggers regeneration and replaces edits.
- Abandoned DRAFT (no Stage-2 commit in 7 days) is purged.
- PATCH DRAFT→ACTIVE without AI text returns 409.
- PII scrubbing redacts phone and email from `raw_text` before
  prompt assembly; original `raw_text` in DB unchanged.
- `ai_generations` row written for every generation (success +
  failure).

---

## Risks

- **OpenAI cost spike on burst parser import** (Medium / High).
  Mitigation: Celery worker concurrency cap of 10; per-day budget
  alert via F5; hard daily cap env var with template-fallback
  bypass.
- **Two-step publish friction → seller drop-off** (Medium / High).
  Mitigation: Stage 2 perceived speed (p95 ~3s); manual "Обновить"
  after 30s; abandoned drafts auto-purged; DRAFT visible in
  cabinet with continue CTA.
- **Seller's Stage 2 edits lost on back-navigation** (Low / Medium).
  Mitigation: Effector store persists edits across stage swap;
  param-change banner explicitly warns on regenerate.
- **F1 regeneration races D4 autopost** (Low / Medium).
  Mitigation: D4's `bot_channel_posts.uq_(listing_id, channel_id)`
  ensures idempotency; D4's stale-badge UX surfaces re-publication
  to seller's "Update post" click.
