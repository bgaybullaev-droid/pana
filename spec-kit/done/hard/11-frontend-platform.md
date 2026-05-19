# 11 — Frontend Platform

**Status:** DONE (platform layer)
**Complexity:** HARD — TWA detection edge cases, FSD architecture, BackButton version-gated compatibility, dual-token (cookie + localStorage) auth state machine, broad surface.

## Summary

React 18 + Vite 5 + TypeScript 5 single-page app, Telegram-WebApp-aware, served on its own port and proxied through nginx in production. State is managed by Effector v23 stores; UI by Mantine 7; the swipeable feed by Swiper 11. Architecture follows Feature-Sliced Design: `app/` → `modules/` (former `pages/`) → `shared/`.

## Stack

| Layer | Tech |
|---|---|
| Build | Vite 5 with the standard `server.proxy` config — `/api` and `/uploads` forwarded to the backend on `:7879`. Dev server binds `host: "0.0.0.0"`, port `7878`. |
| Framework | React 18, React Router. |
| State | Effector v23 (`createStore`, `createEffect`, `createEvent`, `combine`, `connect`). Stores live next to features under `model/`. |
| UI kit | Mantine 7 + custom theme tokens in `app/styles/theme`. |
| Swiper | Swiper 11 — used by the home feed (single-tab Krutilka today). |
| Forms | Mantine `useForm`. |
| HTTP | Axios via `shared/api/client.ts` with JWT injection from auth store + 401 → refresh interceptor. |
| i18n | `react-i18next`, locales under `shared/i18n/locales/{ru,uz}/*.json`. |
| Tests | Vitest + Testing Library; Playwright for e2e. |

## Architecture

```
src/
  app/                  routing, providers (Auth, Telegram), theme, error boundary
  modules/
    buyer/              public-facing buyer surfaces
    seller/             seller cabinet (listings, found, settings)
    admin/              admin queues + dashboard
  shared/
    api/                axios client, typed endpoints, types
    state/              cross-feature stores (auth, user)
    ui/                 reusable components (ListingCard, InnerPage, ...)
    i18n/               locales + i18n setup
    lib/                date utilities, telegram type stubs, helpers
  test/                 Vitest setup
```

`vite.config.ts` proxies `/api` and `/uploads` to the local backend on `:7879`. The dev SPA is served at the conventional root — there is no custom URL-prefix middleware. Production-style Telegram WebApp integration relies on the Mini App URL pointing at the production-built SPA served behind nginx (see `demo-nginx` in deployment).

## Telegram integration

`frontend/src/app/providers/TelegramProvider.tsx`:

- Lazy-loads `https://telegram.org/js/telegram-web-app.js` from `index.html` (async, never blocks render).
- Exposes `TelegramContext` with `webApp`, `user`, `initData`, `isReady`, `isTelegramWebApp`.
- **`isTelegramWebApp` is true only when `webApp` is present AND (`initData.length > 0` OR `platform !== "unknown"`)**. The script injects a stub on plain browsers; this guard prevents the auth page from going into "Telegram-only" loading state outside Telegram.
- BackButton — only attached when `webApp.version >= 6.1` (older Mini App hosts crash on `BackButton.show()`).
- Theme parameters — `--tg-theme-bg-color` etc. pushed to CSS variables.

## Auth state machine

`frontend/src/shared/state/auth/model/`:

- Sources: `verifySellerOTPFx`, `loginWithBuyerPhoneFx`, `authenticateWithTelegram`, `loginAdminFx`, `refreshTokensFx`, `logoutFx`.
- Each completion event is wired to `fetchUserStatsFx` so the unread-count badge resyncs after every login.
- 401 from `apiClient` triggers `refreshTokensFx`; failure logs out.
- Tokens persisted to `localStorage` for fallback when cookies are stripped (mobile WebView scenarios).

## Date utilities

`frontend/src/shared/lib/date.ts`:

- `parseDate(string)` → `new Date(string)`.
- `formatTimeAgo(string)` → `только что` / `5 мин` / `2 ч` / `3 д` / locale date.
- `formatDate`, `formatDateTime`, `formatTime` — `Intl.DateTimeFormat` with `timeZone: "Asia/Tashkent"`.
- Pairs with the backend's UTC-with-Z serialisation (see [12-utc-serialization](../easy/12-utc-serialization.md)) so today's items group correctly under "Сегодня".

## i18n

`frontend/src/shared/i18n/`:

- Two locales: `ru`, `uz`.
- Namespaced files: `buyer.json`, `seller.json`, `common.json`, etc.
- Missing-key fallback to `ru`.

## Build / serve

- Dev: `npm run dev` → Vite at `:7878`.
- Prod build: `npm run build` → static under `dist/`, served by nginx (in production).
- Source maps shipped in dev only.

## References

- `frontend/vite.config.ts` — proxy config.
- `frontend/index.html` — async Telegram SDK loader.
- `frontend/src/app/providers/TelegramProvider.tsx`
- `frontend/src/shared/api/client.ts`
- `frontend/src/shared/state/auth/model/`
- `frontend/src/shared/lib/date.ts`

## Known gaps

- Hardcoded RU strings still live in some seller surfaces (vision §2.2 #6). See `../../partial/medium/pre-launch-fixes.md`.
- Three-tab Krutilka not implemented yet — single feed only. See `../../not-started/medium/F048-krutilka-three-tabs.md`.
