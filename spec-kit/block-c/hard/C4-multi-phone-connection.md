# C4 — Multi-phone connection for realtors (up to 3 additional)

**Status:** NOT STARTED — `User`, `Seller`, `Listing`, source tables all carry exactly one phone column. No `UserPhone` join table. Block A's `prf_canonicalize_phone` migration explicitly collapsed phones to one-winner-per-canonical. OTP infra is **Telegram-bot-only**, not SMS.
**Complexity:** HARD — schema work + verification flow + parser-side query expansion + listing-create UI + delete-with-active-listings flow + cross-system phone lookup + must not break Block A's claim/A4 paths.
**Block-C V2.0 ref:** C4.
**Why now:** widens claim coverage (a realtor with 3 phones currently shows 1/3 of their portfolio in Found) and removes a major incentive for multi-account abuse — both are core launch-quality concerns.

## What's done

- **Phone columns (single each):**
  - `User.phone` — `String(20)`, nullable. Primary auth identifier.
  - `Seller.phone` — `String(20)`, nullable. Mirror of User.phone for the seller profile.
  - `Listing.phone` — `String(20)`, nullable. The contact phone shown on this listing.
  - `TelegramListing.contact_phone`, `OLXListing.contact_phone` — what the parser scraped.
  - `ListingClaim.otp_phone` — used during the OTP-claim flow.
- **`prf_canonicalize_phone` migration** (`backend/alembic/versions/20260428_prf_canonicalize_phone.py`) normalised every `User.phone` and `Seller.phone` to E.164 (`+998XXXXXXXXX`) and merged duplicates by keeping the latest record. **This established that "one user = one canonical phone" is currently a hard invariant.**
- **OTP infra (Telegram-bot, not SMS):**
  - `backend/app/api/v1/auth.py:767-906` — `request_seller_otp` and `verify_seller_otp` endpoints. Generate 6-digit code, deliver via Telegram bot DM (NOT SMS). Redis-backed: 10-min TTL, 3 attempt cap, 10-min rate-limit window for re-requests.
  - `backend/app/core/security.py:149` — `generate_otp` helper.
- **Phone-suffix matching in claim/A4 (single-column today):**
  - `backend/app/services/seller_crawled_listings.py:31, 40, 72, 105` — `func.right(contact_phone, 9)` against the parsed listing's contact_phone.
  - `backend/app/workers/tasks/crawled_match.py:137` — `func.right(User.phone, 9) == suffix[-9:]`.
  - **Both will need to be expanded** to "phone IN (set of seller's verified phones)".

## What's missing

1. **No `UserPhone` table.** No way to attach more than one phone to an account.
2. **No "additional phones" UI.** No `/seller/profile/phones` route, no "My Numbers" section.
3. **No phone-picker on listing-create.** Today `Listing.phone` defaults to `seller.phone`. There's no select, no override mechanism in the form.
4. **No SMS infrastructure.** Spec says verification via SMS; only Telegram-bot OTP exists. **Major open question** — see Open Questions section.
5. **Parser-side query is single-column.** `seller_crawled_listings_for_user`, `crawled_match` need to expand to a JOIN/IN query.
6. **No delete-with-active-listings flow.** When a phone-on-record is referenced by N listings, what happens on delete?
7. **No re-search trigger after verification.** Spec wants a synchronous re-scan of `TelegramListing` / `OLXListing` for the new phone immediately after verification.
8. **No "after first claim" prompt** to add additional phones.
9. **No A4 fanout adjustment** — `crawled_match.py` doesn't yet know about the multi-phone set.
10. **Rate-limit / abuse vectors** for OTP on additional phone numbers — same Redis pattern can be re-used but separate keys needed.
11. **"Phone already attached to another account" check** — needs to look across all `UserPhone` rows + `User.phone`.

## Path to DONE

This is a multi-PR feature. Recommended split below.

### Step 1 — schema

Migration `prk_user_phone.py`:

