# Block F — Execution Plan

> Order driven by real code dependencies, not by spec section number.
> The principle from Block D: never start implementation until every
> upstream dependency is satisfied. No mid-stream "oh I need X"
> surprises.

---

## Dependency graph

```
F5 (logging + prompt_templates table)
  │
  ▼
F1 (AI gen + 2-step publish — reads prompt from F5 registry)
  │
  ├──────────────────────────────────┐
  ▼                                   ▼
F2 (synonym matcher —                F3 (SSR — needs AI text on
    reads from text editor               every listing)
    on Stage 2)
  │                                   │
  └──────────────────────────────────┤
                                      ▼
                                 F4 (exports —
                                     reads AI text;
                                     gated by Block D
                                     subscription helper)
```

**Critical path: F5 (DB) → F1 → max(F2, F3, F4).**

F5's *database* lands first because F1 reads prompts from it. F5's
*admin UI + alerts* can ship in parallel once the tables exist.

Serial: ~26 calendar days. Parallel after F1: ~17 calendar days.

---

## Suggested PR sequence

### PR-F5a — Logging + prompt-template tables (1.5 days)

Lands the database surface F1 depends on. No UI yet.

**Backend**
1. Migration `pro_block_f_ai_foundation`:
   - `ai_generations` table
   - `prompt_templates` table
   - `ai_generation_feedback` table
   - `Listing.last_ai_param_snapshot` column
   - `ALTER TYPE listingstatus ADD VALUE 'draft'` in `autocommit_block()`
2. `services/prompt_registry.py` — `get_active_prompt`, `record_generation`.
3. Seed `prompt_templates` with v1 = current hard-coded prompt from
   `ai_generation.py:_build_prompt`. Set `is_active=true`.
4. Extend `ai_generation.py` worker to:
   - Read prompt body from registry instead of hard-coded.
   - Call `record_generation` on success and failure.
   - Apply PII scrubber on `raw_text` before prompt build.
   - Truncate `raw_text` to 1500 chars (head + tail).

**Sign-off**
- Existing parser-import flow still generates AI text and ends in
  ACTIVE state (verify against a test listing).
- `SELECT count(*) FROM ai_generations` grows after each generation.
- `SELECT * FROM prompt_templates WHERE is_active` returns exactly 1 row.

---

### PR-F1 — Two-step publish + DRAFT flow (5 days)

Most-visible change for sellers; ships F1.

**Backend**
1. Endpoints: `POST /listings/draft`, `GET /listings/{id}/draft-preview`,
   `POST /listings/{id}/regenerate`, `GET /listings/{id}/source-text`.
2. PATCH guard: DRAFT→ACTIVE rejected with 409 when
   `ai_description_ru IS NULL`.
3. `B2C` query filter — `status IN (ACTIVE, GENERATION_FAILED)` (DRAFT
   excluded automatically).
4. Celery beat: `purge_abandoned_drafts` daily 05:00, retention 7 days.
5. `listing.version` bump on regeneration (D4 cabinet picks this up
   automatically as "stale post" badge).

**Frontend**
1. Split `create-listing` page into `Stage1.tsx` + `Stage2.tsx`.
2. Effector store tracks `draftId`, `stage`, `paramSnapshot`,
   `editedDescriptions` (per language).
3. Stage 2 polls `/draft-preview` at 2s, max 30s. Manual "Обновить"
   button after timeout.
4. Three-tab language switcher (ru / uz / uz-cyrl).
5. Disclaimer block below editor.
6. Param-change banner with "Обновить" / "Оставить как есть".
7. Master-record detail (`seller/pages/listings/.../detail`):
   expandable "Показать исходный текст из источника" calling
   `GET /listings/{id}/source-text`.

**Sign-off**
- New listing via cabinet → DRAFT → AI text appears within 10s p95
  → seller publishes → ACTIVE.
