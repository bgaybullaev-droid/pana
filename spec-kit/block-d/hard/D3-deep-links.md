# D3 — Deep Links for marketing

**Difficulty**: hard (4–5 days)
**Spec source**: Block D V2.0, §D3
**Dependencies**: D1 (language picker must run before payload applies
for new users), A1 (claim-flow already exists), B3 (filter surface
unification)
**Blocks**: D2 "Подробнее" button URL, D4 channel-post deep links, E4
marketing material, E5 manual B2B onboarding

---

## Goal

Six payload categories on `/start <payload>` that route the user to the
right place in TWA / right onboarding state — for marketing, sharing,
B2B onboarding, referrals, and future Phase-2 invoicing.

---

## Existing infrastructure to reuse

(see TRUTH_LAYER_AUDIT.md §3 for citations)

- `/start <payload>` parser scaffold — `bot/handlers.py:232-268`. Today
  it only recognizes `link_<phone>`.
- Frontend `start_param` consumer — `app/router/Router.tsx:19-36`.
  Today: `listing_<uuid>` only.
- `Telegram.WebApp.start_param` exposed via `initDataUnsafe`.
- `ListingClaim` infrastructure — `api/v1/claims.py:35-80`,
  `services/account_linking.py`, migration `prd_crawled_claim_reject.py`.
- Bot username config — `config.py:99-100`,
  `frontend/src/shared/lib/constants.ts:1-12`.

---

## Existing prefix vs spec prefix

| Spec V2.0 says | Code today uses | Decision needed |
|---|---|---|
| `obj_<id>` | `listing_<uuid>` | **see OPEN Q1** |

The frontend `StartParamHandler` (Router.tsx:28-30) currently does
`startParam.startsWith("listing_")`. The notification deep-link
builder (`notifications.py:138-141`) emits `startapp=listing_{id}`.
Spec D3 says use `obj_<id>`. **Recommend: keep `listing_` (it's
already live)** and update the spec text. Sub-decision: should we
ALSO accept `obj_` for forward compatibility with marketing materials
that already say `obj_`? Recommend: accept both, prefer one canonical
on outgoing.

---

## What changes

### Backend

1. **`/start` payload dispatcher** — refactor `bot/handlers.py:232-268`
   into a registry:
   ```python
   START_PAYLOAD_HANDLERS: dict[str, Callable] = {
       "link":   handle_payload_link,
       "listing": handle_payload_listing,   # (or "obj")
       "filter": handle_payload_filter,
       "claim":  handle_payload_claim,
       "agent":  handle_payload_agent,
       "ref":    handle_payload_ref,
       "inv":    handle_payload_inv,  # stub for Phase 2
   }
   ```
   Unknown prefix → tihaya degradation: open TWA normally, log to
   metrics with prefix label.

2. **Language-first for new users**: if user is new and chooses
   language at `/start`, save the payload in FSM state and apply it
   **after** the language callback fires.

3. **`obj_` / `listing_` handler**: pass listing_id to TWA via
   `start_param`. Frontend already routes correctly (`/listings/:id`).

4. **`filter_` handler**:
   - Telegram limit: payload total ≤ 64 chars. Subtract `filter_` (7)
     leaves ≤ 57 chars.
   - Option A (recommended): server-stored DeepLinkPayload table —
     `deep_link_payloads(id text(12), filters jsonb, created_at,
     used_count)`. The shareable URL contains the short id; on
     `/start filter_abc123def4` the bot looks up the row and pushes
     the JSON into `start_param` (still ≤64) as
     `filter_abc123def4` → TWA fetches via a new endpoint
     `GET /deep-links/{id}` → applies filter state.
   - Option B: compact ASCII encoding (`chilonzor_2r_buy`) — works
     for simple cases but breaks when filters get richer.
   - Recommend A; B is reserved for hand-built marketing slugs that
     never change.

5. **`ref_<user_id>` handler**:
   - New columns on User:
     - `referred_by_user_id UUID REFERENCES users(id) NULL`
     - `referral_source TEXT NULL` (free-text bucket: "ad_yandex",
       "tiktok_blogger_x", etc.)
   - On first `/start ref_<id>` for a not-yet-registered user, store
     `referred_by_user_id = <id>`. If user already exists, silently
     ignore (do **not** allow late attribution — abuse vector).
   - Reward logic is Phase 2 (E2: referral program). D3 only records.

