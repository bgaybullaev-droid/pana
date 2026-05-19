# 10 — Deep Links — Filter Pre-fill

**Status:** NOT STARTED
**Complexity:** EASY — frontend-only effect that reads start_param and pushes filters / route — half a day.
**Vision-doc refs:** §4.2 ("Deep Links: ...t.me/ucharmarket_bot?start=chilanzar_2rooms")
**Why now:** Phase 1. Half a day. Marketing wants this for ad-link conversions.

## Goal

Allow `t.me/<bot>?start=<payload>` to deep-link into the Mini App with pre-applied filters / target route.

Examples:
- `?start=chilanzar_2rooms` → home feed pre-filtered to Chilanzar / 2 rooms.
- `?start=listing_<uuid>` → listing detail page.
- `?start=found` → seller's Found page (skip onboarding for invited sellers).

## What's done

- `?start=link_<phone>` is parsed by the bot (`backend/app/bot/handlers.py:225-268`) — used for binding telegram_id to a phone-only user.

## Implementation outline

### Bot side

When the user opens the Mini App via the button injected in `/start`, Telegram appends `start_param` to `Telegram.WebApp.initDataUnsafe`. Most deep-links can be handled purely on the frontend reading that param — **no backend change required** for filter prefill. The bot can also recognise specific prefixes for non-MiniApp behaviour (e.g. ref codes) — see [referral-program](../hard/referral-program.md).

### Frontend side

`frontend/src/app/providers/TelegramProvider.tsx` already extracts `initData`. Add:

```ts
const startParam = (webApp as any)?.initDataUnsafe?.start_param || "";
```

Expose it in `TelegramContext`. New router-level effect:

```ts
useEffect(() => {
  if (!startParam) return;
  if (startParam.startsWith("listing_")) navigate(`/listings/${startParam.slice(8)}`);
  else if (startParam === "found") navigate("/seller/found");
  else if (startParam.startsWith("ref_")) saveReferralCode(startParam.slice(4));
  else applyFilterShortcut(startParam);  // chilanzor_2rooms etc.
}, [startParam]);
```

`applyFilterShortcut` parses tokens (`<district>_<rooms>rooms_<sell|rent>`) and pushes filters to the URL — feed already syncs from URL.

## Behaviour & invariants

- **One-shot consumption** — clear the param after handling so re-mount doesn't redirect again.
- **Unknown payload** — fall through to home feed; never error.
- **Validation** — payload contains only `[a-z0-9_]`; ignore otherwise (Telegram's spec already enforces this, but defense in depth).

## Acceptance criteria

- `t.me/<bot>?start=chilanzor_2rooms` opens the Mini App with district=Chilanzor and rooms=2 selected.
- `t.me/<bot>?start=listing_<uuid>` opens that listing's detail page.
- `t.me/<bot>?start=found` opens the seller Found page (when the user is a seller).
- Existing `link_<phone>` flow unaffected.