- D4 autopost fires on the resulting ACTIVE flip.
- A4 saved-search push fires on the same transition.
- Abandoned DRAFT (no Stage-2 commit within 7 days) is purged.

---

### PR-F5b — Feedback + admin UI + quality alerts (2.5 days)

Lands after F1 so feedback has real generations to point at.

**Backend**
1. `services/quality_alerts.py:check_thresholds()` — Celery beat
   hourly at :15.
2. `services/maintenance.prune_ai_generations()` — daily 04:45,
   90-day retention.
3. `POST /ai-feedback`.
4. `api/v1/admin_ai.py` — generation list/detail, feedback queue
   + handle, prompt versions list/create/activate.

**Frontend**
1. `seller/feature/ai-feedback/` — "Не нравится текст" link + modal
   on Stage 2 and Master-record detail.
2. `admin/pages/ai-quality/` — tabs Metrics / Generations / Feedback
   queue / Prompts. Side-by-side diff for prompt versions.

**Sign-off**
- Submitting feedback writes a row in `ai_generation_feedback`
  visible in `/admin/ai/feedback`.
- Activating a new prompt version flips `is_active` atomically;
  next generation uses the new prompt body.
- Threshold breach simulated → admin Telegram alert delivered.

---

### PR-F2 — Synonym matcher (3 days)

Independent of F3 / F4; can run in parallel with either.

**Backend**
1. Migration `prp_block_f_synonyms` — `synonym_entries` table.
2. `services/synonym_matcher.py` — `match_text_to_params`.
3. `POST /listings/{id}/analyse-text`.
4. Admin CRUD endpoints under `/admin/synonyms`.
5. Seed `synonym_entries` with curated launch list
   (air_conditioner, balcony, furniture, parking, elevator,
   pets_allowed, repair_type, ...).

**Frontend**
1. Hint cards below Stage 2 editor — debounced 1s.
   - Sequence 1: "You mentioned X — add to params?"
   - Sequence 2: contradictory mention.
   - Grouped UI when 3+ matches.
2. `admin/pages/synonyms/` — list, create, delete, CSV bulk-import.

**Sign-off**
- Type "с кондиционером" in editor (no AC param checked) → hint
  appears within 1.5s.
- Click "Добавить" → AC param checked in Stage 1 on back-navigation.
- Negation ("без мебели") flips polarity correctly.

---

### PR-F4 — Cabinet exports (4 days)

Parallel with F2 / F3 once F1 ships.

**Backend**
1. Migration `prq_block_f_exports`:
   - `export_templates` table
   - `sellers.export_signature / export_cta / export_extra_hashtags`
     columns
2. `services/text_export.py` — sandbox-Jinja2 renderer with
   allowlisted placeholders.
3. `api/v1/seller_exports.py`:
   - `GET /seller/exports/{listing_id}/{platform}?lang=…` — gated by
     D4 `check_active_subscription(CABINET)`.
   - `GET /seller/exports/settings`
   - `PATCH /seller/exports/settings`
4. Admin CRUD for `export_templates`.
5. Seed `export_templates` × 3 platforms × 3 langs = 9 rows.

**Frontend**
1. `seller/feature/text-export/` — buttons block: OLX / Telegram /
   Instagram / Пакет.
2. Paywall modal for free users — CTA links to `/seller/tariffs`.
3. Settings extension: signature / CTA / extra hashtags fields.
4. `admin/pages/export-templates/` — per-platform / per-lang body
   editor.

**Sign-off**
- Subscriber clicks "Экспорт OLX" → text copied to clipboard +
  toast.
- Free user sees paywall modal.
- Admin edits template body → next export reflects the change.

---

### PR-F3 — SEO infrastructure (10 days)

Largest single-PR effort. Can run in parallel with F4 once F1 ships.

**Backend**
1. `services/seo_meta.py` — title / description / og / JSON-LD
   builders.
