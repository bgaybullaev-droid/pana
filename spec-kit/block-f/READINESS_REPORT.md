# Block F — Readiness Report

> What's blocked, what's known, what needs a product/ops decision
> before implementation can begin.

---

## At a glance

| Block | Spec | Audit | Open Questions | Ready to implement? |
|-------|------|-------|----------------|---------------------|
| F1 | ✓ | ✓ | 0 (5 frozen in decision-pass) | After PR-F5a lands |
| F2 | ✓ | ✓ | 0 (3 frozen) | After F1 — UI depends on Stage 2 |
| F3 | ✓ | ✓ | 0 (4 frozen) | After F1 — needs AI text to render; DNS prerequisite |
| F4 | ✓ | ✓ | 0 (3 frozen) | After F1 — exports need AI text |
| F5 | ✓ | ✓ | 0 (4 frozen) | F5a unblocks F1; F5b stacks |

**All decisions frozen** in
[decision-pass/DECISION_MATRIX.md](decision-pass/DECISION_MATRIX.md).
No open product questions remain.

---

## Strengths discovered

The audit found existing infrastructure that significantly reduces
Block F's scope:

1. **F1 worker exists** (`app/workers/tasks/ai_generation.py`, 300
   LOC). Generates ru/uz/uz_cyrl in one batch, has template fallback,
   already integrated with Block D D4 autopost hook
   (`_enqueue_autopost`) and A4 push hook
   (`_notify_sellers_after_generation`).
2. **`Listing.ai_description_{ru,uz,uz_cyrl}`** columns shipped in
   Block A V2.0 — no migration to surface these.
3. **`Listing.raw_text`, `TelegramListing.raw_text`, `OLXListing.raw_text`**
   all persisted. F1's "show original" expander is read-only against
   existing data.
4. **`ListingStatus.PENDING_GENERATION` / `GENERATION_FAILED`** enum
   values exist; F1 adds only `DRAFT`.
5. **Block D `check_active_subscription`** is exactly the helper F4's
   paywall needs.
6. **Block D `build_listing_link`** is exactly the URL F3 + F4 need
   for "Open in UcharMarket" CTAs.
7. **D4 `bot_channel_posts.uq_*`** unique constraint provides
   idempotency for F1 regeneration → D4 channel-post update.
8. **Block D D2 `maintenance.prune_behavioral_signals`** pattern
   applies verbatim to F5's `prune_ai_generations`.
9. **Frontend FSD modules from Block D** (autoposting, tariffs,
   phones) are clean precedents for F4 `text-export/` and F5
   `ai-quality/` admin pages.

---

## Hard gaps requiring new code

### Backend new modules

| Module | Purpose | Used by |
|---|---|---|
| `app/services/prompt_registry.py` | Read active prompt; record generation | F1, F5 |
| `app/services/synonym_matcher.py` | Keyword + negation matching | F2 |
| `app/services/text_export.py` | Sandbox-Jinja2 platform renderer | F4 |
| `app/services/seo_meta.py` | Title / desc / og / JSON-LD builders | F3 |
| `app/services/sitemap.py` | Sitemap-index + per-lang paginated | F3 |
| `app/services/quality_alerts.py` | Threshold checks for F5 alerts | F5 |
| `app/workers/tasks/maintenance.prune_ai_generations` | 90-day retention | F5 (Celery beat) |
| `app/workers/tasks/maintenance.purge_abandoned_drafts` | 7-day DRAFT TTL | F1 (Celery beat) |
| `app/api/v1/seo.py` | Jinja2-rendered HTML routes | F3 |
| `app/api/v1/seller_exports.py` | Export endpoints | F4 |
| `app/api/v1/ai_feedback.py` | POST feedback | F5 |
| `app/api/v1/admin_ai.py` | Admin generation review + prompt CRUD | F5 |

### Backend extended

| File | Change |
|---|---|
| `app/workers/tasks/ai_generation.py` | Read prompt from registry; PII scrub raw_text; log to `ai_generations` |
| `app/api/v1/listings.py` | DRAFT endpoint, draft-preview, regenerate, source-text, PATCH guard |
| `app/api/v1/admin.py` (or new `admin_synonyms.py`, `admin_export_templates.py`) | Admin CRUD for synonyms + export templates |
| `app/db/models.py` | New tables; `Listing.last_ai_param_snapshot`; `Seller.export_*`; `DRAFT` enum |

### Backend new HTTP endpoints

- `POST /api/v1/listings/draft` (F1)
- `GET /api/v1/listings/{id}/draft-preview` (F1)
- `POST /api/v1/listings/{id}/regenerate` (F1)
- `GET /api/v1/listings/{id}/source-text` (F1, B2B owner only)
- `POST /api/v1/listings/{id}/analyse-text` (F2)
- `GET /{lang}/listing/{id}/{slug}` (F3, HTML)
- `GET /{lang}/tashkent/{district}` (F3, HTML)
- `GET /{lang}/{deal}/{type}` / `/{district}` / `/{rooms}-rooms/{district}` (F3)
- `GET /sitemap.xml`, `/sitemap-{lang}-listings.xml`, `/sitemap-{lang}-filters.xml`, `/robots.txt` (F3)
- `GET /api/v1/seller/exports/{listing_id}/{platform}` (F4)
- `GET /api/v1/seller/exports/settings` (F4)
- `PATCH /api/v1/seller/exports/settings` (F4)
- `POST /api/v1/ai-feedback` (F5)
- `GET /api/v1/admin/ai/generations` (F5)
- `GET /api/v1/admin/ai/generations/{id}` (F5)
- `GET /api/v1/admin/ai/feedback` (F5)
- `POST /api/v1/admin/ai/feedback/{id}/handle` (F5)
- `GET /api/v1/admin/ai/prompts` (F5)
- `POST /api/v1/admin/ai/prompts` (F5)
- `POST /api/v1/admin/ai/prompts/{id}/activate` (F5)
- `GET /api/v1/admin/synonyms`, `POST`, `DELETE` (F2)
- `GET /api/v1/admin/export-templates`, `PATCH` (F4)