```python
op.create_table(
    "user_phones",
    sa.Column("id", UUID, primary_key=True, default=uuid4),
    sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"),
              nullable=False, index=True),
    sa.Column("phone", sa.String(20), nullable=False),  # E.164 canonical
    sa.Column("verified_at", sa.DateTime, nullable=False),
    sa.Column("verification_method", sa.String(16), nullable=False),  # 'sms_otp' | 'tg_otp'
    sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(),
              onupdate=sa.func.now()),
)
op.create_index("uq_user_phone_phone", "user_phones", ["phone"], unique=True)
op.create_index("uq_user_phone_primary", "user_phones",
                ["user_id"], unique=True,
                postgresql_where=sa.text("is_primary = true"))
op.create_index("idx_user_phone_user", "user_phones", ["user_id"])
```

**Backfill:** every existing User with non-null `phone` gets a `user_phones` row with `is_primary=true`, `verified_at=now()`, `verification_method='legacy'`.

```sql
INSERT INTO user_phones (user_id, phone, verified_at, verification_method, is_primary)
SELECT id, phone, NOW(), 'legacy', true
FROM users
WHERE phone IS NOT NULL;
```

`User.phone` stays as the auth-identifier column. The new table is the source of truth for "all verified phones of this user". `is_primary=true` rows correspond exactly to `User.phone`.

### Step 2 — `Listing.contact_phone` semantics

`Listing.phone` becomes officially the **contact phone for this specific listing**, optionally different from any of the seller's verified phones. Recommend renaming the column for clarity (`contact_phone`) — but only if existing code can be safely refactored. Otherwise leave as `phone` and document.

Constraint: at create-time, the contact phone MUST be one of the seller's verified phones (selected from a dropdown). Existing data: every Listing's `phone` is already valid because today it equals the seller's only phone.

### Step 3 — verification endpoint

`POST /sellers/me/phones/request-otp`:

```json
{ "phone": "+998XXXXXXXXX" }
```

Validates format (E.164), checks not already attached anywhere (return `409 phone_in_use` if conflict), generates OTP via the same `generate_otp` helper, delivers via the chosen channel (see Open Questions on SMS vs Telegram). Re-uses the Redis pattern from `auth.py:767-906`.

`POST /sellers/me/phones/verify-otp`:

```json
{ "phone": "+998XXXXXXXXX", "code": "123456" }
```

On success: insert `user_phones` row, expand `crawled_match` lookups, return matched-listings count. On failure: 3-attempt cap, 5-min lockout per spec.

### Step 4 — list / delete endpoints

`GET /sellers/me/phones` → list of attached phones with `is_primary` flag and per-phone listing-count.

`DELETE /sellers/me/phones/{phone_id}`:
- If primary → 400, "primary phone cannot be deleted via UI; contact support".
- If active listings reference this phone → 409 with `affected_listings_count`. Front-end shows the modal.
- Body for the modal action:
  ```json
  { "action": "transfer_to_primary" }   // or
  { "action": "transfer_to_other", "target_phone_id": "<uuid>" }   // or
  { "action": "archive_listings" }
  ```

### Step 5 — synchronous re-search after verify

After a successful verify, run the same query that powers `seller_crawled_listings_for_user` against the newly-verified phone. Return the count + listings. The frontend shows: "По этому номеру найдено N ваших объявлений. Открыть Found?".

Implement as part of the verify endpoint response — it's already query-bounded to one phone; no Celery dispatch needed for the synchronous part. The async part (subscribing the new phone to A4 fanout) is automatic because the `crawled_match` query expansion (Step 6) reads the table directly.

### Step 6 — parser-side query expansion

**Critical change.** Replace single-column suffix match with set-membership.

`backend/app/services/seller_crawled_listings.py`:

```python
# Before
query = select(...).where(func.right(OLXListing.contact_phone, 9) == suffix)

# After
suffixes = (await db.execute(
    select(func.right(UserPhone.phone, 9))
    .where(UserPhone.user_id == user_id)
)).scalars().all()
if not suffixes:
    return []
query = select(...).where(func.right(OLXListing.contact_phone, 9).in_(suffixes))
```

`backend/app/workers/tasks/crawled_match.py:137` — same change pattern. Look up users whose phone-set contains the listing's contact_phone suffix.

### Step 7 — listing-create form: phone picker

