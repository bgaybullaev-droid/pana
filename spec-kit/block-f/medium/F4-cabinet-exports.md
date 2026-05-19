# F4 — Cabinet exports for paid accounts

**Difficulty**: medium (4 days)
**Spec source**: Block F V2.0, §F4
**Dependencies**: F1 (needs AI text to export), Block D D4
(`check_active_subscription` helper)
**Blocks**: nothing — anchor deliverable of Cabinet subscription

---

## Goal

One-tap formatted export of a listing's AI-generated text to OLX,
Telegram channel, Instagram, and an "all variants" pack. Custom
seller signature/CTA/hashtags applied automatically. Cabinet
subscription required (paywall modal for free users). Base
clipboard copy of plain text remains free for everyone.

---

## Existing infrastructure to reuse

- Block D D4 `services.subscriptions.check_active_subscription(db,
  user_id, CABINET)` — gate every `/seller/exports/*` endpoint.
- Block D D3a `services.deeplink.build_listing_link` — Telegram
  template references this URL.
- `Listing.ai_description_{ru,uz,uz_cyrl}` — content source.
- Block D D1 `bot/i18n.t` — paywall modal copy.
- Block D D4 cabinet FSD pattern
  (`modules/seller/pages/autoposting/`) — clean precedent for
  `modules/seller/feature/text-export/`.
- Block C C1 `/seller/tariffs` route — paywall CTA destination.

---

## What changes

### Database

Migration `prq_block_f_exports`:

```sql
CREATE TABLE export_templates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform      VARCHAR(32) NOT NULL,        -- "olx" | "telegram_channel" | "instagram"
    language      VARCHAR(8) NOT NULL,          -- "ru" | "uz" | "uz_cyrl"
    template_body TEXT NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    updated_at    TIMESTAMP NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_export_template_active
    ON export_templates (platform, language) WHERE is_active;

ALTER TABLE sellers
    ADD COLUMN export_signature      TEXT NULL,
    ADD COLUMN export_cta            TEXT NULL,
    ADD COLUMN export_extra_hashtags VARCHAR(500) NULL;
```

### Backend

1. **`app/services/text_export.py`** — new service:
   ```python
   @dataclass(frozen=True)
   class ExportPayload:
       text: str
       title: Optional[str]     # for OLX
       truncated: bool

   async def render_for_platform(
       db: AsyncSession,
       listing: Listing,
       seller: Seller,
       platform: str,
       lang: str,
   ) -> ExportPayload: ...
   ```
   - Loads active `ExportTemplate(platform, language)` from DB.
     Falls back to `(platform, "ru")` if exact lang missing.
   - Builds context dict: `title`, `price_formatted`, `district`,
     `description` (from `ai_description_{lang}`), `signature` (from
     `seller.export_signature`), `cta` (from `seller.export_cta`),
     `extra_hashtags` (from `seller.export_extra_hashtags`),
     `listing_url` (from D3 `build_listing_link`).
   - Renders via **sandboxed** Jinja2 environment with autoescape ON
     and allowlisted placeholders only (no `if`/`for` blocks).
   - Applies per-platform truncation:
     - OLX title: 70 chars max.
     - Instagram body: 2200 chars max.
     - Telegram body: 4096 chars max (Telegram message limit).
     - OLX body: 9000 chars max (OLX listing limit).
   - Sets `truncated=True` if any cap kicked in.

2. **`app/api/v1/seller_exports.py`** (new router):
   - `GET /seller/exports/{listing_id}/{platform}?lang={lang}`:
     - Auth: seller-owns-listing + `check_active_subscription(CABINET)`.
     - Free user → 402 `{error: "subscription_required"}`.
     - Listing missing AI text → 422 `{error: "ai_text_not_ready"}`.
     - Else → 200 `{text, title, truncated}`.
     - `platform = "pack"` returns concatenated payload:
       ```json
       { "items": [
           {"platform": "olx", "text": "...", "title": "..."},
           {"platform": "telegram_channel", "text": "..."},
           {"platform": "instagram", "text": "..."}
         ]
       }
       ```
   - `GET /seller/exports/settings`:
     - Auth: seller. Returns `{signature, cta, extra_hashtags}`
       from current seller row.
   - `PATCH /seller/exports/settings`:
     - Auth: seller. Body: any subset of the three fields.
     - Updates `Seller.export_*` columns; max 500 chars each;
       Jinja2 placeholder syntax rejected at the input layer
       (signature/CTA stored as plain text).

3. **`app/api/v1/admin_export_templates.py`** (new module):
   - `GET /admin/export-templates` — list all templates grouped by
     platform × language.
   - `PATCH /admin/export-templates/{id}` — body: `{template_body?,
     is_active?}`. Activation flips `is_active` for the new row +
     deactivates the prior active row in a single transaction
     (partial unique index `WHERE is_active` enforces invariant).
   - `POST /admin/export-templates` — create new version (initially
     `is_active=false`).

4. **`app/api/v1/__init__.py`** — register both new routers.

### Frontend