6. **`claim_<user_id>` handler**:
   - Verify the `from_user.id` matches `claim_<user_id>` decoding
     (HMAC or signed id) — never trust raw payload (spec security
     bullet). The user_id in the payload is a one-time link to a
     pre-imported seller pending claim. Use a `claim_invite` table:
     `claim_invites(id text(12), pre_imported_user_id UUID,
     issued_at, used_at, used_by_telegram_id)`.
   - On match: redirect TWA to the Found section (the seller's
     pre-aggregated crawled listings, see Block A1/A2). Set
     `Seller.onboarding_state = "claim_invited"`.
   - On mismatch (claim link used by someone else): open normal
     onboarding, log abuse-counter row.

7. **`agent_<channel_id>` handler**:
   - Variant of claim_ for sellers identified by Telegram channel rather
     than phone. Same `claim_invites` table; the lookup key is
     channel username instead of pre-imported user.

8. **`inv_` handler**: empty stub returning "Эта функция скоро
   будет доступна" + open TWA normally. Phase 2.

9. **Deep-link analytics**: new `deep_link_events` table
   `(id, prefix, payload, user_id NULL, is_new_user BOOL, created_at)`.
   Inserted at every `/start <payload>` regardless of prefix validity.
   Lightweight; admin UI is post-MVP.

10. **Server-side deep-link builder**: `backend/app/services/deeplink.py`
    (new). Mirrors `frontend/src/shared/lib/constants.ts:9-12`:
    ```python
    def build_listing_link(listing_id: str) -> str: ...
    def build_filter_link(filters: dict) -> str: ...  # stores DeepLinkPayload
    def build_claim_link(seller_id: str, ttl_hours: int = 168) -> str: ...
    ```

### Frontend

1. **Extend `StartParamHandler`** (`Router.tsx:19-36`) to handle the
   filter case: `filter_<id>` → fetch `/deep-links/<id>` → apply to
   buyer filter store → navigate to home with filters applied.

2. **Extend obj/listing case** (already works) to also accept `obj_`
   prefix.

3. **Found section deep entry** for `claim_/agent_`: route
   `/seller/found` with a banner: "Это объявления, которые мы
   нашли по вашему номеру. Подтвердите свои." — already exists per
   recent Block A work.

4. **404 listing**: when `start_param` is `listing_<id>` and listing
   is gone, show "Это объявление больше не актуально" + CTA
   "Перейти к похожим" (link to home with same district/type filter
   if known).

---

## OPEN QUESTIONS

1. **`obj_` vs `listing_`**: confirm decision. Recommend accept both,
   prefer `listing_` on outgoing (existing notifications keep
   working). Marketing team uses `obj_` if they prefer the spec
   wording.
2. **`claim_` payload entropy / signing**: simple random id in
   `claim_invites` table (recommended), or HMAC-signed user_id in
   the payload itself (smaller payloads, no DB write)? Recommend
   table — supports revocation, single-use, expiry.
3. **`ref_` semantics if user already on UcharMarket**: spec says
   "ignore." Confirm we do **not** retroactively assign.
4. **`filter_` URL TTL**: shareable filter links — never expire, or
   90 days? Spec silent. Recommend never expire (cheap to keep).
5. **Aggregate analytics dashboard**: deep_link_events table is enough
   for SQL queries; do we need an admin UI? Recommend no for MVP —
   product can run SQL.
6. **Should `link_<phone>`** (existing) be migrated into the new
   registry, or kept as a special case? Recommend migrate, single
   dispatcher.
7. **`agent_<channel_id>` source**: how is the channel identifier
   provided? `@channel_username`? Confirm format.

---

## Acceptance criteria

- All 7 prefixes parsed (link, listing/obj, filter, claim, agent, ref,
  inv). Unknown prefix → quiet TWA open + analytics row.
- Language picker (D1) runs first for new users; payload applied
  after.
- `filter_<id>` → `deep_link_payloads` row → TWA applies filters.
- `ref_<id>` → `users.referred_by_user_id` written for new users.
- `claim_/agent_` → only the intended user can consume; mismatched
  users get the normal flow and a row in an abuse log.
- Payload analytics row written for every `/start <payload>`.
- All payloads ≤ 64 chars (Telegram hard limit).
- No payload value is trusted — every privileged action verifies.

---

## Risks

- Payload tampering: `claim_<user_id>` if id is plain — anyone with
  any user_id can attempt claim. The `claim_invites` table approach
  fixes this (random opaque id, single-use, expiry).
- UTM-loss from web ads to Telegram: spec mentions a landing page
  builds a `filter_<id>` before redirect — that's E4's job, but D3
  must support the receiving end (covered by `filter_` handler).
- Migration risk on prefix change: notifications already in the wild
  reference `listing_`. If we ever rename to `obj_`, the old links
  break. **Recommendation: never rename, just accept both.**