Frontend `frontend/src/modules/seller/pages/create-listing/`:

- New select on the form: "Контактный номер".
- Default = primary phone.
- Hidden when seller has only the primary (no extras).
- On submit, the selected phone is passed in the listing payload and stored in `Listing.phone`.

### Step 8 — listing edit: phone change

Same picker on the edit form. `PATCH /listings/{id}` accepts `contact_phone`; validates it's one of the user's verified phones.

### Step 9 — "Add a number?" hint after first claim

Frontend hook on the post-claim success path in `frontend/src/modules/seller/pages/found/ui/page/Page.tsx`:

```tsx
{!hasShownAddPhoneHint && claimsCount === 1 && (
  <PhoneHintBanner ... />
)}
```

Stored in `localStorage` to avoid re-showing.

### Step 10 — settings UI: "My Phones" section

`frontend/src/modules/seller/pages/profile/` (or `/seller/settings/phones/`) — list, add, delete, "make default contact" flag.

## Behaviour & invariants

- **Exactly one `is_primary=true` per user.** Enforced by the partial unique index.
- **`User.phone` matches `user_phones.phone WHERE is_primary=true` for the same user_id.** Maintained by application code (no DB constraint to enforce this).
- **Phones globally unique across all users.** `uq_user_phone_phone` (UNIQUE on phone column).
- **Cannot delete the primary phone via UI.** Operations team handles primary-phone changes manually.
- **Listings are pinned to a contact phone.** When the contact phone is removed, the listing must transition (transfer or archive).
- **Claim/A4 use the union of all verified phones.** Set-membership query everywhere.
- **Listing count is per-account, not per-phone.** A seller with 3 phones and 8 listings has 8 listings against their *one account* — see C2.
- **OTP per-phone.** Adding a new phone requires its own OTP; existing phones stay.

## Architecture notes