2. `services/sitemap.py` — index + per-language paginated sitemaps.
3. `api/v1/seo.py` — Jinja2-rendered HTML routes mounted at root.
4. `templates/seo/` — Jinja2 templates (listing, filter, gone,
   empty, sitemap_*, robots).
5. Read-only Postgres pool for SEO routes.
6. User-Agent based TWA bounce.
7. Mount in `main.py` with priority below `/api`, `/uploads`.

**Frontend**
1. None — SSR templates render server-side.

**Ops**
1. DNS A record for `ucharmarket.uz`.
2. TLS cert provisioning.
3. Reverse-proxy routing:
   - `/api/v1/*` → FastAPI API
   - `/admin/*`, `/seller/*` → SPA bundle
   - `/uploads/*` → FastAPI static
   - `/{lang}/*`, `/sitemap*.xml`, `/robots.txt` → FastAPI SEO router
   - everything else → SPA bundle
4. Submit `/sitemap.xml` to Google Search Console + Yandex.Webmaster.

**Sign-off**
- `curl https://ucharmarket.uz/ru/listing/<uuid>/<slug>` returns
  200 HTML with title / description / og:* / canonical / hreflang /
  JSON-LD.
- `curl https://ucharmarket.uz/sitemap.xml` returns sitemap index.
- Google Rich Results Test passes on a sample listing page.
- Soft-deleted listing returns 410 Gone.
- Mobile Lighthouse score for a listing page: Performance ≥ 75,
  SEO 100.

---

## Total timeline

| PR | Days | Cumulative serial |
|----|------|-------------------|
| F5a | 1.5 | 1.5 |
| F1 | 5 | 6.5 |
| F5b | 2.5 | 9 |
| F2 | 3 | 12 |
| F4 | 4 | 16 |
| F3 | 10 | 26 |

**~26 calendar days serial.** With parallel F2/F4 alongside F3 after
F1 ships, **~17 calendar days end-to-end**.

---

## What can ship independently

If we need partial wins:

- **PR-F5a + PR-F1** ships the user-visible Block F win: every new
  listing has AI text via the two-step flow.
- **PR-F5b** stacks on top — operational quality surface.
- **PR-F2** is independent of F3/F4 — small UX polish.
- **PR-F4** ships the Cabinet subscription's anchor feature without
  waiting for F3.
- **PR-F3** can ship last; SEO compounds over months, no urgency to
  the same week.

---

## Cross-cutting must-do BEFORE PR-F1 ships

1. **F5a's prompt registry must be live** — F1 reads prompts from
   the table; hard-coded prompt removed.
2. **PII scrubber must catch the phone + email regexes** before
   prompts include any `raw_text`. Verified on three sample
   Telegram-channel posts known to contain numbers.
3. **`Listing.last_ai_param_snapshot`** column must be migrated —
   F1's regeneration logic depends on it.

---

## Out of scope (explicitly)

- Lifetime regeneration quotas per seller (Phase 2)
- Multiple-variant generation, "give me 3 takes" UI (Phase 2)
- Tone control (neutral / business / warm) (Phase 1.5)
- AI-generated separate title (Phase 1.5; title stays derived from
  structured params)
- A/B testing of prompts in production (infra reserved via
  `prompt_templates.version`, live testing deferred)
- Personalised AI text per buyer
- AI image captioning / generation
- Direct OLX / Instagram API publishing
- PDF export, bulk export of all listings (Phase 2)
- Image rendering for social cards (Phase 2)

---

## Risk-based execution strategy

### Top 5 highest-risk implementation steps

