# Block F — Decision Matrix (frozen)

> Format mirrors Block D's matrix: every open question is listed
> alongside the locked decision, rationale, and implementation
> impact. Status legend:
>
> 🚨 **Critical** — blocks PR start
> 🔵 **Standard** — defaults stand
> ✅ **Architectural** — cross-cutting platform choice

All 19 rows are frozen. No outstanding product questions.

---

## Cross-cutting decisions (CC)

### CC1 — AI text as platform infrastructure, not a paid feature

🚨 ✅ **DECIDED.** AI generation is free for all listings (manual + crawler).
Paid layer is the formatted **export** of that text (F4), not the
generation itself.

**Rationale**: AI text is the foundation of B2C content quality and
SEO indexability. Locking it behind a paywall undermines the
strategic moat in F3. F4's export layer is the value-add that
sellers will pay for.

**Impact if overridden**: F1 would need a per-seller quota counter
and a paywall on the listing-create flow. None of that is
implemented. Currently scoped: not implementing.

### CC2 — Three-locale generation in one batch

🔵 ✅ **DECIDED.** Single LLM call returns ru / uz / uz_cyrl
simultaneously. Counted as one generation for metrics.

**Rationale**: matches what the F1 worker already does
(`ai_generation.py` returns `{"ru":…, "uz":…, "uz_cyrl":…}`).
No transliteration — each locale independently generated.
Transliteration produces non-idiomatic uz_cyrl.

**Impact**: every metric (`ai_generations_total`, daily cost) is
per-batch, not per-locale.

### CC3 — `raw_text` retained forever; B2C never sees it

🚨 ✅ **DECIDED.** `Listing.raw_text` (and parser side) persists for the
life of the listing. B2C views always show AI text. B2B (cabinet,
after claim) gets a "Показать исходный текст" expander.

**Rationale**: future operational value (claim flow context, prompt
quality analysis); negligible storage cost; zero B2C UX risk.

**Impact if overridden**: claim flow loses context; F5 cannot
investigate prompt deficiencies against actual source material.

---

## F1 — AI generation + two-step publish

### F1-Q1 — DRAFT as enum value vs separate table

🚨 ✅ **DECIDED.** Add `'draft'` to the `listingstatus` enum via
`ALTER TYPE … ADD VALUE` inside `op.get_context().autocommit_block()`.

**Rationale**: reuses every existing listing query path; one-line
schema delta vs. an 80-column duplicate table; precedent set by
Block A PR-G and Block C `prj_wallet_billing` migrations.

**Impact if overridden**: separate `listing_drafts` table with
copy-on-promotion → +2 weeks of rework on every query that filters
listings; rejected.

### F1-Q2 — Stage 2 readiness polling vs WebSocket

🚨 ✅ **DECIDED.** Polling. `GET /listings/{id}/draft-preview` every 2
seconds, max 30 seconds (15 attempts).

**Rationale**: zero new infra. p95 generation ~3s → 1–2 round-trips
typical. WebSocket adds auth pass-through, reverse-proxy buffering,
reconnect logic for a feature with one client.

**Impact if overridden**: WebSocket route + frontend reconnect
handling → +2 days; rejected.

### F1-Q3 — Stage 2 timeout behaviour

🔵 ✅ **DECIDED.** After 30s without `ai_description_ru`, UI shows
"Текст ещё генерируется…" with a manual **Обновить** button.

**Rationale**: avoids a forced status flip on a flaky network;
seller controls when to retry.

**Impact if overridden**: an automatic page reload at 30s could
trigger duplicate Celery tasks; rejected.

### F1-Q4 — DRAFT lifetime / abandonment

🔵 ✅ **DECIDED.** DRAFT listings older than 7 days are purged daily
by `purge_abandoned_drafts` Celery beat at 05:00.

**Rationale**: long enough for seller to come back across a weekend;
short enough that DRAFT photos don't accumulate indefinitely.
Photos GC'd by existing `uploads_gc.cleanup_orphan_uploads`.

**Impact if overridden**: longer TTL → more orphan media; shorter →
seller frustration. 7 days hits the median weekly cadence.

### F1-Q5 — PII scrubbing scope

🚨 ✅ **DECIDED.** Pre-prompt scrubber strips phone (`\+?9?98\d{9}|\d{9}`)
and email regex from `raw_text` before assembly. Replaced with
`[contact]`. Original `raw_text` in DB untouched.

**Rationale**: phones/emails are already in structured fields;
including them in prompts wastes tokens and creates PII-in-logs
risk. Original `raw_text` retained for ops use.

**Impact if overridden**: PII leakage into `ai_generations.prompt_text`
column → compliance risk; rejected.

---

## F2 — Synonym matcher

### F2-Q1 — Matching approach: keyword vs LLM-classifier