- The `user_phones` table is the canonical "which phones belong to which user" — but `User.phone` remains the auth identifier (so the auth flow doesn't have to JOIN on every login).
- Every place in the codebase that previously did `User.phone == ...` for "find user by phone" needs to JOIN via user_phones (because the user might have logged in with their primary, but their listing has their additional phone). Use a small helper:

  ```python
  async def get_user_by_any_phone(db, phone: str) -> Optional[User]:
      res = await db.execute(
          select(User)
          .join(UserPhone, UserPhone.user_id == User.id)
          .where(UserPhone.phone == phone)
      )
      return res.scalar_one_or_none()
  ```

- Crawled-match expansion (Step 6) is the single biggest correctness change. Once shipped, A4 fanout works for additional phones automatically.

## Upstream dependencies

- **A1, A4** — claim flow and push fanout — done. C4 expands their phone-match logic.
- **A8** — admin pattern (admin endpoints surface, AuditLog hook) — done.
- **A6** — i18n foundation — done.
- **C2** — counter is per-account; no change needed beyond the comment in C2's spec.

## Downstream dependencies

- **C5** — multi-account detection MUST exclude legitimate multi-phone aggregations. The signal logic explicitly checks `user_phones` membership before flagging. **C5 must land after C4 schema lands.**
- **B6** — aria-label sweep should cover the new "remove phone" / "primary" / "make default contact" buttons.
- **D-block** — Telegram bot needs to know the user has multiple phones if/when bot autopost (D4) gets per-listing-phone support.

## Migration / schema implications

- **One additive migration** (prk_user_phone). Backfill is one INSERT-from-SELECT.
- **Dependency on `prf_canonicalize_phone` having run.** The backfill assumes E.164 format on `users.phone`.
- **No FK from `Listing.phone` to `user_phones.phone`** — listings have phones that may not match a user (parser-imported, not yet claimed). Soft validation only.
- **Forward-compat with C5.** The new table makes "is this phone in the same account?" a 1-line query.

## API implications

- Five new endpoints under `/sellers/me/phones`.
- `seller_crawled_listings_for_user` query rewrite.
- `crawled_match.notify_sellers_of_crawled_listing` query rewrite.
- `POST /listings`, `PATCH /listings/{id}` accept `contact_phone` field; validate against user_phones.

## Crawler / bot implications

- **Crawler:** none. Crawler keeps writing phones to `TelegramListing.contact_phone` / `OLXListing.contact_phone` as today.
- **Bot:**
  - `crawled_match.py` push fanout uses the expanded query → automatic.
  - The bot itself doesn't (yet) have a "manage my phones" flow. UI-only feature. The bot might gain a deeplink in Phase 2.

## AI / F-block implications

- **F1:** none. AI generation reads structured params + raw text; phone is a metadata field.
- **F3 SEO:** none.

## SEO implications

- **None.**

## Localization implications

- ~30 new strings × 3 locales (page title, button labels, error toasts, modal copy for delete-with-listings, OTP success/failure messages).
- Verification SMS / Telegram template needs translation if it changes per channel.
- Modal: "5 объявлений используют этот номер" → plural rules apply (Russian has 4 forms, Uzbek has 2).

## Infra / deploy implications

- **Major open question:** does C4 ship with SMS or Telegram-bot OTP?
  - Telegram-bot OTP: **already deployed**, zero infra cost. Limitation: the additional phone must own a Telegram account that's reachable. Most Uzbek realtors do, but not all.
  - SMS via Eskiz.uz: requires API key + paid SMS quota + integration. **Eskiz is mentioned in CLAUDE.md but never integrated.** New env vars, new service, new operational cost.
- Rate limits / monitoring on OTP endpoint similar to `request_seller_otp`.

## Edge cases

- **Phone already attached to another account.** Return 409, generic message. Don't disclose which account (privacy).
- **OTP re-send.** Limited to once per minute, max 3 within 5 minutes (mirroring existing pattern). 4th request → 30-minute lockout.
- **Duplicate phone in payload.** "This phone is already attached to your account" or "This is your primary phone" — disambiguate in the response code/copy.
- **Limit (3 additional) reached.** 409 with quota info.
- **Many-listings re-search.** Verifying a phone with 50 matched listings → don't load all on one screen; redirect to Found with deep-link or a "View all 50 in Found" CTA.
- **Phone removed from telco network.** SMS / TG OTP doesn't deliver → spec says "user contacts support". Document in copy.
- **Race during delete-with-listings.** While the user is choosing in the modal, another endpoint creates a new listing on this phone. Handle: re-check at delete-execution; if new listings appeared, abort with 409 + refresh the count.
- **Primary-phone can't be removed.** Surface a clear error; route to support.
- **C5 false positive prevention.** If user A has phone P1 and user B has phone P1 attached at different times (one removed, one added), the dedup signal could misfire. Mitigation: C5's signal logic compares `user_phones` row WHERE `removed_at IS NULL` (so removed rows don't trigger).

## Operational risks

- **Phone hijacking.** If an attacker controls phone P, they get the OTP and attach P to their account; a future listing with P shows their A4 push. Mitigation: phone uniqueness + rate-limit OTP requests (already in spec). For high-value abuse, this is a Phase-3 problem; for MVP, baseline OTP is acceptable.
- **Bot-only OTP excludes some users.** Realtors without a reachable Telegram chat can't add additional phones. Operational implication: support has to handle requests, or we ship Eskiz integration. **Decision needed before launch.**
- **Migration backfill.** All existing users get a primary `user_phones` row in one INSERT. At MVP scale (low thousands), trivial. At scale, batch.
- **Crawler→A4 query expansion.** Slight cost increase for the crawled-match query (set-membership via subquery). Index on `user_phones.user_id` covers it.

## Rollout strategy

1. Schema migration (PR1) — additive; safe to deploy any time.
2. Backend services + endpoints (PR2) — feature-flagged off in `app.core.config.multi_phone_enabled`.
3. Frontend (PR3) — phones management UI hidden behind same feature flag.
4. Parser / A4 query expansion (PR4) — read from `user_phones` table; immediately benefits all users (the backfill ensures every user has at least one row).
5. Soft-launch: enable feature flag for ~10 sellers; monitor.
6. Wide enable.

**Rollback:** disable the flag; the feature flag gates only the management UI, not the parser query (which is correct after PR4 regardless). Schema is additive — rollback drops the table only if no rows exist.