| # | Step | Risk | Mitigation | Rollback |
|---|---|---|---|---|
| **R1** | **PR-F5a — worker reads prompt from DB** | Existing parser-import generation breaks if no `prompt_templates` row exists at restart | Seed runs **before** worker restart (deploy script enforces order); worker has a safety fallback to the hard-coded prompt if `prompt_registry.get_active_prompt` raises | Revert worker patch — the inline prompt is still in git history one commit back |
| **R2** | **PR-F5a — `ALTER TYPE listingstatus ADD VALUE 'draft'`** | Postgres cannot drop enum values; downgrade leaves residual value | Verify no rows have `status='draft'` before downgrade; harmless residual otherwise | Downgrade is a no-op for the enum; tables drop cleanly |
| **R3** | **PR-F3 — SSR router mounted at root** | Could shadow `/api/v1/*` if registered with wrong order/prefix | Smoke test `/api/v1/auth/me`, `/api/v1/listings/*`, `/uploads/*` after SSR mount; document `include_router` order in `main.py` as a comment | Comment out the SEO router include in `main.py`; API surface unaffected |
| **R4** | **PR-F4 — subscription paywall enforcement** | `check_active_subscription` returns True wrongly → free user gets paid feature | Phase-1 flag is intentionally `cabinet_subscription_open_to_all=True`; integration tests cover both flag states; staging flips flag for 1h to verify the 402 path | No rollback needed — paywall is opt-in via env flag |
| **R5** | **PR-F1 — two-step publish UX change** | Sellers used to one-shot creation may abandon at Stage 2 | Staging UAT with 2–3 internal sellers before prod; Stage 2 polling timeout shows "Обновить" not error; p95 generation time tracked from day 1 | Frontend revert to single-step (`Page.tsx` in git history); backend draft endpoints stay (drafts auto-purge in 7 days) |

### Gates between PRs — must-pass before merge

| Before merging | Must verify |
|---|---|
| PR-F5a → PR-F1 | • Live POST `/listings/draft` happy path<br>• Existing PATCH `/listings/{id}` regression unchanged<br>• `ai_generations` row appears per generation<br>• `prompt_templates` partial unique index enforces exactly 1 active per `kind` |
| PR-F1 → next | • Manual UAT: create draft, polish text, publish, back-edit param, regenerate<br>• Confirm D4 autopost task enqueued on ACTIVE flip<br>• Confirm A4 saved-search push fires on ACTIVE flip<br>• `purge_abandoned_drafts` removes a 7-day-old DRAFT on next run |
| PR-F5b → next | • Submit 11 negative feedbacks → `check_quality_thresholds()` → admin Telegram alert delivered exactly once<br>• Admin activates v2 prompt → next AI gen uses v2 body (verify via `ai_generations.prompt_template_id`) |
| PR-F2 → next | • Negation matrix test ("без мебели" with `furniture=with_furniture` → contradiction)<br>• Admin CSV bulk-import via `/admin/synonyms`<br>• ≥ 3 matches grouped into single hint card |
| PR-F4 → next | • Subscriber GET `/seller/exports/<id>/olx` → 200<br>• Free user same endpoint → 402<br>• Listing without AI text → 422<br>• Instagram caption truncation flag set when AI text > 2200 chars<br>• Manual E2E: paste exported text into Telegram chat |
| PR-F3 → next | • `curl /ru/listing/<id>/<slug>` returns HTML with title / og:* / canonical / hreflang / JSON-LD<br>• Google Rich Results Test passes on a sample URL<br>• Soft-deleted listing → 410 Gone<br>• Lighthouse Performance ≥ 75, SEO 100 on a listing page<br>• TWA UA → 302 to deep link |

---

## Testing strategy

### Unit tests per module