### Migrations needed

| Name | Tables / columns | PR |
|---|---|---|
| `pro_block_f_ai_foundation` | `ai_generations`, `prompt_templates`, `ai_generation_feedback`, `listings.last_ai_param_snapshot`, `listingstatus += 'draft'` | PR-F5a |
| `prp_block_f_synonyms` | `synonym_entries` | PR-F2 |
| `prq_block_f_exports` | `export_templates`, `sellers.export_signature/cta/extra_hashtags` | PR-F4 |

### Frontend new modules

- Stage1.tsx + Stage2.tsx split in `seller/pages/create-listing/` (F1)
- `seller/pages/create-listing/.../ui/SourceTextDrawer.tsx` (F1)
- `seller/feature/text-export/` (F4)
- `seller/feature/ai-feedback/` (F5)
- `admin/pages/ai-quality/` (F5)
- `admin/pages/synonyms/` (F2)
- `admin/pages/export-templates/` (F4)

---

## Risk register

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| OpenAI cost spike on burst parser import | Medium | High | Worker concurrency cap (10); per-day budget alert via `quality_alerts`; hard daily cap env var with template-fallback bypass |
| Two-step publish friction → seller drop-off | Medium | High | Stage 2 perceived speed (poll 2s, p95 generation 3s); manual "Обновить" after 30s; abandoned drafts auto-purged |
| AI text drifts from structured params | High | Medium | F2 covers known params; product accepts that AI text and structured params are two channels of truth |
| SSR Postgres pool exhaustion under crawler burst | Medium | Medium | Dedicated read-only pool; 5min HTTP cache; rate-limit by reverse proxy |
| Sitemap stale for new listings | Low | Medium | Rebuild every 15 min; `lastmod` updated on PATCH; can opt-in Google IndexNow ping post-launch |
| F1 regeneration thrashes D4 channel posts | Low | Medium | `bot_channel_posts.uq_*` constraint; D4 stale-badge UX already wires re-publication to seller's manual "Update" click |
| Prompt activation race (two admins click simultaneously) | Low | Low | Partial unique index `WHERE is_active` enforces ≤1 per kind atomically |
| Seller can't find Stage 2 after closing the tab | Medium | Medium | DRAFT visible in cabinet's "Мои объявления" with "Продолжить публикацию" CTA |
| LLM returns malformed JSON | Low | Medium | Existing worker's `_template_fallback` covers this path; logged as `outcome=invalid_response` |
| PII leaks into `ai_generations.prompt_text` log | Low | High | Pre-prompt PII scrubber for phone + email regex; structured fields like `seller.phone` never enter prompts by construction |
| `ucharmarket.uz` DNS/TLS misconfigured at launch | Medium | High | Ops checklist item with explicit verification step before F3 deploy |
| Synonym matcher false positives flood Stage 2 | Medium | Low | Conservative dictionary curated at launch; context-aware negation check; "Оставить как есть" dismisses for the session |

---

## What I need from product/ops before implementation starts

**Nothing.** All decisions are frozen
([decision-pass/DECISION_MATRIX.md](decision-pass/DECISION_MATRIX.md)).

Ops prerequisites — to be scheduled in parallel with PR-F3:

1. DNS A record for `ucharmarket.uz` → web host.
2. TLS certificate (Let's Encrypt or vendor) provisioned.
3. Reverse-proxy / ingress configuration deployed.
4. Google Search Console + Yandex.Webmaster property verified for
   `ucharmarket.uz`.
5. OpenAI API key with adequate quota provisioned in production env
   (`OPENAI_API_KEY`).
6. Operational decisions on alert recipients
   (`F5_OPENAI_DAILY_BUDGET_USD`, `F5_ALERT_BAD_FEEDBACK_RATE`).

---

## What's NOT covered (and shouldn't be)

- Lifetime regeneration quotas per seller — Phase 2.
- Multiple-variant generation, "give me 3 takes" UI — Phase 2.
- Tone control (neutral / business / warm) — Phase 1.5.
- AI-generated separate title — Phase 1.5; title stays derived from
  structured params.
- A/B testing of prompts in production — `prompt_templates.version`
  reserved; live A/B deferred.
- Personalised AI text per buyer.
- AI image captioning / generation.
- Direct OLX / Instagram API publishing.
- PDF export, bulk export of all listings — Phase 2.
- Image rendering for social cards — Phase 2.

---

## Recommended next phase

**Implementation in PR order from
[EXECUTION_PLAN.md](EXECUTION_PLAN.md).** No additional decision pass
required — all open questions resolved in
[decision-pass/DECISION_MATRIX.md](decision-pass/DECISION_MATRIX.md).

Ops prerequisites (DNS, TLS, OpenAI key, alert recipients) can be
provisioned in parallel with PR-F5a's backend work; they only block
PR-F3 deploy.
