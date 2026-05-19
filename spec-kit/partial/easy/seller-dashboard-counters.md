# Seller Dashboard — View + Contact Counters

**Status:** PARTIAL — per-card chips for views + contacts already render; the contact-event endpoint, the aggregate dashboard, and the self-view guard are missing.
**Complexity:** EASY — surfacing logic exists; what remains is one new endpoint, one aggregate query, one guard, and a UI panel.
**Vision-doc refs:** §2.2 #4, §5.1 ("Уровень 1")

## What's done

- **Per-card view chip** — `frontend/src/modules/seller/pages/listings/ui/page/Page.tsx:546-557` renders `card.views_count` with an `IconEye`. Visible on every listing card in the seller portfolio.
- **Per-card contacts chip** — same file, immediately below the views chip; renders `card.contacts_count` when `> 0`.
- **`Listing.contacts_count` column** exists on the model.
- **`Listing.views_count` increment** — `backend/app/api/v1/listings.py:1821` increments on every detail open via `resolve_listing()`.

## What's missing

1. **Contact-event endpoint.** `Listing.contacts_count` is never incremented anywhere — there is no `POST /listings/{id}/contact` route. The chip renders 0 forever.
2. **Aggregate dashboard panel.** No `total_views / total_contacts / total_favorites` summary at the top of the seller listings page. The vision spec ("sellers see proof the platform works") needs this top-of-page band.
3. **`GET /sellers/me/dashboard` endpoint.** Doesn't exist; would back the aggregate panel.
4. **Self-view exclusion guard.** `views_count += 1` at `listings.py:1821` runs unconditionally. A seller opening their own listing inflates their own metrics. Needs `if current_user and current_user.id == listing.seller.user_id: skip`.
5. **Favorites-count chip on the card.** `Favorite` rows exist but no `favorites_count` is exposed per listing in the seller cabinet. Computable on the fly via `COUNT(*) WHERE listing_id = ?`.

## Path to DONE

1. **Self-view guard** — single `if` in `resolve_listing()` (or wherever `views_count` is bumped). Smallest patch with the highest data-quality impact; do this first.
2. **Contact-event endpoint** — `POST /listings/{id}/contact`, idempotent per (user, listing, day) via Redis key `contact_seen:{user_id}:{listing_id}:{date}`. Increments `Listing.contacts_count`. Frontend wires the button on `ListingCard` (the "Связаться" button) to call it before revealing the phone.
3. **Aggregate dashboard endpoint** — `GET /sellers/me/dashboard` returning `{total_views, total_contacts, total_favorites, top_listings: [...]}` over the seller's `Listing` set.
4. **Favorites-count chip** — extend the seller listings response to include `favorites_count` per row (subquery or correlated `COUNT`). Render a third chip next to views + contacts.
5. **UI panel** — a small band at the top of `frontend/src/modules/seller/pages/listings/ui/page/Page.tsx` showing the four totals.

## Behaviour & invariants

- **Self-view excluded** for both anonymous → owner-detection (no anonymous match) and authenticated.
- **Contact-event dedup** — at most one increment per (viewer × listing × day). Anonymous viewers can still trigger a contact event because the button is auth-gated; effective dedup key always has a `user_id`.
- **Anonymous viewers** still increment `views_count` (anonymous = real audience).

## Acceptance criteria

- Seller-self-views don't increment `views_count`.
- "Связаться" tap increments `contacts_count` once per user-day; double-tap doesn't double-count.
- Per-card chips show three counters: 👁️ views · 📞 contacts · ❤️ favorites.
- Top-of-page band shows totals across the seller's portfolio.
- After this spec lands, the per-event richer table from `../hard/F077-personalization.md` (Phase 1 of personalisation) is still required separately for the recommendation pipeline; this spec deliberately avoids that scope to ship quickly.

## Open questions

- "Connect via Telegram" deep link as a separate counter from "phone reveal"? Defer — start with one `contacts_count`, split later if product asks.
- Sparkline / time-series in cabinet — out of scope for Phase 1; Phase 2 with the personalisation event table.