1. **`modules/seller/feature/text-export/`** (new FSD module):
   - `ui/ExportButtons.tsx`:
     - 4 buttons: "OLX", "Telegram-канал", "Instagram", "Пакет".
     - Click → call `GET /seller/exports/{listing_id}/{platform}`.
     - On 200 → `navigator.clipboard.writeText(text)` + toast
       "Скопировано — вставьте в {platform}".
     - On 402 → opens `PaywallModal`.
     - On 422 → toast "Сначала опубликуйте объявление".
   - `ui/PaywallModal.tsx`:
     - Modal: "Эта функция в подписке Кабинет за 99 000 сум".
     - CTA → `navigate("/seller/tariffs")` (Block C C1 route).
   - `model/effects/index.ts`:
     `fetchExportFx({listing_id, platform, lang})`,
     `fetchExportSettingsFx`, `updateExportSettingsFx`.
   - `model/stores/index.ts`: `$exportSettings`,
     `$lastExportPlatform`.

2. **Integration points** (where the buttons appear):
   - `modules/seller/pages/listings/ui/main/ListingDetail.tsx` — at
     the bottom of detail card.
   - `modules/seller/pages/create-listing/ui/page/Stage2.tsx` —
     below "Опубликовать" once status flips ACTIVE.
   - `modules/seller/pages/listings/ui/main/ListingsList.tsx` —
     small "Экспорт" overflow menu on each card.

3. **`modules/seller/pages/profile/ui/...`** — extend seller
   profile-edit page with three new fields:
   - "Подпись для экспорта" (multiline, 500 chars).
   - "Призыв к действию" (multiline, 500 chars).
   - "Дополнительные хэштеги" (single line, 500 chars).
   Calls `PATCH /seller/exports/settings` on save.

4. **`modules/admin/pages/export-templates/`** (new FSD module):
   - List view: 3 platforms × 3 languages = 9 templates with active
     version visible.
   - Edit modal: Monaco-style textarea + placeholder reference
     side panel.
   - Activate button → flips `is_active` atomically.

### Seed data (PR-F4 deploy)

9 initial templates (3 platforms × 3 languages). Sample structure:

**OLX (ru)**:
```
{{ title }}

{{ description }}

{% if cta %}{{ cta }}{% endif %}

{{ signature }}
```

**Telegram (ru)**:
```
🏠 {{ title }}

📍 {{ district }}
💵 {{ price_formatted }}

{{ description }}

{% if cta %}👉 {{ cta }}{% endif %}

— {{ signature }}
{{ listing_url }}
```

**Instagram (ru)**:
```
{{ description }}

{% if cta %}{{ cta }}{% endif %}

📍 {{ district }} • {{ price_formatted }}

#недвижимость #ташкент {{ extra_hashtags }}
```

(uz / uz_cyrl variants follow same structure with localised
labels.)

---

## Failure handling

| Failure | Behaviour |
|---|---|
| Free user requests export | 402 `{error: "subscription_required"}` → frontend paywall modal. |
| Listing missing AI text (still DRAFT or GENERATION_FAILED with no fallback) | 422 `{error: "ai_text_not_ready"}` → frontend toast. |
| Caption exceeds platform limit | Truncated with `…`; `truncated: true` in response; frontend toast informs. |
| Custom signature contains Jinja2 syntax | Stored as plain text (autoescape ON); placeholders allowlisted in template, not in user fields. |
| Subscription expires mid-session | Each request re-checks; same 402 path. |
| Template missing for `(platform, lang)` | Falls back to `(platform, "ru")` automatically; logged at WARNING. |
| Admin saves syntax-invalid template | Server-side Jinja2 parse validation before insert; rejects with 422. |
| User clicks "Пакет" → all 3 platforms × 3 languages = 9 sub-renders | Server returns 9-item array; frontend lets user pick which to copy first. |

---

## Observability

- `text_export.served seller=<id> platform=<p> lang=<l> truncated=<bool>`
- `text_export.paywall_hit user=<id> platform=<p>`
- `text_export.template_fallback_used platform=<p> from_lang=<l> to_lang=ru`
- `text_export.ai_text_missing listing=<id>`
- `admin.export_template.activated id=<id> platform=<p> lang=<l> by=<admin>`

---

## Acceptance criteria

- Subscriber clicks "Экспорт OLX" → text copied to clipboard +
  toast in < 500 ms.
- Free user clicks any export button → paywall modal opens with CTA
  to `/seller/tariffs`.
- DRAFT or generation-failed listing → 422 + toast "Сначала
  опубликуйте объявление".
- Seller saves custom signature → next export includes it.
- Admin edits OLX-ru template body → next OLX-ru export reflects
  the change (no service restart).
- "Пакет" returns 9 variants (3 platforms × 3 langs).
- Template missing for uz_cyrl → falls back to ru; export still
  works.
- Truncation: Instagram body capped at 2200 chars; `truncated: true`.
- Plain clipboard copy of listing text (without F4 buttons) still
  works for all users — no `oncopy` interference.

---

## Risks

- **Platform rules change** (OLX/Instagram modify formatting
  requirements) (Medium / Low). Mitigation: DB-stored templates;
  admin edits without redeploy.
- **Custom signature mis-renders in Telegram** (Markdown syntax in
  user input) (Low / Low). Mitigation: autoescape ON; Telegram
  parses Markdown only when explicitly tagged.
- **Jinja2 template injection from admin error** (Low / Medium).
  Mitigation: sandbox environment; allowlisted placeholders; no
  `if`/`for` blocks; admin-only write access.
- **Subscription expires mid-page-load** (Low / Low). Mitigation:
  per-request check; same paywall path.
- **Paywall reduces conversion** (Medium / Low). Mitigation:
  modal copy emphasizes time savings; CTA links to tariffs page
  where subscription value is laid out.
