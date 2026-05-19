# F5 — AI generation quality management

**Difficulty**: medium (4 days; split as 1.5d F5a + 2.5d F5b)
**Spec source**: Block F V2.0, §F5
**Dependencies**: F5a blocks F1 (worker reads prompts from registry);
F5b stacks on top of F1 (feedback button needs Stage 2 to exist).

---

## Goal

Make AI generation operational: every generation logged with full
metadata, sellers can flag bad text via "Не нравится текст",
prompts editable from admin without redeploy, alerts fire when
quality / cost / latency drift. Mirrors Block D D2's
`behavioral_signals` retention pattern.

---

## Existing infrastructure to reuse

- Block D D2 `workers/tasks/maintenance.prune_behavioral_signals` —
  verbatim pattern for `prune_ai_generations`.
- Block D D1 `bot/notifications.notify_admins_*` — alert delivery.
- Existing `services.deeplink` (not used by F5 directly; mentioned
  for completeness — Block D services stay stable).
- Block A admin FSD pattern (`modules/admin/pages/sources/`) —
  template for `admin/pages/ai-quality/`.
- Existing Celery beat schedule (`workers/celery_app.py`) — F5
  adds 2 entries.

---

## What changes

### Database

Migration `pro_block_f_ai_foundation` (covers F5 tables; also adds
F1's DRAFT enum):

```sql
CREATE TABLE prompt_templates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind                VARCHAR(48) NOT NULL,    -- "listing_description"
    version             INTEGER NOT NULL,
    body                TEXT NOT NULL,
    model_hint          VARCHAR(64) NULL,
    is_active           BOOLEAN NOT NULL DEFAULT false,
    notes               TEXT NULL,
    created_by_user_id  UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_prompt_active_per_kind
    ON prompt_templates (kind) WHERE is_active;
CREATE INDEX idx_prompt_kind_version
    ON prompt_templates (kind, version DESC);

CREATE TABLE ai_generations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id          UUID NULL REFERENCES listings(id) ON DELETE SET NULL,
    prompt_template_id  UUID NULL REFERENCES prompt_templates(id) ON DELETE SET NULL,
    model               VARCHAR(64) NOT NULL,
    prompt_text         TEXT NOT NULL,           -- PII-scrubbed
    response_text       TEXT NOT NULL,
    duration_ms         INTEGER NOT NULL,
    input_tokens        INTEGER NULL,
    output_tokens       INTEGER NULL,
    cost_usd_micros     BIGINT NULL,             -- $0.000001 unit
    triggered_by        VARCHAR(32) NOT NULL,    -- "manual" | "auto_parser" | "param_change"
    outcome             VARCHAR(32) NOT NULL,    -- "ok" | "fallback_template" | "timeout" | "rate_limit" | "invalid_response"
    created_at          TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_gen_listing_created
    ON ai_generations (listing_id, created_at DESC);
CREATE INDEX idx_ai_gen_outcome_created
    ON ai_generations (outcome, created_at DESC) WHERE outcome != 'ok';

CREATE TABLE ai_generation_feedback (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id  UUID NULL REFERENCES ai_generations(id) ON DELETE SET NULL,
    listing_id     UUID NULL REFERENCES listings(id) ON DELETE SET NULL,
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category       VARCHAR(32) NOT NULL,
    comment        TEXT NULL,
    handled        BOOLEAN NOT NULL DEFAULT false,
    created_at     TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_fb_handled_created
    ON ai_generation_feedback (handled, created_at DESC);
```

Retention: 90 days for `ai_generations` (pruning daily 04:45).
`ai_generation_feedback` retained indefinitely (low volume,
high signal).

### Backend

1. **`app/services/prompt_registry.py`** — new service:
   ```python
   async def get_active_prompt(
       db: AsyncSession, kind: str = "listing_description"
   ) -> PromptTemplate: ...

   async def record_generation(
       db: AsyncSession,
       *,
       listing_id: Optional[UUID],
       prompt_template_id: Optional[UUID],
       model: str,
       prompt_text: str,
       response_text: str,
       duration_ms: int,
       input_tokens: Optional[int],
       output_tokens: Optional[int],
       cost_usd_micros: Optional[int],
       triggered_by: str,
       outcome: str,
   ) -> AIGeneration: ...
   ```
   - `get_active_prompt` raises if no active row exists (deploy
     prerequisite: seed v1 of `listing_description` prompt).
   - `record_generation` writes a row and commits its own
     transaction so worker failures don't block log persistence.

2. **`app/services/quality_alerts.py`** — new service:
   ```python
   @celery_app.task
   def check_quality_thresholds() -> dict: ...
   ```
   Hourly evaluation:
   - **Bad-feedback rate**: `count(unhandled feedback last 24h) /
     count(generations last 24h)` > `F5_ALERT_BAD_FEEDBACK_RATE`
     (default 0.10).
   - **Generation duration p95**: > `F5_ALERT_P95_DURATION_MS`
     (default 8000) over last hour.
   - **Daily cost spike**: today's cost > 2× rolling 7-day average.
   - **OpenAI 5xx rate**: > `F5_ALERT_OPENAI_5XX_RATE` (default
     0.05) over last 15 minutes.

   Alert on transition false→true only (not every evaluation).
   State stored in Redis: `ai_alert:state:<metric>` with value
   `"firing"` / `"recovered"`.
   Delivery via `bot/notifications.notify_admins_*`.

3. **`app/workers/tasks/maintenance.py`** — extend with
   `prune_ai_generations()`:
   ```python
   @celery_app.task
   def prune_ai_generations() -> dict:
       cutoff = datetime.utcnow() - timedelta(days=90)
       # Direct SQL DELETE on ai_generations where created_at < cutoff.
       # Returns {"deleted_rows": N, "cutoff": "..."}
   ```
   Mirrors Block D D2 `prune_behavioral_signals` shape.

4. **`app/workers/celery_app.py`** — 2 new beat entries:
   ```python
   "prune-ai-generations": {
       "task": "app.workers.tasks.maintenance.prune_ai_generations",
       "schedule": crontab(minute=45, hour=4),
   },
   "check-quality-thresholds": {
       "task": "app.services.quality_alerts.check_quality_thresholds",
       "schedule": crontab(minute=15),
   },
   ```

5. **`app/workers/tasks/ai_generation.py`** — extended:
   - Start of task: `prompt_template = await
     prompt_registry.get_active_prompt(db, "listing_description")`.
     Use `prompt_template.body` as the prompt (replaces hard-coded
     `_build_prompt`).
   - Worker measures `duration_ms`, parses OpenAI response for
     token counts, computes `cost_usd_micros` (model-specific
     rates).
   - On finally: `await prompt_registry.record_generation(...)`
     in its own session (so a worker DB rollback doesn't lose the
     log).

6. **`app/api/v1/ai_feedback.py`** (new router):
   - `POST /ai-feedback`:
     - Auth: any authenticated user.
     - Body: `{generation_id, listing_id, category, comment?}`.
     - Validates `category ∈ {grammar, unnatural, factual,
       too_long, too_short, other}`.
     - Inserts row with `handled=false`.
     - Returns `{id}`.

7. **`app/api/v1/admin_ai.py`** (new router):
   - `GET /admin/ai/generations` — paginated list with filters:
     date_from / date_to / lang / model / outcome / has_feedback /
     page. Returns metadata only (no full prompt body in list view).
   - `GET /admin/ai/generations/{id}` — full row including
     prompt_text + response_text.
   - `GET /admin/ai/feedback?handled={bool}&page=` — feedback queue.
   - `POST /admin/ai/feedback/{id}/handle` — marks `handled=true`.
   - `GET /admin/ai/prompts?kind=` — versions list per kind.
   - `POST /admin/ai/prompts` — create new version
     (`is_active=false` initially).
   - `POST /admin/ai/prompts/{id}/activate` — atomic activation:
     ```python
     async with db.begin():
         await db.execute(
             update(PromptTemplate)
             .where(PromptTemplate.kind == row.kind)
             .values(is_active=False)
         )
         row.is_active = True
     # Partial unique index guarantees ≤1 active per kind atomically.
     ```

### Frontend

1. **`modules/seller/feature/ai-feedback/`** (new FSD module):
   - `ui/FeedbackLink.tsx`: subtle "Не нравится текст" link.
   - `ui/FeedbackModal.tsx`: modal with 6 category radios + optional
     comment textarea + Cancel / Submit buttons.
   - `model/effects/index.ts`: `submitFeedbackFx({generation_id?,
     listing_id, category, comment?})`.
   - Integration: rendered on Stage 2 + Master-record detail.

2. **`modules/admin/pages/ai-quality/`** (new FSD module):
   - Top-level tabs: **Метрики** / **Генерации** / **Очередь
     обратной связи** / **Промпты**.
   - **Метрики** tab: counts of generations by outcome (today / 7d
     / 30d); average duration p95; total cost; bad-feedback rate;
     unhandled feedback count.
   - **Генерации** tab: filterable table; click row → modal with
     full prompt + response side-by-side.
   - **Очередь обратной связи** tab: filterable by handled/unhandled;
     "Mark handled" button per row.
   - **Промпты** tab: list versions per kind; side-by-side diff
     between active and selected version; "Activate" button on
     non-active versions.

---

## Failure handling

| Failure | Behaviour |
|---|---|
| Feedback references pruned generation | `generation_id` FK uses `ON DELETE SET NULL`; `listing_id` keeps grouping signal. |
| Prompt activation race | Partial unique index `WHERE is_active=true` makes 2 active rows impossible at DB level. |
| PII in `prompt_text` | Pre-write PII scrubber from F1 ensures phone+email already redacted before `record_generation` is called. |
| Alert fatigue | Each threshold evaluated hourly; only fires on transition false→true (Redis state). |
| Pruning fails | Logged at WARNING; next run retries. Old rows accumulate slowly; no functional impact. |
| Quality-alerts task fails | Caught; logged; no admin notification (silent failure preferred over alert-spam). |
| Worker can't read active prompt at task start | Hard error — generation fails with `outcome="prompt_unavailable"`. Listing falls back to template via existing `_template_fallback` path. Operational: deploy includes prompt seed; this should never happen. |
| Admin saves invalid prompt body | Server validates Jinja2 parse before insert; rejects with 422. |
| Concurrent admins activate two different versions | Partial unique index allows only one to win; loser sees 409. |

---

## Observability

- `ai_feedback.received generation=<id> category=<c>`
- `ai_feedback.handled feedback=<id> by=<admin>`
- `ai_prompt.activated kind=<k> version=<n> by_user=<id>`
- `ai_prompt.fetched kind=<k> version=<n> active=true`
- `quality_alerts.threshold_breached metric=<m> value=<v> threshold=<t>`
- `quality_alerts.threshold_recovered metric=<m>`
- `maintenance.prune_ai_generations deleted=<n> cutoff=<iso>`

---

## Acceptance criteria

- Every AI generation (success + failure) writes a row in
  `ai_generations`.
- `prompt_text` excludes phone numbers and email addresses (PII
  scrubber verified on 3 sample crawler posts).
- Seller submits feedback → row in `ai_generation_feedback` with
  `handled=false`.
- Admin sees feedback in `/admin/ai/feedback` queue.
- Admin creates new prompt version → next generation uses the new
  body without service restart.
- Activating prompt is atomic — partial unique index enforces
  ≤1 active per kind.
- Threshold breach (simulated bad-feedback rate) → admin Telegram
  alert delivered.
- Threshold recovered → no extra alert (no false-→-recovery spam).
- `prune_ai_generations` deletes rows older than 90 days; 0-row
  case logged but doesn't error.

---

## Risks

- **PII leakage into `ai_generations.prompt_text`** (Low / High).
  Mitigation: pre-prompt scrubber from F1; verified during F1
  acceptance.
- **Alert fatigue from sustained breach** (Medium / Low).
  Mitigation: transition-only firing; Redis state per metric.
- **Prompt activation accidentally breaks production** (Low /
  High). Mitigation: admin previews diff side-by-side; can
  re-activate prior version immediately if regression observed.
- **`ai_generations` table growth at scale** (Medium / Low at
  MVP). At 1000 listings/day × 1.2 attempts avg = 1200 rows/day ×
  365 ≈ 440K rows/year. Mitigated by 90-day retention.
- **Worker pulls active prompt every invocation → DB overhead**
  (Low / Low). Mitigation: optional in-memory LRU cache with 60s
  TTL in `prompt_registry` (out of scope for MVP; add if observed
  >5% worker time spent on prompt fetch).
- **Cost computation drifts from actual billing** (model rates
  change) (Medium / Low). Mitigation: cost rates stored in code
  (constants); update on model migration; budget alert via daily
  cost still catches divergence.
