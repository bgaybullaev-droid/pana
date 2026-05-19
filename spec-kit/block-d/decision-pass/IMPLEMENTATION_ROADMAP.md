# Block D — Implementation Roadmap

> **Goal**: a turn-by-turn execution blueprint with zero remaining
> architectural ambiguity. After the user approves the companion
> `DECISION_MATRIX.md`, development can start the same day.
>
> **Audit ground truth**: `../TRUTH_LAYER_AUDIT.md`
> **Status snapshot**: `../READINESS_REPORT.md`
> **Open questions resolved**: `DECISION_MATRIX.md`

---

## Table of contents

1. [Scope & 30-second summary](#scope--30-second-summary)
2. [Reuse inventory — what already exists](#reuse-inventory--what-already-exists)
3. [New infrastructure inventory](#new-infrastructure-inventory)
4. [Migrations — exact DDL](#migrations--exact-ddl)
5. [API contracts — every new endpoint](#api-contracts--every-new-endpoint)
6. [Telegram constraints — hard limits](#telegram-constraints--hard-limits)
7. [Architecture impact — code touch map](#architecture-impact--code-touch-map)
8. [PR sequence with critical path](#pr-sequence-with-critical-path)
9. [Per-task deep dives (D1–D5)](#per-task-deep-dives)
10. [Risk register](#risk-register)
11. [Mandatory decisions before coding](#mandatory-decisions-before-coding)
12. [What can ship today vs deferred](#what-can-ship-today-vs-deferred)

---

## Scope & 30-second summary

Block D = five Telegram-native mechanics that move UcharMarket from
"a TWA that happens to run in Telegram" to "a product that exploits
Telegram for retention and virality."

| ID | Concrete change | Net new LOC (est) | Calendar days |
|----|---|---|---|
| D1 | Menu Button + 3rd locale (uz_cyrl) + TWA language UI + bot↔TWA sync | ~400 | 1.5 |
| D2 | Inline buttons on push (fav/contact/details) + prefilled-text URL + behavioral_signals table | ~700 | 3 |
| D3 | Deep-link payload registry + 7 prefix dispatcher + claim_invites + referral cols | ~900 | 2 |
| D4 | Channel autoposting + 48h cutoff modal + cabinet history view | ~2000 | 6–8 |
| D5 | NL query parser + bot /search + InlineQueryHandler + Meili wrapper | ~1500 | 5–7 |

Total **~17.5 calendar days serial**, ~12 calendar days with parallel
work after PR-D1 and PR-D3a land. Three Alembic migrations. Seven
new service modules. Six new HTTP endpoints. Two new frontend
modules (Settings → Language; Seller → Autoposting).

The work is **not** evenly distributed: D4 alone is ~40% of effort.
If we need to ship faster, D4 can be split (connect/verify first;
update/delete second) or deferred a sprint.

---

## Reuse inventory — what already exists

Verified directly against source (see TRUTH_LAYER_AUDIT for citations).
**Do not rebuild these; import or extend.**

### Bot platform
| Asset | Path | Reused by |
|---|---|---|
| aiogram 3.x dispatcher with FSM | `backend/app/bot/main.py`, `bot/handlers.py:1-100` | D1, D2, D3, D4, D5 |
| `/start` handler with payload arg | `bot/handlers.py:225-312` | D3 (extended) |
| `/language` command | `bot/handlers.py:320-323` | D1 (extended) |
| `callback_query` router infrastructure | `bot/handlers.py:1541-1635` (claim_crawled / reject_crawled precedent) | D2 (`fav_add`/`fav_remove`) |
| Outbound bot messaging helpers | `bot/notifications.py:17-181` | D2 (push), D4 (channel posts) |
| InlineKeyboard helpers | `bot/keyboards.py:14-231` | D1 (3rd button), D2, D4 |
| Bot i18n loader | `bot/i18n.py:1-117` | D1 (add uz_cyrl) |

### Backend services
| Asset | Path | Reused by |
|---|---|---|
| `User.language` column (String(10)) | `db/models.py:174` | D1 — single source of truth |
| AI description (3 locales) per listing | `db/models.py:508-510` (`ai_description_ru/uz/uz_cyrl`) | D2 push, D4 channel post |
| F1 AI generation worker | `workers/tasks/ai_generation.py` | D4 channel post body |
| Idempotent favorites endpoint | `api/v1/favorites.py:244-265` | D2 inline button → direct service call |
| Saved-search push pipeline | `workers/tasks/notifications.py:366-401` | D2 (gains `reply_markup`) |
| Crawled-match push with reply_markup | `workers/tasks/crawled_match.py:221-268` | D2 reference impl |
| WebApp init_data HMAC verification | `core/security.py:78-146` | D1 sync, D3 entry path |
| Subscription model (CABINET) | `db/models.py:1411-1602` | D4 gate |
| District dictionary (3 scripts) | `core/regions.py:215-376` | D5 parser |
| Meilisearch index `listings` | `services/search_index.py` | D5 search executor |
| Telegram-WebApp wrapper + BackButton | `frontend/src/app/router/Router.tsx:19-73`, `src/shared/lib/telegram/types.ts` | D1, D3 |
| Frontend `start_param` consumer | `frontend/src/app/router/Router.tsx:19-36` | D3 (extended to filter_/obj_) |
| Frontend i18n (3 locales) | `frontend/src/shared/i18n/locales/{ru,uz,uz-cyrl}/` | D1 — already complete |
| Bot username config | `core/config.py:99-100`, `frontend/src/shared/lib/constants.ts:1-12` | D2, D3, D4 |

### Existing patterns to mirror
| Pattern | Source | Apply to |
|---|---|---|
| Alembic enum-add inside `autocommit_block` | `alembic/versions/20260502_prj_wallet_billing.py` | new behavioral_signal_type enum |
| ON CONFLICT additive merge for idempotency | wallet.py service | D3 deep-link analytics writes |
| SELECT FOR UPDATE row-level lock | wallet.py service | D4 channel-post update concurrency |
| BIGINT smallest-currency-unit money storage | wallet.py models | (no money in Block D — N/A) |
| FSD module: `pages/<name>/{model/effects,model/stores,ui/page}` | `modules/seller/pages/tariffs/` | D1 (settings/language), D4 (autoposting) |
| Phone canonicalization to E.164 | `services/account_linking.py` | (already canonical — no change) |

---

## New infrastructure inventory

### New backend modules (services)
| File | Purpose | Used by |
|---|---|---|
| `backend/app/bot/setup.py` | One-shot `set_chat_menu_button` on app startup; idempotent | D1 |
| `backend/app/bot/translations/uz_cyrl.yml` | 3rd-locale bot strings | D1, all of Block D |
| `backend/app/bot/inline.py` | `InlineQueryHandler` registration + executor | D5 |
| `backend/app/services/deeplink.py` | Server-side URL builder + payload table writer | D2, D3, D4 |
| `backend/app/services/seller_contact.py` | Prefilled `?text=` URL builder + intro renderer per lang | D2 |
| `backend/app/services/subscriptions.py` | `check_active_subscription(user_id, type)` helper | D4 |
| `backend/app/services/autopost.py` | Channel publish/update/delete/mark_sold | D4 |
| `backend/app/services/query_parser.py` | NL → ParsedQuery (rule-based) | D5 |
| `backend/app/services/query_parser_dict.yml` | Curated dictionaries (rooms, deal types, property types, units) | D5 |
| `backend/app/services/bot_search.py` | ParsedQuery → Meilisearch → BotSearchResult list | D5 |
| `backend/app/services/behavioral_signals.py` | Single writer for personalization signals | D2, D5 (future), in-app |

### New backend endpoints (HTTP)
| Method | Path | Purpose | Auth |
|---|---|---|---|
| PATCH | `/api/v1/me/language` | Persist language change from TWA | bearer |
| GET | `/api/v1/deep-links/{id}` | Resolve filter_<id> → filter JSON | none |
| POST | `/api/v1/seller/autopost/connect` | Verify bot is admin in seller's channel | bearer (seller) |
| POST | `/api/v1/seller/autopost/disconnect` | Clear channel binding | bearer (seller) |
| GET | `/api/v1/seller/autopost/posts` | Paginated history | bearer (seller) |
| POST | `/api/v1/seller/autopost/posts/{id}/update` | Manual edit trigger; returns `media_too_old` if needed | bearer (seller) |

### New backend bot commands / callbacks
| Trigger | Handler | PR |
|---|---|---|
| `/start <payload>` (registry pattern) | `bot/handlers.py` (refactored dispatcher) | D3 |
| `/start link_<phone>` | unchanged behavior (now in registry) | D3 |
| `/start listing_<id>` / `obj_<id>` | TWA deep-entry | D3 |
| `/start filter_<id>` | Apply filter via `/deep-links/{id}` | D3 |
| `/start claim_<id>` | Claim-invite consumption | D3 |
| `/start agent_<id>` | Channel-based claim variant | D3 |
| `/start ref_<id>` | Referral record (new users only) | D3 |
| `/start inv_<id>` | Phase-2 stub | D3 |
| `/search` (command) | Bot-side search entry | D5 |
| `@bot inline_query` | `InlineQueryHandler` | D5 |
| `fav_add:<listing_id>` callback | Toggle favorite + edit message | D2 |
| `fav_remove:<listing_id>` callback | Toggle off + edit message | D2 |
| `lang_uz_cyrl` callback | Already-supported pattern, just add value | D1 |

### New frontend modules
| Path | Purpose | PR |
|---|---|---|
| `frontend/src/modules/buyer/pages/settings/...` (extend) | Add "Язык / Til / Тил" picker | D1 |
| `frontend/src/modules/seller/pages/autoposting/` (new FSD module) | Cabinet page: connect, history, update buttons | D4 |
| `frontend/src/shared/lib/deepLinks.ts` | Client wrapper for filter-/obj-/ref- payloads on entry | D3 |

---

## Migrations — exact DDL

Three Alembic revisions, in order. All follow conventions from
Block A/B/C: file naming `YYYYMMDD_pr<letter>_<short_name>.py`,
enum-additions wrapped in `autocommit_block`.

### Migration 1 — `prl_deep_link_payloads` (PR-D3a)

```python
"""prl_deep_link_payloads — D3 deep-link infrastructure"""

revision = "prl_deep_link_payloads"
down_revision = "prk2_align_billing_enum_names"

def upgrade():
    # users — referral tracking
    op.add_column("users", sa.Column("referred_by_user_id",
        UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("users", sa.Column("referral_source",
        sa.String(64), nullable=True))
    op.create_index("ix_users_referred_by_user_id", "users",
        ["referred_by_user_id"])

    # short-id → filter JSON
    op.create_table("deep_link_payloads",
        sa.Column("id", sa.String(12), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),          # "filter" only for MVP
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False),
        sa.Column("used_count", sa.Integer, nullable=False, server_default="0"),
    )

    # claim invites — single-use, expiring
    op.create_table("claim_invites",
        sa.Column("id", sa.String(12), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),          # "claim" | "agent"
        sa.Column("pre_imported_user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id"), nullable=True),             # for claim_
        sa.Column("channel_username", sa.String(64), nullable=True),  # for agent_
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_telegram_id", sa.BigInteger, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_claim_invites_pre_imported_user_id",
        "claim_invites", ["pre_imported_user_id"])

    # event log for analytics
    op.create_table("deep_link_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()")),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("payload", sa.String(64), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_new_user", sa.Boolean, nullable=False,
            server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False, index=True),
    )

def downgrade():
    op.drop_table("deep_link_events")
    op.drop_table("claim_invites")
    op.drop_table("deep_link_payloads")
    op.drop_index("ix_users_referred_by_user_id", "users")
    op.drop_column("users", "referral_source")
    op.drop_column("users", "referred_by_user_id")
```

### Migration 2 — `prm_behavioral_signals` (PR-D2)

```python
"""prm_behavioral_signals — D2 inline-button + in-app signal feed"""

revision = "prm_behavioral_signals"
down_revision = "prl_deep_link_payloads"

def upgrade():
    op.create_table("behavioral_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("listing_id", UUID(as_uuid=True), nullable=True),  # no FK — survives listing delete
        sa.Column("event_type", sa.String(32), nullable=False),
        # event_type values (no DB enum — keep schema flexible):
        #   fav_add | fav_remove | contact_tap | view | details_tap
        sa.Column("source", sa.String(32), nullable=False),
        # source values:
        #   push_inline | in_app | bot_search | inline_mode
        sa.Column("created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_behavioral_signals_user_created",
        "behavioral_signals", ["user_id", sa.text("created_at DESC")])
    op.create_index("ix_behavioral_signals_listing_event",
        "behavioral_signals", ["listing_id", "event_type"])

def downgrade():
    op.drop_table("behavioral_signals")
```

### Migration 3 — `prn_autopost` (PR-D4)

```python
"""prn_autopost — D4 bot-autopost-to-channel + listing.version"""

revision = "prn_autopost"
down_revision = "prm_behavioral_signals"

def upgrade():
    # Seller — outbound channel binding
    op.add_column("sellers", sa.Column("autopost_channel_username",
        sa.String(64), nullable=True))
    op.add_column("sellers", sa.Column("autopost_channel_id",
        sa.BigInteger, nullable=True))
    op.add_column("sellers", sa.Column("autopost_enabled",
        sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("sellers", sa.Column("autopost_verified_at",
        sa.DateTime(timezone=True), nullable=True))

    # Listing — version counter; ON UPDATE bumped by service layer
    op.add_column("listings", sa.Column("version",
        sa.Integer, nullable=False, server_default="1"))

    op.create_table("bot_channel_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()")),
        sa.Column("listing_id", UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seller_id", UUID(as_uuid=True),
            sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("channel_id", sa.BigInteger, nullable=False),
        sa.Column("message_id", sa.BigInteger, nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False),
        sa.Column("last_edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_listing_version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="live"),
        # status values: live | sold_marker | deleted
    )
    op.create_unique_constraint("uq_bot_channel_posts_listing_channel",
        "bot_channel_posts", ["listing_id", "channel_id"])
    op.create_index("ix_bot_channel_posts_seller_status",
        "bot_channel_posts", ["seller_id", "status"])

def downgrade():
    op.drop_index("ix_bot_channel_posts_seller_status", "bot_channel_posts")
    op.drop_constraint("uq_bot_channel_posts_listing_channel",
        "bot_channel_posts")
    op.drop_table("bot_channel_posts")
    op.drop_column("listings", "version")
    op.drop_column("sellers", "autopost_verified_at")
    op.drop_column("sellers", "autopost_enabled")
    op.drop_column("sellers", "autopost_channel_id")
    op.drop_column("sellers", "autopost_channel_username")
```

---

## API contracts — every new endpoint

### `PATCH /api/v1/me/language` (D1)

Request:
```json
{ "language": "ru" | "uz" | "uz_cyrl" }
```

Response 200:
```json
{ "language": "uz_cyrl" }
```

Behavior:
- Writes `User.language`.
- Validates against `SUPPORTED_LANGUAGES`.
- Does NOT propagate to currently-queued push messages (those keep
  their original language).

### `GET /api/v1/deep-links/{id}` (D3)

Response 200:
```json
{
  "id": "abc123def4",
  "kind": "filter",
  "payload": {
    "district": "chilonzor",
    "rooms_min": 2,
    "rooms_max": 2,
    "price_max_uzs": null,
    "deal_type": "sale"
  }
}
```

Response 404 if id unknown / expired (not expired for filter_ per
decision-pass; reserved for future kinds).

Side-effect: `deep_link_payloads.used_count += 1` (ON CONFLICT-safe).

### `POST /api/v1/seller/autopost/connect` (D4)

Request:
```json
{ "channel": "@my_real_estate_channel" }
```

Response 200:
```json
{
  "status": "verified",
  "channel_id": -1001234567890,
  "channel_username": "my_real_estate_channel",
  "verified_at": "2026-05-13T12:00:00Z"
}
```

Response 400 cases:
- `bot_not_admin` — bot is not an admin of the channel.
- `bot_lacks_post_permission` — admin but `can_post_messages=false`.
- `channel_not_found` — username invalid.
- `channel_not_public` — private channel + bot also not admin
  (cannot resolve).

Behavior:
- Calls `bot.get_chat(@username)` → channel_id.
- Calls `bot.get_chat_member(channel_id, bot_self_id)` → checks
  status="administrator", `can_post_messages=True`.
- Posts a sticker or 1-line "Канал подключён" message; immediately
  deletes it. If post succeeds → verified.
- Writes `Seller.autopost_*` columns.

### `POST /api/v1/seller/autopost/disconnect` (D4)

Response 200: `{ "status": "disconnected" }`

Behavior:
- Clears `Seller.autopost_*` columns.
- Existing `bot_channel_posts` rows are **kept** (per decision-pass) —
  posts in the channel are left as-is.

### `GET /api/v1/seller/autopost/posts` (D4)

Query: `?page=1&page_size=20`

Response 200:
```json
{
  "items": [
    {
      "id": "uuid",
      "listing_id": "uuid",
      "listing_title": "3-комн, Чиланзар",
      "posted_at": "2026-05-13T12:00:00Z",
      "last_edited_at": null,
      "is_stale": true,
      "status": "live",
      "telegram_message_url": "https://t.me/my_real_estate_channel/45"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 137
}
```

### `POST /api/v1/seller/autopost/posts/{post_id}/update` (D4)

Request:
```json
{ "force_text_only": false }
```

Response 200 (success):
```json
{ "result": "updated", "last_edited_at": "2026-05-13T12:00:00Z" }
```

Response 200 (needs user choice):
```json
{
  "result": "media_too_old",
  "post_age_hours": 73,
  "options": ["text_only", "recreate"]
}
```

When client receives `media_too_old`, it shows the 48h-cutoff modal.
Re-submitting with `force_text_only=true` → text-only edit succeeds.
Submitting `result=recreate` → DELETE old post + new autopost call.

---

## Telegram constraints — hard limits

These are non-negotiable Telegram-platform rules. The implementation
must respect them or it will fail in production.

| Constraint | Limit | Affects | Mitigation in this roadmap |
|---|---|---|---|
| `start_param` max length | 64 chars | D3 all payloads | All prefixes use short opaque IDs (≤12 chars) — `claim_invites.id` and `deep_link_payloads.id` are `String(12)` |
| Media-edit cutoff | 48h after send | D4 | `bot_channel_posts.posted_at` recorded; service computes `now - posted_at` and returns `media_too_old` if past cutoff |
| Outbound messages per bot | ~30 msg/sec global | D2 push, D4 channel posts | Existing Celery queue; D4 per-channel serial queue at 1 edit/sec |
| Outbound messages per chat | ~1 msg/sec | D2 push, D4 channel posts | Per-channel serial queue (1/sec) |
| Inline-mode results | max 50 per response | D5 | Cap at 20 (cleaner UX) |
| Inline-mode response time | <30s hard / <2s UX | D5 | Pre-compiled regexes + Meilisearch (<50ms typical) + 60s Redis cache |
| Inline-mode cache_time | configurable | D5 | Set `cache_time=60` per spec |
| `t.me/<username>?text=` prefill | works for usernames only | D2 | Fallback to `tg://user?id=` without text when handle is missing |
| Bot must be channel admin | `can_post_messages=True` | D4 | `connect` endpoint verifies before persisting binding |
| Caption length | 1024 chars | D4 channel posts | Truncate AI text to ~700 chars + ellipsis |
| `bot.delete_message` | works any age | D4 mark_archived | No special handling — delete always works |
| Block / forbidden user | `TelegramForbiddenError` | D2 push | Existing handler in `notifications.py:366-401` — extends to D4 |
| Bot kicked from channel | `TelegramForbiddenError` on send | D4 | Detect and set `autopost_verified_at=NULL`; surface in cabinet |

---

## Architecture impact — code touch map

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (TWA)                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│  │ Settings → Language  │  │ Seller → Autoposting │  │ start_param     │ │
│  │ (D1, extend)         │  │ (D4, new module)     │  │ handler (D3)    │ │
│  └──────────┬───────────┘  └──────────┬───────────┘  └─────────┬───────┘ │
│             │                         │                        │         │
└─────────────┼─────────────────────────┼────────────────────────┼─────────┘
              │ PATCH /me/language      │ POST /autopost/...     │ GET /deep-links/{id}
              ▼                         ▼                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                           │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│  │ /api/v1/me/language  │  │ /api/v1/seller/      │  │ /api/v1/deep-   │ │
│  │ (new)                │  │   autopost/* (new)   │  │   links/{id}    │ │
│  └──────────────────────┘  └──────────────────────┘  └─────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Services (new)                                                     │  │
│  │  • deeplink.py    builder + analytics writer                       │  │
│  │  • seller_contact.py   prefilled text URL                          │  │
│  │  • subscriptions.py    check_active_subscription helper            │  │
│  │  • autopost.py    channel publish/update/delete                    │  │
│  │  • query_parser.py    NL → ParsedQuery                             │  │
│  │  • bot_search.py    Meilisearch wrapper                            │  │
│  │  • behavioral_signals.py    single writer                          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────┬────────────────────────┘
                   │                              │
                   ▼                              ▼
┌──────────────────────────────────┐  ┌───────────────────────────────────┐
│  BOT (aiogram, same process)     │  │  WORKERS (Celery)                 │
│  ┌────────────────────────────┐  │  │  ┌─────────────────────────────┐  │
│  │ Existing /start handler    │  │  │  │ Existing crawled_match push │  │
│  │ — refactored to registry   │  │  │  │ — pattern reused in D2      │  │
│  │ (D3)                       │  │  │  └─────────────────────────────┘  │
│  └────────────────────────────┘  │  │  ┌─────────────────────────────┐  │
│  ┌────────────────────────────┐  │  │  │ Existing saved_search push  │  │
│  │ New /search command (D5)   │  │  │  │ — gains reply_markup (D2)   │  │
│  │ + InlineQueryHandler       │  │  │  └─────────────────────────────┘  │
│  └────────────────────────────┘  │  │  ┌─────────────────────────────┐  │
│  ┌────────────────────────────┐  │  │  │ New autopost dispatcher     │  │
│  │ New callbacks fav_add /    │  │  │  │ on Listing status events    │  │
│  │ fav_remove (D2)            │  │  │  │ (D4)                        │  │
│  └────────────────────────────┘  │  │  └─────────────────────────────┘  │
│  ┌────────────────────────────┐  │  └───────────────────────────────────┘
│  │ New: setup.py              │  │
│  │ set_chat_menu_button       │  │
│  │ at app startup (D1)        │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

### Files touched (modified, not new)

| File | Change | PR |
|---|---|---|
| `backend/app/bot/handlers.py` | Refactor /start to registry; add fav_add/fav_remove callbacks; add /search; add lang_uz_cyrl support | D1, D2, D3, D5 |
| `backend/app/bot/keyboards.py` | Add 3rd language button | D1 |
| `backend/app/bot/i18n.py` | Add uz_cyrl to SUPPORTED_LANGUAGES; uz→uz_cyrl mapping | D1 |
| `backend/app/bot/main.py` | Register inline_router; call setup.set_menu_button | D1, D5 |
| `backend/app/bot/notifications.py` | (read-only — unchanged) | — |
| `backend/app/workers/tasks/notifications.py` | `send_telegram_notification` gains optional `reply_markup` param; saved-search push passes new keyboard | D2 |
| `backend/app/workers/tasks/ai_generation.py` | (unchanged) | — |
| `backend/app/api/v1/__init__.py` | Register autopost, deeplinks routers; PATCH me/language route | D1, D3, D4 |
| `backend/app/api/v1/auth.py` | On first auth, write User.language from initData if null | D1 |
| `backend/app/db/models.py` | Add Seller.autopost_*; Listing.version; BotChannelPost; DeepLinkPayload; ClaimInvite; DeepLinkEvent; BehavioralSignal models | D2, D3, D4 |
| `backend/app/services/listings.py` (or equivalent) | Hook autopost on status transitions | D4 |
| `frontend/src/app/router/Router.tsx` | StartParamHandler extension for filter_/obj_ | D3 |
| `frontend/src/modules/buyer/pages/settings/ui/page/Page.tsx` | Language picker UI | D1 |
| `frontend/src/shared/i18n/index.ts` | Sync from User.language on auth | D1 |

---

## PR sequence with critical path

```
Time →
┌──────┐
│ D1   │ ─── unblocks everything (1.5d)
└──┬───┘
   │
   ▼
┌──────┐
│ D3a  │ ─── unblocks D2 (Подробнее URL) and D4 (post URL) (2d)
└──┬───┘
   │
   ├───────────────┬───────────────┐
   ▼               ▼               ▼
┌──────┐       ┌──────┐         ┌──────┐
│ D2   │       │ D4   │         │ D5   │
│ (3d) │       │ (6-8d)│        │ (5-7d)│
└──────┘       └──────┘         └──────┘
```

**Critical path: D1 → D3a → max(D2, D4, D5)**

Serial: 17.5 days. Parallel after D3a: ~12 days.

### PR-D1 (1.5 days)
1. **Backend**:
   - `bot/i18n.py:14` → `SUPPORTED_LANGUAGES = ("ru", "uz", "uz_cyrl")`
   - Create `bot/translations/uz_cyrl.yml` (copy uz.yml, transliterate via existing tooling or hire native pass)
   - Update `bot/i18n.py:64-70` `language_code` mapping: `"uz" → "uz_cyrl"`
   - `bot/keyboards.py:14-20` add third button
   - `bot/handlers.py:225-312` replace welcome text with trilingual block
   - `bot/handlers.py:326-350` extend lang_* dispatcher to `lang_uz_cyrl`
   - `bot/setup.py` (new) — `set_menu_button()` called from `bot/main.py` at startup
   - `api/v1/users.py` (or new file) — `PATCH /api/v1/me/language` endpoint
   - `api/v1/auth.py` — on first authenticated WebApp request where User.language is the default, write the mapped initData.language_code
2. **Frontend**:
   - Extend `modules/buyer/pages/settings` with language section
   - `shared/i18n/index.ts` — on auth success sync from User.language
   - On change-language call PATCH endpoint
3. **Verify**: bot picker shows 3 buttons, lang chosen reflects in TWA, lang chosen in TWA reflects in bot.

### PR-D3a (2 days)
1. **Migration**: `prl_deep_link_payloads`.
2. **Backend services**:
   - `services/deeplink.py` — `build_listing_link`, `build_filter_link`, `build_claim_link`, `record_deep_link_event`.
3. **Bot**:
   - Refactor `/start` payload parsing into a registry of 7 handlers.
   - Implement each: link (existing), listing/obj, filter, claim, agent, ref, inv (stub).
   - For new users entering with a payload, save payload to FSM state, run language picker, then apply.
   - Every entry writes to `deep_link_events`.
4. **Endpoint**: `GET /api/v1/deep-links/{id}`.
5. **Frontend**:
   - `StartParamHandler` accepts both `listing_` and `obj_`.
   - New: `filter_` → fetch `/deep-links/{id}` → hydrate filter store → navigate to home.

### PR-D2 (3 days)
1. **Migration**: `prm_behavioral_signals`.
2. **Backend**:
   - `services/seller_contact.py` — prefilled text URL builder.
   - `services/behavioral_signals.py` — single writer.
   - Generalize `send_telegram_notification` to accept `reply_markup`.
   - Build `_listing_action_kb(listing, lang)` (3-button: fav/contact/details).
   - Saved-search push code path passes new keyboard.
3. **Bot callbacks**:
   - `fav_add:` / `fav_remove:` — toggle + edit message + write signal.
4. **In-app**: any existing favorite/contact action also writes a signal (consolidate).
5. **No frontend changes** primary; verify listing-detail handles `start_param=listing_<id>` (already wired).

### PR-D4 (6–8 days)
Split into D4a (connect + first publish) and D4b (update/delete + 48h modal + history) if time-boxing required.

1. **Migration**: `prn_autopost`.
2. **Backend**:
   - `services/subscriptions.py` — `check_active_subscription(user, type)` Phase-1: returns True for sellers.
   - `services/autopost.py` — `autopost_listing`, `update_post`, `mark_sold`, `delete_post`, `_render_channel_post`.
   - Hook into listing status transitions (in `services/listings.py` or wherever ACTIVE/SOLD/PAUSED/DELETED writes happen — verify with grep before PR opens).
   - Endpoints under `api/v1/autopost.py`.
   - Celery retry queue with backoff.
   - Per-channel serial queue (Redis-backed).
3. **Frontend**:
   - New module `modules/seller/pages/autoposting/` (mirror tariffs/ FSD structure).
   - Listing-create form checkbox.
   - Listing-card "stale" badge + "Update post" button.
   - 48h modal (3 options).

### PR-D5 (5–7 days)
1. **Backend**:
   - `services/query_parser.py` + `query_parser_dict.yml`.
   - `services/bot_search.py`.
   - `bot/inline.py` with `InlineQueryHandler`.
   - `/search` command + free-text fallback heuristic in router.
   - Redis rate-limit per user.
   - Register `inline_router` in `bot/main.py`.
2. **No frontend changes**.

---

## Per-task deep dives

> Each task is treated as: **Why** (justification) — **How** (mechanic) —
> **Where** (integration points) — **Reuse** (existing pattern).

### D1 — Menu Button + language consistency

**Why**: Every recurring user pays a 3-tap tax to enter TWA today
(open chat → find /start message → tap button). Menu Button cuts
that to 1 tap. Trilingual picker eliminates the "bot speaks ru,
TWA speaks uz_cyrl" inconsistency the V2.0 spec forbids.

**How**:
- `bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text=..., web_app=WebAppInfo(url=settings.twa_url)))` — single API call at app startup. Idempotent.
- Three-button picker on `/start` for new users; `/language` re-triggers.
- Frontend Settings UI calls `PATCH /api/v1/me/language` to write the canonical value; localStorage syncs as a cache.
- WebApp init_data → `User.language` ON FIRST auth only (never overwrite explicit choice).

**Where it integrates**:
- `bot/main.py` — call `setup.set_menu_button()` after dispatcher init.
- `bot/i18n.py` — extend `SUPPORTED_LANGUAGES`.
- `bot/keyboards.py:14-20` — add third button.
- `bot/handlers.py:225-312` — welcome text + 3-button keyboard.
- `bot/handlers.py:326-350` — extend lang_* dispatcher (lang_uz_cyrl is just one extra branch).
- `api/v1/users.py` (new file or extend) — PATCH endpoint.
- `api/v1/auth.py` — auth-flow language sync.
- `frontend/src/modules/buyer/pages/settings/` — language section.
- `frontend/src/shared/i18n/index.ts` — auth-time sync.

**Reuse**:
- Existing 2-language picker pattern → just add a button + translation file.
- Existing `PATCH /me/*` endpoint pattern (if any — verify with grep before PR).
- Existing i18n loader.

### D2 — Inline keyboard in push

**Why**: Push without inline buttons forces every user action through TWA — high friction for hot leads, lost signal for personalization. Spec § "поведенческие сигналы для рекомендательной системы" is the recommender's hottest fuel.

**How**:
- Generalize `send_telegram_notification(... reply_markup=None)`.
- 3-button keyboard:
  - **В избранное** — `callback_data="fav_add:<listing_id>"`. Toggles. Edits the message in-place to reflect new state.
  - **Написать продавцу** — `url=<prefilled t.me/...?text=...>`. Pure link, no callback. Sender's language used for the intro.
  - **Подробнее →** — `url=<listing-deep-link>`. Opens TWA at the listing.
- Every press writes one `behavioral_signals` row with `source=push_inline`. In-app actions write `source=in_app`. Future bot-search clicks write `source=bot_search`. Single table; future recommender reads from here.

**Where it integrates**:
- `workers/tasks/notifications.py:366-401` — add `reply_markup` param.
- `bot/handlers.py:1541+` — add `fav_add:` / `fav_remove:` callbacks next to the existing `claim_crawled:` / `reject_crawled:` block (same pattern).
- `services/seller_contact.py` (new) — `build_seller_chat_url(listing, sender_lang)`.
- `services/behavioral_signals.py` (new) — `record_event(user, listing, event_type, source)`.
- `api/v1/favorites.py` — existing service function called directly from the bot callback (avoid HTTP round-trip).

**Reuse**:
- `crawled_match.py:221-268` `_send_push()` is the canonical reference for "push with reply_markup".
- `favorites.py:244-265` is idempotent — `fav_add:` callback calls it; if "already in favorites" returned, toggle to remove.
- `services/deeplink.py` from D3 builds the Подробнее URL.

### D3 — Deep links

**Why**: Marketing CPM is wasted if every clickthrough lands on a generic chat. Deep links are the difference between "ad → bot → user fumbles → maybe converts" and "ad → bot → filtered listing → contact." Spec emphasises this is multiplicative ROI on existing ad budgets.

**How**:
- All payloads ≤64 chars. Filter payloads use a short opaque ID indexed into `deep_link_payloads`. Claim/agent payloads use a short ID indexed into `claim_invites` (single-use, expiring).
- `/start <payload>` dispatches by prefix to handlers. Unknown prefix → quiet open + analytics row (graceful degradation).
- New users entering with a payload: save in FSM state, run language picker, then apply.

**Where it integrates**:
- `bot/handlers.py:225-312` refactored: dispatch table `START_PAYLOAD_HANDLERS = {"link":..., "listing":..., "obj":..., "filter":..., "claim":..., "agent":..., "ref":..., "inv":...}`.
- `services/deeplink.py` (new) — single builder used by frontend share, bot push, D4 channel posts.
- `frontend/src/app/router/Router.tsx:19-36` extended: accept `obj_` as alias to `listing_`; handle `filter_<id>` via fetch-then-apply.
- New endpoint `GET /api/v1/deep-links/{id}` reads `deep_link_payloads`.
- `api/v1/users.py` writes referral on first-time user only.

**Reuse**:
- `ListingClaim` model (`api/v1/claims.py:35-80`) and migration `prd_crawled_claim_reject.py` — claim_ payloads consume `claim_invites` and then trigger the existing claim path.
- Existing `link_<phone>` handler — folded into the new dispatcher unchanged.
- Frontend `StartParamHandler` is a 1-line extension.

### D4 — Bot autoposting

**Why**: Anchor feature of Cabinet subscription (99 000 sum/mo). Without it the subscription has no concrete deliverable; with it, sellers automate Telegram-channel rituals AND we get viral B2C traffic via "Через @ucharmarket_bot" footers.

**How**:
- Seller adds bot as admin to their channel → `/seller/autoposting` → "Verify" → server confirms admin + post permissions.
- Listing → ACTIVE: enqueue `autopost_listing(listing)` if seller opted in.
- Listing edited: increment `Listing.version`; cabinet shows "stale" badge; seller manually clicks "Update post" → server attempts edit.
- 48h media-edit cutoff: server returns `media_too_old` for media-changes past 48h; cabinet shows 3-option modal.
- Listing → SOLD: edit caption to "ПРОДАНО"/"СОТИЛДИ"/"СОТИЛДИ" overlay (per locale + per deal_type=SALE/RENT).
- Listing → PAUSED/DELETED/EXPIRED: `bot.delete_message`.

**Where it integrates**:
- `services/autopost.py` (new).
- `services/listings.py` (existing — verify path with grep) — status transition hooks.
- `services/subscriptions.py` (new) — gate check (Phase-1: always True for sellers).
- `api/v1/autopost.py` (new).
- `bot/main.py` — bot instance accessed for outbound sends (existing pattern: `get_bot_instance()` from `bot/notifications.py:171-181`).
- `db/models.py` — `BotChannelPost` model; Seller columns; Listing.version.
- `frontend/src/modules/seller/pages/autoposting/` (new FSD module mirroring `tariffs/`).
- `frontend/src/modules/seller/pages/create-listing/` — checkbox "Опубликовать в моём канале".
- `frontend/src/modules/seller/pages/listings/` — "stale" badge + "Update post" button on cards.

**Reuse**:
- `Subscription` model (Block C) — used as-is, just gain a helper.
- AI text on three locales — used as-is.
- aiogram `bot.send_photo`, `bot.edit_message_caption`, `bot.edit_message_media`, `bot.delete_message` — all native; no new HTTP wiring.
- FSD module structure from `seller/pages/tariffs/`.

### D5 — In-bot search + Inline Mode

**Why**: A meaningful slice of the target audience habituates to bot-search rather than app-search. Today they hit a wall. Spec elevates this to "primary path" for these users in V2.0; Inline Mode is the viral overlay.

**How**:
- Rule-based query parser (no LLM in hot path — cost + latency).
- District/keyword dictionaries curated alongside A7's parser dictionary.
- Bot `/search` and free-text heuristic dispatch to parser → `bot_search.py` → Meilisearch → compact result list.
- InlineQueryHandler same path, with up to 20 results.
- Result language = `User.language` (or Telegram `language_code` for unknown users in Inline Mode).

**Where it integrates**:
- `services/query_parser.py` (new) — pure function `parse(text, lang) → ParsedQuery`.
- `services/bot_search.py` (new) — translates ParsedQuery to Meili query, calls index, formats results.
- `bot/handlers.py` — `/search` command + free-text fallback heuristic.
- `bot/inline.py` (new) — InlineQueryHandler.
- `bot/main.py` — register inline_router.

**Reuse**:
- Meilisearch client (`services/search_index.py`) — `client.index("listings").search(...)` is the call.
- District dictionary (`core/regions.py:215-376`) — `infer_region()` is exactly the fuzzy-match function we need.
- D3 deep-link builder for result URLs.

---

## Risk register

| Risk | Likelihood | Severity | Where addressed |
|---|---|---|---|
| Bot↔TWA language drift | High if D1 short-circuited | High | `User.language` single source of truth; sync both ways at auth + on PATCH |
| `start_param` overflow | Medium | Medium | Short-ID indirection table (`deep_link_payloads`) |
| Telegram 48h media cutoff | Certain | Medium | `media_too_old` API + 3-option modal |
| Tampered `claim_` payload | High if naive | High | Opaque IDs in `claim_invites`, single-use, expiry, server-validates |
| Race: listing flipped mid-publish | Medium | Low | Re-read listing.status at task start; bail if changed |
| Bot kicked from channel | Medium | Low | Detection + cabinet warning + halt until re-verified |
| Inline-button double-tap | Medium | Low | Server reads current favorite state; idempotent toggle |
| Mass autopost-update overwhelms Telegram | Low | Medium | Per-channel serial queue at 1 edit/sec |
| Query parser misclassifies common queries | Medium | Medium | Telemetry on parse confidence; YAML dictionary iteration |
| Caption overflow (D4) | Medium | Low | Truncate AI text to ~700 chars with ellipsis |
| Prefilled-text URL truncation | Low | Low | Cap intro at 200 chars |
| OpenAI cost surge if D5 went LLM-route | N/A — rule-based per decision | — | Decision: stay rule-based |
| Migration failure on enum add | Low | High | Use `autocommit_block` pattern from Block C |
| `start_param` analytics fire-and-forget loses rows | Low | Low | Best-effort fire; not load-bearing |

---

## Mandatory decisions before coding

These nine decisions block PR-D1 start. The full 34 are resolved in
`DECISION_MATRIX.md` with recommended defaults; the user approves
all 34 in one pass to remove all ambiguity. **Critical nine**:

| # | Topic | Recommended | Rationale |
|---|---|---|---|
| 1 | Menu Button text | "UcharMarket" (single, neutral) | Telegram doesn't accept localized variants for menu button |
| 2 | Canonical Cyrillic value | `"uz_cyrl"` (DB & bot), `"uz-cyrl"` (frontend i18n folder, with alias) | Bot Python convention `_`; frontend i18n already exists with `-`; map at the edge |
| 3 | `obj_` vs `listing_` prefix | Accept both; emit `listing_` | Don't break live notification links |
| 4 | `claim_` entropy | Opaque IDs in `claim_invites` (12-char) | Supports revocation, single-use, expiry; safer than HMAC payload |
| 5 | Phase-1 D4 access | Open to all sellers; `check_active_subscription` returns True | Per spec; flip flag after launch |
| 6 | D4 default checkbox state | `True` for manual listings; `False` for claimed-from-crawler | Avoid flooding channels on day 1 |
| 7 | D4 per-channel update pace | 1 edit/sec, serial per channel | Conservative under Telegram limits |
| 8 | D5 query parser | Rule-based, no LLM in hot path | Latency + cost; YAML dictionary as living asset |
| 9 | D5 currency default | UZS unless "у.е."/"usd"/"$" present | Match Tashkent buyer mental model |

---

## What can ship today vs deferred

### Ship in Phase-1 (this Block D)
- D1 (everything)
- D2 (everything)
- D3: link, listing/obj, filter, claim, agent, ref, inv (stub)
- D4: connect + autopost + update + 48h modal + sold/paused/deleted lifecycle + history view
- D5: form-search in bot, inline mode, fuzzy district + transliteration + simple morphology

### Phase-2 (out of Block D)
- Real-time autopost on listing edits (no manual click) — adds complexity, no clear product win
- Multi-channel per seller — needs UI table; deferred
- Internal chat between buyer and seller in TWA — explicitly out of MVP
- Referral payouts — D3 records; payouts are a separate spec
- LLM-assisted query parsing — only if rule-based misclassification telemetry shows >10% false-negatives after a month
- D4 "update all stale" batch button
- Aggregate analytics dashboard for deep_link_events
- Group push ("5 new listings for your search") — A4 spec mentions a Redis batch window; not in Block D scope but unblocks here

### Never (explicit non-goals)
- Autopost to Instagram / VK / non-Telegram — out of scope
- Voice-input bot search — out of scope
- LLM-driven autopost text generation — F1 already covers
- Auto-translate prefilled chat between sender and recipient — spec forbids
