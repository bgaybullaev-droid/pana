# F3 — SEO infrastructure for the public web

**Difficulty**: hard (10 days)
**Spec source**: Block F V2.0, §F3
**Dependencies**: F1 (needs AI text on every listing for the page
content)
**Blocks**: nothing structurally — strategic SEO compounding asset

---

## Goal

Serve indexable HTML for active listings and base filter
combinations at `https://ucharmarket.uz/{lang}/...`. Telegram WebApp
remains the Vite SPA. SSR via FastAPI + Jinja2 — same Python stack,
no Node runtime. Schema.org JSON-LD, hreflang, canonical, sitemap,
robots — all the technical SEO baselines covered.

---

## Existing infrastructure to reuse

- FastAPI app (`backend/app/main.py`) — adds Jinja2 templates and
  the SEO router.
- `Listing.ai_description_{ru,uz,uz_cyrl}` for page content.
- Block D D3a `services.deeplink.build_listing_link` — "Открыть в
  UcharMarket" CTA on every page.
- Block D D3a `services.deeplink.build_filter_link` — shareable
  filter URLs.
- `core/regions._DISTRICT_ALIASES` — slug generation for districts.
- Existing `Listing.deleted_at`, `Listing.status` columns drive 410
  Gone responses.

---

## What changes

### Database

None. F3 reads existing schema.

### Backend

1. **`app/services/seo_meta.py`** — domain helpers:
   ```python
   @dataclass(frozen=True)
   class SEOMeta:
       title: str
       description: str
       og_title: str
       og_description: str
       og_image: Optional[str]
       canonical: str
       hreflang: dict[str, str]  # lang code → URL

   def build_listing_meta(listing: Listing, lang: str) -> SEOMeta: ...
   def build_filter_meta(filters: dict, lang: str) -> SEOMeta: ...
   def build_listing_jsonld(listing: Listing, lang: str) -> dict: ...
   def slug_for_listing(listing: Listing, lang: str) -> str: ...
   ```
   - `build_listing_meta`: title from structured params
     ("3-комн в Чиланзаре, 65 м², 35 000 у.е. — UcharMarket"),
     description from first 160 chars of `ai_description_*` in the
     page's language, og_image from primary photo URL.
   - `build_listing_jsonld`: emits `@type: RealEstateListing` with
     `name`, `description`, `image`, `offers.price`, `offers.priceCurrency`,
     `address.addressLocality`, `numberOfRooms`, `floorSize.value`.
     Drops fields that are null rather than emitting `null` values.
   - `slug_for_listing`: deterministic slug from
     (rooms-комн)-(district-latin); first 30 chars max; matches via
     `_DISTRICT_ALIASES` for transliteration.

2. **`app/services/sitemap.py`** — generators:
   ```python
   async def build_listings_sitemap(db, lang: str, page: int) -> str: ...
   async def build_filters_sitemap(db, lang: str) -> str: ...
   async def build_sitemap_index(db) -> str: ...
   ```
   - `build_listings_sitemap`: paginated 50k URLs/file; `<lastmod>`
     from `listing.updated_at`; `<changefreq>` `daily`;
     `<priority>` `0.7`.
   - `build_filters_sitemap`: enumerates base filter combos (district,
     deal × type, deal × type × district, deal × type × rooms ×
     district) where active-listing count > 0.
   - `build_sitemap_index`: top-level index pointing at per-language
     and per-page sitemaps.

3. **`app/api/v1/seo.py`** (mounted at root, not under `/api/v1`):
   - `GET /{lang}/listing/{id}/{slug}` — listing detail.
   - `GET /{lang}/tashkent/{district}` — district landing.
   - `GET /{lang}/{deal}/{type}` — deal × type landing.
   - `GET /{lang}/{deal}/{type}/{district}` — 2-param combo.
   - `GET /{lang}/{deal}/{type}/{rooms}-rooms/{district}` — 3-param
     combo (last indexable depth).
   - `GET /sitemap.xml` — index.
   - `GET /sitemap-{lang}-listings-{page}.xml`,
     `/sitemap-{lang}-filters.xml`.
   - `GET /robots.txt`.

   Behavior:
   - Listing route: 200 HTML if status ∈ {ACTIVE, GENERATION_FAILED};
     301 to canonical if slug drifted; 410 Gone otherwise.
   - Filter route with 0 active listings: 200 with
     `<meta robots="noindex,follow">` + "Сейчас нет объявлений" body.
   - Beyond 3 indexable params: route doesn't exist (404).
   - User-Agent containing `TelegramWebApp` or `tdesktop` → 302 to
     deep link via `services.deeplink.build_listing_link` (TWA users
     who hit a SEO URL get redirected into the app).
   - `Cache-Control: public, max-age=300` for content pages,
     `max-age=900` for sitemap, `max-age=3600` for robots.

4. **`app/templates/seo/`** Jinja2 templates:
   - `base.html` — common `<head>` (title, description, og:*,
     twitter:*, canonical, hreflang, JSON-LD slot).
   - `listing.html` extends `base.html` — body: photo carousel
     (static, no JS), AI description, structured params block,
     "Открыть в UcharMarket" CTA.
   - `filter.html` — list of listings (up to 20 per page); each row
     links to `/{lang}/listing/{id}/{slug}`.
   - `gone.html` — 410 page.
   - `empty.html` — 200-noindex empty filter page.
   - `sitemap_index.xml`, `sitemap_listings.xml`,
     `sitemap_filters.xml`, `robots.txt`.