| Module | Coverage areas |
|---|---|
| **F5a** | `prompt_registry.get_active_prompt` happy path + missing-row + multiple-versions; `record_generation` writes with correct outcome enum |
| **F1 worker** | `_scrub_pii` (phone variants, emails, mixed); `_truncate_raw_text` (under/at/over budget, multi-byte chars); `_template_fallback` shape |
| **F1 API** | DRAFT → ACTIVE guard returns 409 without AI text; `/regenerate` accepts null vs single-language; `/source-text` ownership filter |
| **F2** | `synonym_matcher.match_text_to_params` matrix: present / absent / contradicts; negation (5-token window); polarity flip; ≥ 2 matches dedup per param; case-insensitive |
| **F3** | `seo_meta.build_listing_meta` produces ≤ 60-char title + ≤ 160-char description; `slug_for_listing` is URL-safe + Latin only; `sitemap.build_listings_sitemap` paginates exactly at 50k |
| **F4** | `text_export.render_for_platform` per (platform, lang) — placeholder substitution, signature/CTA/hashtag injection, length caps, AI-text-missing rejection, malformed-template rejection |
| **F5b** | `quality_alerts.evaluate_*` against synthetic generation/feedback datasets; `check_thresholds` returns expected breach list; transition-only alert (Redis NX flag) |

### Integration tests (end-to-end, staging only)

| Flow | Steps |
|---|---|
| **A** — Draft → publish → autopost | 1) POST `/listings/draft` 2) Poll `/draft-preview` 3) PATCH ACTIVE 4) Assert `bot_channel_posts` row created (D4 autopost fired) |
| **B** — Parser import → AI gen | 1) Insert `TelegramListing` row with `raw_text` 2) Trigger conversion path 3) Wait worker 4) Assert `Listing.status=ACTIVE`, `ai_description_ru` non-null, `ai_generations` row written |
| **C** — Re-gen on param change | 1) Create draft 2) Wait for AI 3) PATCH listing.district 4) POST `/regenerate` 5) Assert `last_ai_param_snapshot.district` updated, new `ai_generations` row |
| **D** — Subscriber export | 1) Create active CABINET subscription 2) GET `/seller/exports/<id>/olx` 3) Assert 200 with formatted text |
| **E** — Free-user paywall | 1) No subscription 2) Same GET → 402 with `{error: "subscription_required"}` |
| **F** — Feedback → alert | 1) Submit 11 negative feedback rows in 24h 2) Run `check_quality_thresholds()` manually 3) Assert mocked Telegram alert sent once |
| **G** — SEO crawl | 1) `curl /ru/listing/<id>/<slug>` 2) Parse returned HTML 3) Assert title / og:* / JSON-LD all present |
| **H** — Synonym hint | 1) POST `/analyse-text` with `"с кондиционером"` + AC missing from `current_params` 2) Assert `[{parameter_key: "air_conditioner", action: "add"}]` |
| **I** — Prompt activation | 1) POST `/admin/ai/prompts` v2 body 2) `/activate` v2 3) New generation 4) Assert `ai_generations.prompt_template_id` references v2 |
| **J** — TWA UA bounce | 1) `curl -H "User-Agent: TelegramWebApp/x.y" /ru/listing/<id>/<slug>` 2) Assert 302 to `t.me/<bot>?startapp=listing_<uuid>` |

### Staging smoke checklist

Run the 10-step "Post-deploy smoke (within 1h)" list from `README.md` SAFE DEPLOY CHECKLIST against staging before promoting to production.

---

## Deployment flow

### Staging deployment order