🚨 ✅ **DECIDED.** Keyword + simple negation heuristic. No LLM.

**Rationale**: latency budget for editor hints is 200ms p95;
debounce 1s already added; LLM blows both budget and cost without
material quality gain on a closed-vocabulary problem (parameter
names are a known set).

**Impact if overridden**: per-keystroke LLM cost ≈ $0.0003 × edit
frequency → unacceptable economics.

### F2-Q2 — Negation context window

🔵 ✅ **DECIDED.** Scan 5 tokens preceding the surface form for
`["не", "без", "no", "yo'q"]`. If found, flip polarity.

**Rationale**: handles common real-estate-listing phrasings ("без
мебели", "без ремонта", "не угловая"); avoids deep NLP for
diminishing returns.

**Impact if overridden**: full-NLP negation handling needs spaCy
or similar; rejected.

### F2-Q3 — Hint behaviour on dismissal

🔵 ✅ **DECIDED.** Dismissed hints stay hidden for the current edit
session; reappear on a fresh page load. No persistence of "user
dismissed X" preference.

**Rationale**: F2 is a soft assist, not a contract. State leaks
into a UI-preference table would over-engineer.

**Impact if overridden**: per-seller preference table; rejected.

---

## F3 — SEO infrastructure

### F3-Q1 — SSR strategy

🚨 ✅ **DECIDED.** FastAPI + Jinja2Templates for `/{lang}/...`,
`/sitemap*.xml`, `/robots.txt`. TWA stays as the Vite SPA.

**Rationale**: same Python stack; no Node runtime; templates
intentionally minimal (text + photos + CTA, no full TWA UI
duplication).

**Impact if overridden**: Next.js bridge introduces a second
runtime + duplicated routing → +2 weeks + ongoing maintenance
burden; rejected.

### F3-Q2 — Public web host

🚨 ✅ **DECIDED.** `https://ucharmarket.uz` (Uzbekistan ccTLD).

**Rationale**: ccTLD ranking signal for the target market;
brand-aligned; single domain simplifies hreflang and canonical.
TWA stays on a subdomain or path that points at the SPA bundle.

**Impact if overridden**: `.com` weaker ccTLD signal for UZ
searches; rejected.

### F3-Q3 — Indexable depth

🔵 ✅ **DECIDED.** Indexable URLs:
- `/{lang}/listing/{id}/{slug}` (all active listings)
- `/{lang}/tashkent/{district}` (district landing)
- `/{lang}/{deal}/{type}` (deal × type landing)
- `/{lang}/{deal}/{type}/{district}` (2-param combo)
- `/{lang}/{deal}/{type}/{rooms}-rooms/{district}` (3-param combo,
  last indexable depth)

Beyond 3 params: `<meta robots="noindex">` to avoid index bloat.

**Rationale**: matches strategy 4.3 from spec — balance potential
vs. quality dilution; 3-param depth covers the highest-traffic
long-tails (e.g. "купить 2-комн в Чиланзаре") without indexing
millions of low-value pages.

**Impact if overridden**: deeper indexable depth → more rank
dilution; shallower → fewer long-tail captures. Current depth is
the spec-recommended balance.

### F3-Q4 — Sitemap pagination

🔵 ✅ **DECIDED.** Sitemap index file + per-language paginated files
at 50k URLs each (Google's hard limit). Rebuild every 15 minutes
by Celery beat.

**Rationale**: Google's documented constraint; rebuild cadence
balances freshness vs. cost.

**Impact if overridden**: less-frequent rebuild slows
crawl-to-index latency; more frequent burns Postgres I/O without
visible benefit.

---

## F4 — Cabinet exports

### F4-Q1 — Subscription gate enforcement

🚨 ✅ **DECIDED.** `services/subscriptions.check_active_subscription(db, user_id, CABINET)` (Block D D4 helper) gates every `/seller/exports/*`
endpoint. 402 response for unsubscribed users.

**Rationale**: existing helper; per-request check supports
mid-session expiry; no new gate code.

**Impact if overridden**: rebuild what D4 already shipped; rejected.

### F4-Q2 — Template storage: code vs DB

🔵 ✅ **DECIDED.** `export_templates` table with `is_active` partial
unique index per `(platform, language)`. Admin CRUD in
`/admin/export-templates`.

**Rationale**: platforms change their formatting requirements
without notice; in-code templates require a redeploy. DB-stored
templates allow same-day fixes.

**Impact if overridden**: hardcoded templates would force a deploy
on every OLX/Instagram rule change; rejected.

### F4-Q3 — Placeholder syntax: full Jinja2 vs allowlist

🔵 ✅ **DECIDED.** Sandbox-Jinja2 environment with allowlisted
placeholders only: `{{ title }}`, `{{ price_formatted }}`,
`{{ district }}`, `{{ description }}`, `{{ signature }}`,
`{{ cta }}`, `{{ extra_hashtags }}`. No `if`/`for` blocks.

**Rationale**: prevents template-injection-as-XSS; constrains
admin error blast radius; allowlist documents the API.

**Impact if overridden**: full Jinja2 → opens code-execution
surface for admin-editable text; rejected.

---

## F5 — Quality management

### F5-Q1 — `ai_generations` retention

🚨 ✅ **DECIDED.** 90 days raw. Daily pruning by
`maintenance.prune_ai_generations` at 04:45.

**Rationale**: mirrors Block D D2's `behavioral_signals` 180-day
pattern but tighter — `ai_generations` rows carry full prompt +
response text and grow faster. 90 days covers any reasonable
incident-investigation window.

**Impact if overridden**: longer retention → larger DB; shorter →
loss of investigation data.

### F5-Q2 — Prompt activation atomicity

🚨 ✅ **DECIDED.** Partial unique index `WHERE is_active=true` on
`prompt_templates(kind)`. Activation flips old + new in single
transaction; index makes any race condition fail closed.

**Rationale**: schema-level invariant; no application coordination
needed.

**Impact if overridden**: race window where two prompts could be
active per kind → wasteful generations; rejected.

### F5-Q3 — Feedback categories

🔵 ✅ **DECIDED.** Six fixed categories: `grammar`, `unnatural`,
`factual`, `too_long`, `too_short`, `other`. Optional free-text
comment field.

**Rationale**: enough granularity to bucket prompt-iteration work;
"other" + comment covers the long tail.

**Impact if overridden**: free-form categories produce unworkable
analysis; rejected.

### F5-Q4 — Alert thresholds

🔵 ✅ **DECIDED.**
- Bad-feedback rate > 10% over 24h (on transition false→true)
- Generation p95 duration > 8s over last hour
- Daily cost > 2× rolling 7-day average
- OpenAI 5xx rate > 5% over last 15 minutes

All thresholds env-overrideable via `F5_ALERT_*` vars. Hourly
evaluation; admin Telegram message via existing
`bot/notifications.notify_admins_*`.

**Rationale**: thresholds chosen high enough to avoid alert
fatigue; transition-only evaluation prevents spam during sustained
breach.

**Impact if overridden**: tighter thresholds → noise; looser →
missed regressions.

---

## Summary table — 19 frozen decisions

| # | Topic | Frozen | Status |
|---|---|---|---|
| 1 | CC1 AI text free for all | platform infra | 🚨 ✅ |
| 2 | CC2 Three-locale per batch | one LLM call | 🔵 ✅ |
| 3 | CC3 raw_text retained | B2B-only visibility | 🚨 ✅ |
| 4 | F1-Q1 DRAFT enum vs table | enum value | 🚨 ✅ |
| 5 | F1-Q2 Polling vs WS | poll 2s/30s | 🚨 ✅ |
| 6 | F1-Q3 Stage 2 timeout | manual retry | 🔵 ✅ |
| 7 | F1-Q4 DRAFT lifetime | 7 days | 🔵 ✅ |
| 8 | F1-Q5 PII scrubbing | phone+email regex | 🚨 ✅ |
| 9 | F2-Q1 Match approach | keyword + negation | 🚨 ✅ |
| 10 | F2-Q2 Negation window | 5 tokens preceding | 🔵 ✅ |
| 11 | F2-Q3 Hint dismissal | session-scoped | 🔵 ✅ |
| 12 | F3-Q1 SSR strategy | FastAPI + Jinja2 | 🚨 ✅ |
| 13 | F3-Q2 SEO host | ucharmarket.uz | 🚨 ✅ |
| 14 | F3-Q3 Indexable depth | up to 3 params | 🔵 ✅ |
| 15 | F3-Q4 Sitemap pagination | 50k/file, 15min rebuild | 🔵 ✅ |
| 16 | F4-Q1 Subscription gate | D4 helper | 🚨 ✅ |
| 17 | F4-Q2 Template storage | DB table | 🔵 ✅ |
| 18 | F4-Q3 Placeholder syntax | allowlisted Jinja2 | 🔵 ✅ |
| 19 | F5-Q1 Retention | 90 days | 🚨 ✅ |
| 20 | F5-Q2 Prompt activation | partial unique index | 🚨 ✅ |
| 21 | F5-Q3 Feedback categories | 6 fixed | 🔵 ✅ |
| 22 | F5-Q4 Alert thresholds | per-rule env vars | 🔵 ✅ |

🚨 = blocks PR start. **All 22 items locked.**

---

## Approval

This matrix is the source of truth. Implementation begins from
[IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) without
further reopening of any row.
