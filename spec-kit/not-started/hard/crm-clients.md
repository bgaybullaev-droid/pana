# 13 — CRM-Light: Clients Linked to Objects

**Status:** NOT STARTED
**Complexity:** HARD — two new tables (clients + M2M with stage), Kanban pipeline view, integration with the sold-price flow, broad seller-cabinet UI work.
**Vision-doc refs:** §5.1 ("Уровень 2") — Lightweight CRM
**Why now:** Phase 2. Activated alongside monetisation as part of the Cabinet Pro tier (99 000 sum/month per §7.3).

## Goal

A seller maintains a list of **clients** (buyers / leads), each linked to one or more listings the client has shown interest in or rented/bought. This is the Pro-tier carrot in the vision doc — replaces the spreadsheets sellers maintain today.

## Proposed data model

`SellerClient`:

| Column | Notes |
|---|---|
| `id` | UUID. |
| `seller_id` | FK CASCADE. |
| `name` | Client display name (free text). |
| `phone`, `telegram_username`, `notes` | Contact + free notes. |
| `created_at`, `updated_at` | Lifecycle. |

`SellerClientListing` (M2M with stage):

| Column | Notes |
|---|---|
| `client_id`, `listing_id` | Composite PK. |
| `stage` | Enum: `INTERESTED` / `VIEWED` / `NEGOTIATING` / `CLOSED_WON` / `CLOSED_LOST`. |
| `expected_close_at` | Optional date. |
| `last_activity_at` | When the seller last interacted. |
| `notes` | Per-deal note. |

## API surface

Under `/api/v1/seller/clients/*`:

| Verb | Path | Purpose |
|---|---|---|
| GET | `/seller/clients` | Paginated client list with active deal counts. |
| POST | `/seller/clients` | Add client. |
| PATCH | `/seller/clients/{id}` | Edit. |
| DELETE | `/seller/clients/{id}` | Soft delete. |
| POST | `/seller/clients/{id}/listings` | Attach listing with initial stage. |
| PATCH | `/seller/clients/{id}/listings/{listing_id}` | Update stage / notes. |
| DELETE | `/seller/clients/{id}/listings/{listing_id}` | Detach. |
| GET | `/seller/pipeline` | Kanban view: clients grouped by stage across all the seller's listings. |

## Frontend

Cabinet → "Клиенты" tab. Two views:

- **List** — clients sortable by activity, with per-client deal count.
- **Pipeline** (Kanban) — columns by `stage`, cards by client × listing.

Linking a client to a listing happens from the listing detail (button "Добавить клиенту") or from the client detail (button "Привязать объект").

## Behaviour & invariants

- **No buyer-side visibility** — clients exist in the seller's private space. Buyers don't see they're "in someone's CRM".
- **Stage transitions** unconstrained (no required transitions — sellers know their workflow better than we do; the doc warns against "sweeping refactors").
- **Closing won** auto-prompts the sold-price modal (links to [`deal-status-and-final-price`](../medium/deal-status-and-final-price.md)).
- **Telegram contact** field — if filled, lets the seller open a direct chat from the CRM card via `tg://resolve?domain=<username>` deep links.

## Acceptance criteria

- Seller can add, edit, delete clients.
- Listing-client link with stage works in both directions.
- Pipeline view (Kanban) groups by stage.
- Closing a deal-listing pair as `CLOSED_WON` opens the sold-price modal.
- All operations available only on Cabinet Pro tier (gated by [`F113-wallet`](F113-wallet.md) once it ships).

## Open questions

- Multi-seller agencies — does a junior agent see senior agent's clients? Not in Phase 2; revisit when an agency tier exists.
- Import from contacts file (CSV) — Phase 2.5.
- Reminders ("call client X, no contact in 7 days") — Phase 2.5.
