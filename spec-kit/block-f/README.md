# Block F — AI-generation and SEO infrastructure

Five tasks that turn AI description generation from a per-seller feature
into platform infrastructure, and lay the SEO foundation that converts
that content into organic search traffic. The economic logic is plain:
high-quality AI text is the foundation, server-rendered web routes
turn it into ranking pages, paid exports turn it into the anchor
deliverable of the Cabinet subscription, and a quality-management
surface keeps the whole thing from rotting over time.

| ID | Task | Difficulty | Phase-1 value |
|----|------|------------|---------------|
| [F1](hard/F1-ai-generation.md) | AI description generation for every listing + two-step publish flow | Hard | Foundation — every other F task assumes AI text exists |
| [F2](medium/F2-synonym-matcher.md) | Synonym-based mention matching while editing | Medium | Keeps structured params and text in sync without nagging |
| [F3](hard/F3-seo-infrastructure.md) | SSR for `/listing/<id>` + filter pages, schema.org, sitemap, hreflang | Hard | Twelve-month-horizon strategic asset |
| [F4](medium/F4-cabinet-exports.md) | Per-platform formatted exports (OLX / Telegram / Instagram / pack) | Medium | Anchor deliverable of the Cabinet subscription |
| [F5](medium/F5-quality-management.md) | Generation logging, in-product feedback, admin review, prompt versioning | Medium | Stops AI quality from degrading silently |

---

## Cross-cutting principle: AI text as platform infrastructure

AI generation is **not** a paid feature. Every listing — manual or
crawled, Russian or Uzbek-speaking seller — gets AI-generated text on
all three locales (ru / uz / uz_cyrl), free, automatically, served to
B2C exclusively. The paid layer is the formatted **export** of that
text to other platforms (F4).

Consequences:

- **B2C never sees `raw_text`.** Parser-imported listings always render
  AI text in the feed. The raw source is retained for ops use and
  exposed only to the listing owner in their cabinet (after claim).
- **Three locales generated in one batch.** Single LLM call returns
  ru / uz / uz_cyrl simultaneously; counted as one generation for
  metrics. No transliteration — each locale is independently generated.
- **DRAFT is a first-class listing status**, not a separate table.
  Stage 1 commits a `Listing(status=DRAFT)`; Stage 2 flips to ACTIVE.
- **Prompts live in DB, not in code.** Admin can iterate without
  redeploy. Block D's `bot/translations` precedent applied to LLM
  prompts.

---

## Reading order

1. [TRUTH_LAYER_AUDIT.md](TRUTH_LAYER_AUDIT.md) — what's already in
   place from Block A (F1 is ~30% scaffolded) vs what needs building.
   **Start here.**
2. [READINESS_REPORT.md](READINESS_REPORT.md) — risk register, blockers,
   what's resolved.
3. [EXECUTION_PLAN.md](EXECUTION_PLAN.md) — PR sequence by real
   dependencies (PR-F1 unblocks everything; F3 parallelisable).
4. Individual specs in `medium/` and `hard/`.
5. [decision-pass/](decision-pass/) — frozen decisions and the
   per-PR operational blueprint.

---

## Discipline lessons applied (from Block D)

- **Existing code is ground truth.** `ai_description_{ru,uz,uz_cyrl}`,
  `Listing.raw_text`, `ai_generation.py` worker, `ListingStatus`
  `PENDING_GENERATION`/`GENERATION_FAILED` already exist. F1 extends;
  it does not re-architect.
- **No new architecture paradigms.** SSR is FastAPI + Jinja2 — same
  Python stack, no Node runtime. Polling Stage 2 — no WebSocket.
- **Block D interfaces are stable.** F consumes
  `services/subscriptions`, `services/deeplink`, `services/autopost`,
  `bot/i18n` — never modifies them.
- **No deferred items shipping unresolved.** Decisions are frozen
  (see [decision-pass/DECISION_MATRIX.md](decision-pass/DECISION_MATRIX.md));
  operational follow-ups (translations review, sitemap submission,
  prompt iteration) are explicitly listed and assigned.
