# Block A — Launch-Blocker Specs (V2.0)

Block A is the eight critical tasks that gate UcharMarket's public launch. **V2.0** reframes Block A around the architectural shift introduced by Block F (AI generation of listing descriptions): the parser no longer owns description text — it extracts structured parameters and persists raw source text as metadata; F1 (Block F) generates the user-visible description asynchronously in three locales.

This subtree organises specs by **complexity only**, since every spec here is launch-critical and the existing repo-level state-axis (`done/` / `partial/` / `not-started/`) does not segregate launch-blockers from later phases.

```
spec-kit/block-a/
├── easy/      — small, well-bounded, junior-friendly
│   ├── A2-mockup-filters.md
│   └── A3-mock-data-found.md
├── medium/    — multi-component, mid-level
│   ├── A1-claim-reject-v2.md
│   ├── A5-view-contact-counters.md
│   ├── A6-i18n-leaks.md
│   └── A8-channels-management.md
└── hard/      — broad surface, senior-led, cross-subsystem
    ├── A4-push-notifications.md
    └── A7-parser-f1-trigger.md
```

Each `<complexity>/<task>.md` follows the V1 spec convention:

- **Status** — DONE / PARTIAL / NOT STARTED, anchored to current code.
- **Complexity** — EASY / MEDIUM / HARD with one-line reason.
- **Block-A V2.0 ref** — pointer to the relevant section of the V2.0 functional spec.
- **What's done / What's missing** — exact file:line evidence.
- **Path to DONE** — concrete steps with code snippets.
- **Behaviour & invariants**.
- **Acceptance criteria** — measurable.
- **References** — citations + cross-spec links.

## Status snapshot at write-time

| Task | Complexity | Spec status | Why |
|---|---|---|---|
| [A2 — Mockup filters](easy/A2-mockup-filters.md) | EASY | PARTIAL | 3/5 backend filters already wired; UI badges still on; 3 fields not in `ListingFilters` schema. |
| [A3 — Mock data in Found](easy/A3-mock-data-found.md) | EASY | PARTIAL | `getMockups()` still renders 20 Unsplash cards on empty backend response. Skeleton + empty-state JSX exist but unreachable. |
| [A1 — Claim/Reject (V2.0)](medium/A1-claim-reject-v2.md) | MEDIUM | PARTIAL | Backend, migration, frontend buttons all real; `raw_text` not copied on convert; AI-description plumbing missing; double-click guard missing. |
| [A5 — View/Contact counters](medium/A5-view-contact-counters.md) | MEDIUM | PARTIAL | Event table + idempotency + self-view + dashboard tile shipped; only 7-day window + anonymous dedup remain. |
| [A6 — i18n leaks](medium/A6-i18n-leaks.md) | MEDIUM | PARTIAL | `ru` + `uz` healthy; `uz-latn` missing; ICU plurals + locale-aware formatters missing; small Cyrillic leaks remain. |
| [A8 — Channels management](medium/A8-channels-management.md) | MEDIUM | PARTIAL | YAML-driven works; admin CRUD, per-source metadata, metrics persistence are greenfield. 14/25 channels. |
| [A4 — Push notifications](hard/A4-push-notifications.md) | HARD | NOT STARTED | Bot infra exists; trigger, callback handlers, F1 gate, 7-day expiry, group-batching all missing. |
| [A7 — Parser quality + F1](hard/A7-parser-f1-trigger.md) | HARD | PARTIAL | LLM extraction + raw_text + Uzbek vocab + signature dedup real; F1 status enum, queue, B2C gating, edit-time regen, junk filter, source metrics absent. |

## Distribution

- **Easy:** 2 (A2, A3)
- **Medium:** 4 (A1, A5, A6, A8)
- **Hard:** 2 (A4, A7)

## Cross-references with the existing spec-kit

Several Block-A tasks supersede or are kin to existing V1 specs in `partial/` and `not-started/`:

| Block-A spec | V1 sibling | Relationship |
|---|---|---|
| [A1 medium](medium/A1-claim-reject-v2.md) | [`partial/medium/04-claim-flow.md`](../partial/medium/04-claim-flow.md) | V1 listed reject as missing — now shipped. V2.0 adds raw-text passthrough + AI description coupling. |
| [A4 hard](hard/A4-push-notifications.md) | [`not-started/medium/F107-seller-claim-notification.md`](../not-started/medium/F107-seller-claim-notification.md) | V2.0 supersedes V1: AI text card + inline buttons + 7-day expiry + group-batch are net-new. |
| [A5 medium](medium/A5-view-contact-counters.md) | [`partial/easy/seller-dashboard-counters.md`](../partial/easy/seller-dashboard-counters.md) | V1 contact endpoint + self-view guard listed missing — now shipped. V2.0 adds 7-day window + anon dedup. |
| [A1 medium](medium/A1-claim-reject-v2.md) (Master ranking aspect) | [`partial/easy/F108-master-record-ranking.md`](../partial/easy/F108-master-record-ranking.md) | Independent — F108 is a ranking ORDER BY change; not Block-A scope. |

