# F2 — Synonym-based mention matching

**Difficulty**: medium (3 days)
**Spec source**: Block F V2.0, §F2
**Dependencies**: F1 (Stage 2 editor exists)
**Blocks**: nothing structurally — UX polish on top of F1

---

## Goal

When a seller types free-form text on Stage 2 ("с кондиционером и
встроенной кухней"), match against a curated dictionary of known
parameter surface forms and surface non-blocking hints when a
parameter is mentioned-but-not-checked or contradicts the structured
state. Helpful, never forced.

---

## Existing infrastructure to reuse

- Block D D5 query parser (`services/query_parser.py`) — same
  rule-based pattern (keyword + simple heuristics; no LLM).
- `core/regions._DISTRICT_ALIASES` — analogous dictionary lookup
  pattern.
- Block D D1 trilingual bot/i18n loader — hint card copy.
- Block A `modules/admin/pages/sources/` — admin CRUD FSD pattern.
- Block D D2 Effector debounce pattern in listing-edit hooks.

---

## What changes

### Database

Migration `prp_block_f_synonyms`:

```sql
CREATE TABLE synonym_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parameter_key   VARCHAR(64) NOT NULL,
    parameter_value VARCHAR(64) NULL,           -- for enum params (e.g. "with_furniture")
    surface_form    VARCHAR(128) NOT NULL,
    language        VARCHAR(8) NOT NULL,         -- "ru" | "uz" | "uz_cyrl" | "*"
    polarity        VARCHAR(8) NOT NULL DEFAULT 'positive',  -- "positive" | "negative"
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX idx_synonym_param_lang   ON synonym_entries (parameter_key, language);
CREATE INDEX idx_synonym_surface_lang ON synonym_entries (surface_form, language);
CREATE UNIQUE INDEX uq_synonym_uniq
    ON synonym_entries (parameter_key,
                        COALESCE(parameter_value, ''),
                        surface_form, language);
```

### Backend

1. **`app/services/synonym_matcher.py`** — new pure-function service:
   ```python
   @dataclass(frozen=True)
   class SynonymMatch:
       parameter_key: str
       parameter_value: Optional[str]
       surface_form: str
       action: str  # "add" | "contradict" | "ok"
       position: int

   async def match_text_to_params(
       db: AsyncSession,
       text: str,
       lang: str,
       current_params: dict[str, Any],
   ) -> list[SynonymMatch]: ...
   ```
   Algorithm:
   - Lowercase `text`; lowercase each `surface_form`.
   - For each (parameter_key, parameter_value, surface_form) loaded
     from `synonym_entries` matching `language IN (lang, '*')`,
     find first occurrence with `text.find(surface_form_lower)`.
   - If found: check 5-token negation window preceding the match
     (`["не", "без", "no", "yo'q"]`). Flip polarity if negation
     present.
   - Compare against `current_params[parameter_key]`:
     - mentioned + checked + same value → `action="ok"` (skipped
       in response unless caller wants full report).
     - mentioned (positive) + not checked → `action="add"`.
     - mentioned (positive) + checked with opposite value (e.g.
       "with mebel" but param says "without_furniture") →
       `action="contradict"`.
     - mentioned (negative — via negation) + checked positive →
       `action="contradict"`.
   - Deduplicate by `parameter_key` (first hit wins).
   - Cap response at 20 matches to bound payload size.

2. **`app/api/v1/listings.py`** — new endpoint:
   - `POST /listings/{id}/analyse-text`:
     - Auth: owner only.
     - Body: `{text, language, current_params}`.
     - Response: `{matches: [SynonymMatch, ...]}`.
     - Read-only; no state change.

3. **`app/api/v1/admin_synonyms.py`** (new module):
   - `GET /admin/synonyms?parameter_key=&language=` — paginated.
   - `POST /admin/synonyms` — bulk-friendly: accepts array of
     entries. Validates `parameter_key` against allowlist (matches
     known structured param fields).
   - `DELETE /admin/synonyms/{id}` — 204.

4. **Seed `synonym_entries`** — operational task at PR ship time.
   Initial set (~30 parameter keys × 3 languages × 3-5 surface forms
   each ≈ 300-400 rows):
   - air_conditioner, balcony, elevator, furniture, parking,
     pets_allowed, renovation_type, gas, internet, security, etc.
   - Per language: ru ("кондиционер", "кондей", "сплит"), uz
     ("kondisioner", "konditsioner"), uz_cyrl ("кондиционер",
     "кондей").

### Frontend

1. **`modules/seller/pages/create-listing/ui/page/Stage2.tsx`**:
   - Debounced effect on text edit (1s after typing stops) → call
     `POST /listings/{id}/analyse-text` with current text +
     current params from Stage 1 store.
   - Render hint cards below editor:
     - **Sequence 1** (`action="add"`): "Кажется, вы упомянули
       кондиционер. Добавить в параметры объявления?"
       Buttons: **Да, добавить** / **Нет, оставить как есть**.
     - **Sequence 2** (`action="contradict"`): "В параметрах
       указано 'без мебели', а в тексте 'с мебелью'. Что верно?"
       Buttons: **Изменить параметр** / **Исправить текст** /
       **Оставить как есть**.
   - When matches ≥ 3 → grouped UI: "Найдено N упоминаний
     параметров. Добавить все?" with expandable list.
   - "Добавить" click → updates Stage 1 store
     (`paramSnapshot.parameter_key = parameter_value`); banner on
     Stage 2 dismisses immediately.
   - "Изменить параметр" click → same as above.
   - "Исправить текст" click → tooltip highlights the surface form
     position in the editor.
   - "Оставить как есть" click → dismisses for session; suppresses
     re-display of the same (parameter_key, action) tuple until
     next page load.

2. **`modules/admin/pages/synonyms/`** (new FSD module):
   - List view with filters (parameter_key, language).
   - Inline-edit row (delete + re-create as edit).
   - Bulk import via CSV paste (parses lines, validates format,
     POSTs in batches of 50).

---

## Failure handling

| Failure | Behaviour |
|---|---|
| Empty `synonym_entries` table at launch | Matcher returns `[]`. UI shows no hints. Acceptable degradation. |
| `analyse-text` request error | Frontend silently drops the update; no toast. |
| False positive (e.g. "балкон" in "вид на балкон соседа") | Negation heuristic handles most; F5 feedback channel captures misses; dictionary curated operationally. |
| Synonym contains regex meta-chars | Stored as plain string; matcher uses `text.lower().find(needle.lower())`, not regex. Safe by construction. |
| 100+ matches against pathologically long text | Capped at 20 in response. |
| Conflicting entries (same surface form mapped to two parameters) | Unique index prevents identical rows; cross-parameter ambiguity resolved by first-match-wins (admin tuning). |

---

## Observability

- `synonym_matcher.matched listing=<id> match_count=<n> langs=<l>`
- `synonym_matcher.contradiction listing=<id> param=<k>`
- `synonym_matcher.hint_accepted listing=<id> param=<k>` (from
  frontend success callback)
- `synonym_matcher.hint_dismissed listing=<id> param=<k>` (idem)
- `admin.synonym.created entry_id=<id> by=<admin>`
- `admin.synonym.deleted entry_id=<id> by=<admin>`

---

## Acceptance criteria

- Type "с кондиционером" in editor (AC param not checked) → hint
  appears within 1.5s.
- Click "Добавить" → AC param checked in Stage 1 on
  back-navigation; hint disappears.
- Type "без мебели" while furniture param is set "with_furniture"
  → contradiction hint with 3 buttons.
- Type "Привет, отличная квартира!" → no hints (subjective
  formulations ignored).
- 5+ matches in long text → grouped UI with one summary hint.
- Admin can create / delete synonym entries via UI.
- Bulk import accepts CSV paste of (parameter_key,
  parameter_value, surface_form, language) rows.
- Dictionary lookup completes in < 50ms p95 for text up to 500
  chars.

---

## Risks

- **False positives flood Stage 2** (Medium / Low). Mitigation:
  conservative dictionary at launch; negation check; session-scope
  dismissal; F5 feedback channel collects misses for prompt
  iteration.
- **Synonym dictionary becomes stale** (Medium / Low). Mitigation:
  admin CRUD UI; weekly review of unmatched mentions from logs.
- **Long text + large dictionary → slow matching** (Low / Low).
  Mitigation: response capped at 20 matches; dictionary held in
  memory after first query (LRU cache); reload on admin
  create/delete.