```
Staging
 ☐ Apply migration `pro_block_f_ai_foundation` on staging Postgres.
 ☐ Run seed: insert one row into `prompt_templates`
       (kind='listing_description', version=1, is_active=true,
       body=<current prompt from ai_generation.py>, model_hint='gpt-4o-mini').
 ☐ Deploy backend (API + workers in same image) — PR-F5a code.
 ☐ Stop Celery beat → Stop Celery worker → Start Celery worker →
       Start Celery beat (drain in-flight tasks during deploy).
 ☐ Restart API process.
 ☐ Smoke: existing /api/v1/auth/me still 200; existing parser-import
       generation still produces ACTIVE listings.
 ☐ Apply migration `prp_block_f_synonyms` on staging.
 ☐ Run seed: ~100 synonym rows × 3 langs.
 ☐ Apply migration `prq_block_f_exports` on staging.
 ☐ Run seed: 9 export_template rows.
 ☐ Deploy backend (API + workers in same image) — PRs F1 + F2 + F4 + F5b code.
 ☐ Restart Celery worker → restart Celery beat → restart API.
 ☐ Deploy frontend (Stage1/Stage2 split, hints, export UI, admin AI page).
 ☐ Deploy SEO router code (PR-F3) — backend redeploy + API restart.
 ☐ Configure reverse proxy:
       /api/v1/*                        → FastAPI
       /uploads/*                       → FastAPI static
       /admin/*  /seller/*              → SPA (TWA bundle)
       /ru/*  /uz/*  /uz-latn/*         → FastAPI SEO router
       /sitemap*.xml  /robots.txt       → FastAPI SEO router
       everything else                  → SPA (TWA bundle)
 ☐ Run integration tests A–J above.
 ☐ Internal UAT — 2-3 sellers create draft → publish; QA exports + Stage 2 edits.
 ☐ Soak 48h. Monitor /admin/ai/generations counts + /admin/ai/feedback queue.

Production rollout (after 48h staging soak)
 ☐ Same migration order, same deploy order.
 ☐ Pause `purge_abandoned_drafts` cron for first 7 days (no historical DRAFTs anyway).
 ☐ Submit https://ucharmarket.uz/sitemap.xml to:
       - Google Search Console
       - Yandex.Webmaster
 ☐ Monitor for first 24h:
       - ai_generation.failure rate target < 2%
       - ai_generation_cost_usd_micros daily sum < F5_OPENAI_DAILY_BUDGET_USD
       - quality_alerts.threshold_breached: zero ideally
       - seo.rendered count growing as crawlers warm up
```

### Worker restart order (every deploy that touches workers)

1. **Stop Celery beat first** — prevents new scheduled tasks landing during deploy.
2. **Stop Celery workers** — they finish in-flight tasks (Celery `task_acks_late=True` already set).
3. **Deploy code**.
4. **Start Celery workers** — new tasks register.
5. **Start Celery beat** — new schedule entries activate.
6. **Restart API process** last — depends on tasks being available for `.delay()` calls.

### Bot restart order

**Not required.** Block F introduces zero changes to `bot/handlers.py`, `bot/inline.py`, `bot/main.py`, `bot/setup.py`, `bot/i18n.py`, or `bot/translations/*.json`. Verified via grep against the spec's "files to touch" list.

### Migration execution order (alembic head sequence)

```
prn_autopost                      (Block D head, already deployed)
   ↓
pro_block_f_ai_foundation         (PR-F5a — F1/F5 backbone)
   ↓
prp_block_f_synonyms              (PR-F2)
   ↓
prq_block_f_exports               (PR-F4)
```

Linear chain. No branches. Each `downgrade()` is reversible (the `draft` enum value is harmless residual).

### Rollback (catastrophic only)

```
 ☐ alembic downgrade prn_autopost  (drops all three Block F tables +
       Listing.last_ai_param_snapshot column + sellers.export_* columns)
 ☐ Redeploy previous backend image (the Block D HEAD image).
 ☐ DRAFT listings remaining post-rollback: SQL bulk-update to DELETED
       (no AI text) or ACTIVE (AI text present). One-time script.
 ☐ Block D pipelines + bot remain unaffected.
```

---

## BLOCK F EXECUTION STATUS

**READY FOR IMPLEMENTATION: YES**

**BLOCKING ISSUES: NONE**

**PARALLELIZATION POSSIBLE: YES** — critical path is `PR-F5a → PR-F1 → max(PR-F2, PR-F3, PR-F4)` ≈ 16 engineer-days serial. With 3 engineers in parallel after PR-F1 deploys, the remaining 4 PRs split across two parallel tracks and complete in ~17 calendar days total. PR-F3 (SSR, 10 engineer-days) is the longest single PR but is fully independent after PR-F1 — assign to a dedicated engineer on the day PR-F1 ships.