5. **`app/main.py`** — mount Jinja2 templates and the SEO router:
   ```python
   from fastapi.templating import Jinja2Templates
   templates = Jinja2Templates(directory="app/templates")
   app.include_router(seo.router)  # at root, no prefix
   ```
   Mount priority: `/api/v1/*` and `/uploads/*` first, then SEO
   router at root.

6. **`app/db/session_seo.py`** (new) — read-only Postgres session
   pool dedicated to SEO routes:
   ```python
   _seo_engine = create_async_engine(
       settings.async_database_url,
       pool_size=10,
       max_overflow=20,
       pool_pre_ping=True,
   )
   ```
   So crawler bursts don't starve the API's main pool.

7. **`app/workers/celery_app.py`** — `rebuild_sitemap` beat task
   (or on-demand on listing PATCH; choose every-15-min for
   simplicity in PR-F3).

### Frontend

None. SSR is server-rendered HTML; no SPA changes.

### Ops (parallel to PR-F3 backend work)

1. DNS A record for `ucharmarket.uz` → web host.
2. TLS cert (Let's Encrypt or vendor).
3. Reverse-proxy / ingress configuration:
   - `/api/v1/*` → FastAPI API
   - `/admin/*`, `/seller/*` → SPA bundle
   - `/uploads/*` → FastAPI static
   - `/{lang}/*`, `/sitemap*.xml`, `/robots.txt` → FastAPI SEO router
   - everything else → SPA bundle
4. Submit `/sitemap.xml` to Google Search Console + Yandex.Webmaster.

---

## Failure handling

| Failure | Behaviour |
|---|---|
| Listing deleted or paused | 410 Gone with sparse "Это объявление больше не актуально" template + CTA back to home. |
| Slug in URL drifts from canonical | 301 to current canonical URL. |
| Filter page has 0 active listings | 200 with `<meta robots="noindex,follow">` + "Сейчас нет объявлений" body. |
| Filter route beyond 3-param depth | 404. |
| TWA user-agent hits SEO route | 302 to deep link. |
| SEO Postgres pool exhausted | 503 with `Retry-After: 30`. Dedicated pool makes this unlikely. |
| Schema.org required field missing | Sanity helper drops `null` fields rather than emitting `"value": null`. |
| Image URL broken | `og:image` falls back to default brand placeholder; listing body still renders without image. |
| Sitemap rebuild fails | Old sitemap stays served; next attempt retries. Log at WARNING. |

---

## Observability

- `seo.rendered path=<p> listing_status=<s> duration_ms=<d>`
- `seo.gone path=<p> reason=<deleted|paused|expired>`
- `seo.slug_redirect from=<p> to=<p>`
- `seo.noindex_empty path=<p>`
- `seo.twa_bounce path=<p> user_agent=<ua_short>`
- `sitemap.generated kind=<listings|filters> lang=<l> entries=<n>`
- `sitemap.rebuild_failed err=<msg>`

---

## Acceptance criteria

- `curl https://ucharmarket.uz/ru/listing/<uuid>/<slug>` returns 200
  HTML with:
  - `<title>`, `<meta name="description">`, `<meta property="og:*">`
  - `<link rel="canonical">` matching the requested URL
  - 3× `<link rel="alternate" hreflang>` for ru/uz/uz-latn
  - `<script type="application/ld+json">` with valid
    `RealEstateListing` schema
- Google Rich Results Test passes on a sample listing page.
- `curl https://ucharmarket.uz/sitemap.xml` returns sitemap index.
- `curl https://ucharmarket.uz/sitemap-ru-listings-1.xml` returns
  valid XML with `<urlset>`.
- `curl https://ucharmarket.uz/robots.txt` allows `/ru/ /uz/
  /uz-latn/ /sitemap*`; disallows `/api /admin /seller /uploads`.
- Soft-deleted listing returns 410.
- TWA user-agent → 302 to deep link.
- Mobile Lighthouse score (sample listing page):
  Performance ≥ 75, SEO 100.
- "Открыть в UcharMarket" CTA links via `services.deeplink.build_listing_link`.

---

## Risks

- **DNS/TLS misconfigured at launch** (Medium / High). Mitigation:
  ops checklist item with explicit verification step
  (`curl -I https://ucharmarket.uz` returns 200, valid cert).
- **SSR Postgres pool exhausted under crawler burst** (Medium /
  Medium). Mitigation: dedicated read-only pool; 5-min HTTP cache;
  reverse-proxy rate limiting (Googlebot exempt by User-Agent).
- **Sitemap stale for new listings** (Low / Medium). Mitigation:
  15-min rebuild cadence; `lastmod` updated on PATCH; Google
  IndexNow ping post-launch (optional).
- **Schema.org validation regression** (Low / Medium). Mitigation:
  sanity helper drops null fields; manual Google Rich Results Test
  per deploy.
- **TWA users land on SEO URL by accident** (Low / Low). Mitigation:
  User-Agent bounce to deep link.
- **Slug drift creates 301 chains over time** (Low / Low).
  Mitigation: slug derived from immutable UUID prefix + first 30
  chars of district/title; rare to change.
- **Lighthouse Performance < 75** (Medium / Medium). Mitigation:
  WebP images via existing pipeline; minimal CSS in templates; no
  JS framework on SEO pages; lazy-load photos.
