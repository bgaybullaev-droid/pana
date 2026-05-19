# B2 — Text contrast over photo (Krutilka + photo-fg cards)

**Status:** PARTIAL — gradient + text-shadow already wired in Krutilka; AI short description is NOT wired in; multi-locale length awareness missing.
**Complexity:** MEDIUM — visual tuning is small but it must coordinate with B1 pills, F1 AI text, three locales, and the ListingSlideContent layout invariant.
**Block-B V2.0 ref:** B2.
**Why now:** central-Asia-bright-screen problem is real for the user; AI text from Block A doesn't appear in the slide yet.

## What's done

- **Gradient overlay** in `frontend/src/modules/buyer/pages/listing-detail/ui/main/ListingSlideContent.tsx:213-222`:

```tsx
<Box style={{
  background: "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.85) 65%)",
  height: "50vh",
  pointerEvents: "none",
  ...
}} />
```

- **text-shadow on price** at `ListingSlideContent.tsx:503-510`:

```tsx
<Text size="xl" fw={800} c="white" style={{ textShadow: "0 2px 6px rgba(0,0,0,0.6)" }}>
  {formattedPrice}
</Text>
```

- **text-shadow on description** at `ListingSlideContent.tsx:484-500`.
- **Locale-aware price formatting** via `formatNumber` (added in A6 foundation).
- **Default photo placeholder** for listings without images (Block A7 covers this; not B2's job).

## What's missing

1. **AI short description not wired into the slide.** Today the slide reads:

```tsx
{listing.description?.slice(0, 400) || listing.title || ...}
```

It does **not** read `listing.ai_description_ru / ai_description_uz / ai_description_uz_cyrl` — those columns landed in Block A but the Krutilka consumer hasn't been switched. Spec wants the first 100-150 chars of the AI text, locale-aware.

2. **No locale-aware text length sizing.** Uzbek translations are 20-40% longer than Russian; today's `lineClamp={3}` and fixed font size don't compensate.

3. **`raw_text` accidentally readable.** `listing.description` is the legacy field that for parser-imported listings sometimes contains the realtor's raw post text. Per V2.0, B2C must NOT show raw text — only AI text. Switching the slide to read `ai_description_*` first, with a graceful fallback to `description` only when AI text is missing, fixes this.

4. **Long UZS price** ("1 250 000 000 сум") can push the price line past the slide width on small phones. Spec calls for compact form ("1.25 млрд сум") or USD-primary fallback. Today's `formatNumber` doesn't apply this.

5. **Inline characteristics block (B1)** sits in the same overlay area; the gradient height (`50vh`) and the price/description vertical rhythm need to accommodate the new pill row without clipping.

6. **No "solid pill" alternative** explored. Spec offers two paths (Path 1 gradient — already shipped; Path 2 solid pill behind text). Today only Path 1 is implemented; whether Path 2 is needed for any specific surface is open.

## Path to DONE

1. **Wire AI text into Krutilka.** `ListingSlideContent.tsx:484-500` — change the description source:

```tsx
const lang = i18n.language === "ru" ? "ru" : i18n.language === "uz-cyrl" ? "uz_cyrl" : "uz";
const aiText =
  (listing as any)[`ai_description_${lang}`] ??
  (listing as any).ai_description_ru ??
  null;
const shortText = (aiText ?? listing.description ?? "").slice(0, 150);
```

The fallback chain ensures: AI in current locale → AI in Russian (always populated) → legacy `description` → empty (no text). Never `raw_text`.

2. **Tighten the gradient height** to match the new content footprint when B1 pills are present. Use a CSS variable so B1 can extend the gradient by the pill row height without copy-pasting magic numbers.

3. **Long-price formatter.**

```ts
function formatPriceShort(price: number, currency: string): string {
  if (currency === "UZS") {
    if (price >= 1e9) return `${(price / 1e9).toFixed(2)} млрд сум`;
    if (price >= 1e6) return `${(price / 1e6).toFixed(1)} млн сум`;
  }
  return formatPrice(price, currency);
}
```

Threshold tuned for UZS only; USD prices are short enough to stay verbatim.

4. **Multi-locale font sizing.** When `i18n.language` ≠ `ru`, drop description font from `size="sm"` to `size="xs"` and reduce `lineClamp` from 3 → 2. This keeps overflow in check without touching the gradient.

5. **a11y check** — text-shadow alone doesn't satisfy WCAG contrast in some edge cases. The gradient does the heavy lifting; verify with the spec's "bright sun" test on a real device.

6. **Document the Path 1 vs Path 2 decision** — Path 1 (gradient) is the canonical Krutilka treatment; Path 2 (solid pill) is reserved for a single-line surface like a notification card, where covering 35% of the photo isn't acceptable. No code change today; add a one-paragraph note in `ListingSlideContent.tsx`.

## Behaviour & invariants

- **Slide reads `ai_description_*` first**, never `raw_text`. `listing.description` is a fallback only.
- **Gradient covers all text** including the new pill row from B1; the gradient height is parameterised, not hardcoded.
- **Price never wraps**; long UZS amounts are formatted compactly.
- **No locale gets cut off** — uz / uz-cyrl strings fit within the slide bounds, possibly at smaller font.
- **Decorative gradient is `pointer-events: none`** — touch passes through to the swiper.

## Acceptance criteria

- Krutilka description reads `ai_description_<locale>` for an `ACTIVE` or `GENERATION_FAILED` listing; never `raw_text`.
- Cycling locale (ru → uz → uz-cyrl) re-renders the description in the chosen language; unscrolled slides update.
- A 1.25 billion UZS price renders as "1.25 млрд сум" on the slide, not "1 250 000 000 сум".
- On a 360-px phone in uz locale with the longest seed listing, no text wraps below the gradient or clips at the edges.
- B1 pill row, when present, sits cleanly under the price within the gradient.
- Manual screenshot test on a known-bright photo (white facade, daylight): every text element legible.

## Edge cases

- **AI gen failed** (`status="generation_failed"`) — the listing surfaces with the template description in `ai_description_*` (per A7's fallback). Slide renders it normally.
- **AI gen pending** (`status="pending_generation"`) — buyer feed already excludes this status (Block A); slide should never see it. If it does (deep-link), guard with a skeleton.
- **Empty AI text + empty `description`** — render only the title and structured params; no description block at all.
- **Photo missing** — A7 placeholder kicks in; gradient still applied for consistency with photo cards.
- **Dark fully-saturated photo** — gradient may make the bottom too dark; verify with a couple of test photos. If it becomes a complaint, dial down to `0.75` opacity.
- **Long uz amenity in B1 pill + long price** — both fight for horizontal space; prioritise the price (it's the higher-priority signal).

## Production risks

- **Locale fallback for AI text** — if `ai_description_uz_cyrl` is null but `ai_description_ru` is populated, the user in uz-cyrl locale sees Russian text. That's better than empty but it's a UX inconsistency. Document the fallback order so support can answer "why did it show in Russian?".
- **Snapshot testing for the slide** — visual regressions in the slide are easy to introduce. Ship with at least one Playwright/Chromatic screenshot of the slide in three locales.
- **Performance** — text-shadow + 50vh gradient on every slide; on Android low-end devices this is fine but verify on a 2017-era phone before launch.

## Dependencies

- **Upstream:** A7 / F1 (AI columns shipped — done), A6 (`formatNumber`, plural keys — done).
- **Coupled:** B1 (the pill row sits in the same overlay space — coordinate gradient height).
- **Downstream:** none direct.

## Open questions

1. **Compact UZS thresholds** — the spec doesn't pin them. Recommend `>= 1e9 → млрд`, `>= 1e6 → млн`. Confirm with product.
2. **Locale fallback order** — if uz-cyrl AI text is missing, fall back to uz Latin (similar script family) or to ru? Recommend uz Latin → ru. Confirm.
3. **WCAG target** — AA or AAA? AA is the spec's intent; locks the minimum opacity / font-size combo.
4. **Path 2 (solid pill)** — leave as documentation only, or implement for any concrete surface today (e.g. push card)? Not blocking — defer.

## References

- `frontend/src/modules/buyer/pages/listing-detail/ui/main/ListingSlideContent.tsx:213-222, 484-510` — overlay + text rendering.
- `frontend/src/shared/lib/formatNumber.ts` — extend with `formatPriceShort`.
- `backend/app/db/models.py:498-510` — `ai_description_{ru,uz,uz_cyrl}` columns.
- [B1](./B1-inline-characteristics.md) — pill row coordination.
- [A6](../../block-a/medium/A6-i18n-leaks.md), [A7](../../block-a/hard/A7-parser-f1-trigger.md) — i18n + AI text plumbing.