## V2.0 invariants the specs assume

These run through every Block-A spec; ground them once here so each spec doesn't repeat:

1. **Parser writes params + raw_text + source metadata.** Description text is never set by the parser.
2. **F1 (Block F) owns user-visible description** for B2C, push notifications, and seller cabinet rendering.
3. **`Listing.raw_text` is realtor-only** — visible in cabinet "Show source" block, never in B2C.
4. **Status gating in B2C feed:** `PENDING_GENERATION` and `UNCONFIRMED` are excluded; `GENERATION_FAILED` shows with a template description.
5. **Reject is permanent per-seller.** Same listing reappearing later (matched by signature) does not re-prompt that seller.
6. **i18n at write time.** Every new UI string lands in `ru` + `uz` + `uz-latn` on day one.
7. **Public Telegram channels only.** No invite-link channels.
8. **No backend Russian text.** HTTP error payloads are codes; frontend translates.

## Suggested execution order

Order is dictated by dependency direction and unlock-shape, not strictly by complexity. F1 (Block F) is a hard prerequisite for the V2.0 deltas in A1, A4, A7 — but plenty of work can ship before F1 lands.

### Pre-F1 (ship now)

1. **easy** → [A3 mock-data Found](easy/A3-mock-data-found.md) — half-day deletion; also drops 5 Russian-hardcoded titles, knocking work off A6.
2. **easy** → [A2 mockup filters](easy/A2-mockup-filters.md) — half-day; drops badges where filters already work, hides the three unimplemented sections.
3. **medium** → [A1 claim/reject — pre-F1 part](medium/A1-claim-reject-v2.md) — copy `raw_text` on convert (one line per function), add disabled-state to buttons, "Show source" UI block. F1-coupled work waits.
4. **medium** → [A5 counters — 7-day window](medium/A5-view-contact-counters.md) — extend dashboard endpoint + UI line.
5. **medium** → [A6 i18n — `uz-latn` set + ICU plurals](medium/A6-i18n-leaks.md) — operational work (translations) in parallel with engineering.
6. **medium** → [A8 channels — admin CRUD + metadata schema](medium/A8-channels-management.md) — unlocks operational expansion.

### F1 prerequisite (Block F start point)

7. **hard** → [A7 parser + F1](hard/A7-parser-f1-trigger.md) — extends `ListingStatus`, stands up F1 Celery task, gates B2C feed, fixes signature dedup.

### Post-F1

8. **medium** → A1 V2.0-coupled remainder: AI description in B2C, skeleton on `pending_generation`, edit-time regen wiring.
9. **hard** → [A4 push notifications](hard/A4-push-notifications.md) — depends on F1 being live (push card body uses AI text).
10. **medium** → A8 per-source AI-quality metrics (depends on F1 + F5 to populate).

### Operational (Block E, not engineering)

- [A8 operational expansion](medium/A8-channels-management.md) — founder grows source list to 25+ via tgstat.ru.
- [A6 native-speaker review](medium/A6-i18n-leaks.md) — `uz-latn` translation pass.

## Open questions raised across specs

- **A1:** UI for two-realtors-same-phone admin moderation — does an admin queue exist, or just detection-and-message?
- **A2:** Path 1 (real backend filters) vs hybrid (drop badges + hide three sections)? Hybrid recommended in this kit.
- **A4:** Capture-to-push p95 SLA target?
- **A5:** Cookie + fingerprint vs cookie-only for anonymous dedup? Cookie-only recommended for .uz privacy.
- **A7:** "Representative sample" definition — fixed dataset or rolling 7-day live?
- **A8:** Real admin UI in this iteration vs DB table + later UI? Recommended: DB table now, basic UI now, polish later.

## Conventions

- File paths use repo-root-relative form.
- Line numbers are accurate at write-time and may drift; treat as starting points.
- Cross-spec links use relative paths: `../<complexity>/X.md` for same-state, `../../<state>/<complexity>/X.md` for V1 specs.
- Every spec is independently readable. No "see above" — link instead.