## Acceptance criteria

- Migration `prk_user_phone.py` applies cleanly + backfill seeds primary rows for all existing users.
- `POST /sellers/me/phones/request-otp` and `/verify-otp` work with 3-attempts cap + 5-min lockout.
- After verify, the response includes the count of newly-matched parser listings.
- Listing-create / edit forms show a phone-picker when the seller has > 1 verified phone; default = primary.
- `DELETE /sellers/me/phones/{id}` returns 409 with `affected_listings_count`; the modal action body resolves it.
- `seller_crawled_listings_for_user` and `crawled_match.notify_sellers_of_crawled_listing` use set-membership over all verified phones.
- Cannot delete the primary phone via UI.
- `grep -nE "func\.right\(.*phone, 9\)" backend/app | grep -v user_phones` returns zero — every phone-match site reads from `user_phones`.

## Recommended PR split

- **PR1 (BE)** — `user_phones` model + migration + backfill + tests.
- **PR2 (BE)** — endpoints (request-otp, verify, list, delete) + OTP rate limits + tests.
- **PR3 (BE)** — `crawled_match` query expansion + `seller_crawled_listings_for_user` rewrite + tests; `Listing.contact_phone` validation.
- **PR4 (FE)** — "My Phones" page + phone-picker on listing forms + post-claim hint banner + i18n.

## Estimated complexity

- BE schema + endpoints: ~3 dev-days.
- BE query expansion (with tests): ~1 dev-day.
- FE forms + page: ~2 dev-days.
- BE delete-with-listings flow: ~1 dev-day.
- i18n + native-speaker review: parallel.

Total **~7 dev-days** with senior FE+BE.

## Open questions

1. **SMS vs Telegram OTP** — biggest unresolved. Spec says SMS; only Telegram-bot OTP exists. Decision: ship with Telegram-bot OTP for MVP (zero infra cost, mirrors existing flow), revisit Eskiz integration as a Phase-2 upgrade if support requests are high. **Needs founder/product sign-off.**
2. **Listing.phone rename to contact_phone** — recommended for clarity. Risk of grep hits across the codebase. Alternative: keep `phone` and document the new semantic.
3. **`Seller.phone` future** — synced to primary or dropped? Recommend: drop, derive from `user_phones WHERE is_primary=true` everywhere. Migration removes the column once all reads are switched.
4. **Should support be able to swap a user's primary phone** via admin UI? Spec implies it's manual (operations channel). Recommend: yes, build a small admin endpoint in PR3 with full AuditLog.
5. **Per-phone listing limit?** Spec says no — limit is per-account. Confirm.
6. **Phone-removal soft-delete vs hard-delete?** Recommend: hard-delete the row (it's a verification artifact, not user data). Listing transfer happens before the delete.
7. **Localized OTP delivery.** If TG bot, the message language follows the bot user's language preference; if SMS, the SMS text is fixed (and the user has to read it in whatever language). Operational: pin Russian for SMS.

## References

- `backend/app/db/models.py` — `User.phone`, `Seller.phone`, `Listing.phone`.
- `backend/app/db/models.py:1374, 1378` (or thereabouts) — source-table `contact_phone`.
- `backend/alembic/versions/20260428_prf_canonicalize_phone.py` — pre-existing canonical-phone normalisation (key context).
- `backend/app/api/v1/auth.py:767-906` — OTP flow to clone for the new endpoint.
- `backend/app/services/seller_crawled_listings.py:31, 40, 72, 105` — claim-side phone match (rewrite target).
- `backend/app/workers/tasks/crawled_match.py:137` — A4 fanout phone match (rewrite target).
- `backend/app/core/security.py:149` — `generate_otp`.
- `frontend/src/modules/seller/pages/create-listing/` — listing-create form to extend.
- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx` — post-claim hook.
- [A1](../../block-a/medium/A1-claim-reject-v2.md), [A4](../../block-a/hard/A4-push-notifications.md), [C2](../medium/C2-free-limit-logic.md), [C5](./C5-multi-account-detection.md), [B6](../../block-b/medium/B6-aria-labels-sweep.md).
