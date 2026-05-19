# Block D — Readiness Report

> What's blocked, what's known, what needs a product decision before
> implementation can begin.

---

## At a glance

| Block | Spec | Audit | Open Questions | Ready to implement? |
|-------|------|-------|----------------|---------------------|
| D1 | ✓ | ✓ | 5 | After OPEN Q1, Q3 resolved |
| D2 | ✓ | ✓ | 6 | After D1 lands + Q1, Q5 resolved |
| D3 | ✓ | ✓ | 7 | After Q1 (prefix), Q2 (claim entropy) resolved |
| D4 | ✓ | ✓ | 8 | After Q1, Q2, Q7 resolved |
| D5 | ✓ | ✓ | 8 | After Q1 (parser approach), Q8 (currency) resolved |

**Total: 34 OPEN QUESTIONS across the block.** Most have a recommended
answer in the per-task spec; the decision-pass converts them to
DECIDED rules.

---

## Strengths discovered

The audit found existing infrastructure that significantly reduces
Block D's scope:

1. **aiogram 3.x production-ready bot** with FSM, CallbackQuery,
   InlineKeyboard, and outbound messaging — D2 / D4 / D5 reuse all of
   this.
2. **`User.language` already persistent** — D1's job is mostly to add
   the third locale and the Menu Button; the data model is done.
3. **Multi-locale AI text** (`ai_description_ru/uz/uz_cyrl`) on every
   listing — D2 and D4 do not need to call OpenAI at notification
   time. F1 already produced everything.
4. **Frontend `start_param` consumer** is wired and extensible — D3
   doesn't need to build it from scratch.
5. **Idempotent favorites endpoint** — D2's "В избранное" callback
   can call the same path without weird double-tap state.
6. **District dictionary with Cyrillic + Latin aliases** —
   `core/regions.py` is sufficient for D5's fuzzy district match.
7. **Meilisearch already indexes the listing fields D5 needs**
   (district, region, city, microdistrict, metro_station).

---

## Hard gaps requiring new code

### Backend new modules

| Module | Purpose | Used by |
|---|---|---|
| `app/bot/setup.py` | `set_chat_menu_button` on startup | D1 |
| `app/bot/translations/uz_cyrl.yml` | 3rd locale | D1 |
| `app/services/deeplink.py` | Server-side link builder | D3, D2, D4 |
| `app/services/seller_contact.py` | Prefilled `?text=` URL | D2 |
| `app/services/subscriptions.py` (helper) | `check_active_subscription` | D4 |
| `app/services/autopost.py` | Channel post lifecycle | D4 |
| `app/services/query_parser.py` | Free-text → filters | D5 |
| `app/services/bot_search.py` | Meilisearch wrapper for bot | D5 |
| `app/bot/inline.py` | InlineQueryHandler | D5 |

### Backend new endpoints

- `PATCH /api/v1/me/language` (D1)
- `GET  /api/v1/deep-links/{id}` (D3)
- `POST /api/v1/seller/autopost/connect` (D4)
- `POST /api/v1/seller/autopost/disconnect` (D4)
- `GET  /api/v1/seller/autopost/posts` (D4)
- `POST /api/v1/seller/autopost/posts/{id}/update` (D4)

### Migrations needed

| Name | Tables / columns | PR |
|---|---|---|
| `prl_deep_link_payloads` | `deep_link_payloads`, `deep_link_events`, `claim_invites`, `users.referred_by_user_id`, `users.referral_source` | PR-D3a |
| `prm_behavioral_signals` | `behavioral_signals` | PR-D2 |
| `prn_autopost` | `sellers.autopost_*` cols, `bot_channel_posts`, `listings.version` | PR-D4 |

### Frontend new modules

- TWA Settings → Язык picker (D1)
- `modules/seller/pages/autoposting/` (D4)

---

## Risk register

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Bot/TWA language drift | High if D1 skipped | High | Single source: `User.language`. PATCH endpoint + auth-time sync. |
| Telegram 64-char start_param overflow on `filter_` | Medium | Medium | Server-stored payload table (D3 recommendation) |
| Telegram 48h media-edit cutoff blocks D4 | Certain (Telegram limit) | Medium | Graceful 3-option modal; documented constraint |
| Stale Cyrillic users on `language="uz"` | Low | Low | User can re-pick via `/language`; do not force-migrate |
| Tampered `claim_` payload | High if naive impl | High | `claim_invites` table, opaque IDs, single-use, expiry |
| D5 query parser misclassifies common queries | Medium | Medium | Telemetry on parse confidence + dictionary updates as living asset |
| Bot rate limits during mass autopost | Low | Medium | Per-channel serial queue, 1 edit/sec |
| Bot kicked from seller channel | Medium | Low | Detection + cabinet warning + halt until re-verified |
| Push inline-button race condition | Low | Low | Server-side state read on every callback, idempotent favorites |
| Prefilled-text URL truncation | Low | Low | Cap intro at 200 chars |
| `auth_source` vs `referral_source` confusion | Medium | Low | Spec calls out explicit distinction; clear column names |

---

## What I need from product before implementation starts

1. **D1 Q1** — Menu Button text choice (one string, all languages).
2. **D1 Q3** — Canonical storage value for Cyrillic: `"uz_cyrl"` or
   `"uz-cyrl"`?
3. **D3 Q1** — Accept `obj_` as alias to `listing_`, or migrate to
   `obj_`?
4. **D3 Q2** — `claim_` payload: random opaque IDs in
   `claim_invites` table (recommended), or HMAC-signed user_id?
5. **D4 Q1** — Phase-1 / test-period boundary: when does the
   subscription gate flip from "open to all" to "subscribers only"?
6. **D4 Q2** — Default checkbox state on **claimed crawled listings**
   (vs manually created listings)?
7. **D4 Q7** — Per-channel update queue pace (1 edit/sec recommended)?
8. **D5 Q1** — Confirm rule-based parser (recommended) — no LLM in
   hot path.
9. **D5 Q8** — Currency default for "до 35тыс" (UZS recommended).

The remaining 25 OPEN QUESTIONS have a recommended default in their
per-task spec; the decision-pass either confirms or overrides.

---

## What's NOT covered (and shouldn't be)

- TWA internal chat between buyer and seller — Phase 2 (spec defers).
- Multi-channel autoposting — MVP is 1 channel/seller (spec defers).
- Real-time autopost-update without seller's button — Phase 2.
- Referral payouts — Phase 2 (D3 only records).
- Aggregate analytics dashboard — out of MVP scope; raw tables are
  enough.

---

## Recommended next phase

**Decision-resolution pass** (Block C precedent): user runs through
the 34 OPEN QUESTIONS, accepting the recommended default or
overriding. Output: `spec-kit/block-d/decision-pass/DECISION_MATRIX.md`
+ per-topic decision docs as needed (e.g.
`DEEP_LINK_PAYLOAD_FORMAT.md`, `CHANNEL_POST_LIFECYCLE.md`).

After decision-pass: implementation in PR order from EXECUTION_PLAN.

**No implementation should begin before the decision-pass completes.**
This is the same guardrail that prevented mid-stream surprises in
Block C.
