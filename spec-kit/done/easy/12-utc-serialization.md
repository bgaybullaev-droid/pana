# 12 — UTC Serialization Invariant

**Status:** DONE (platform-level invariant fix)
**Complexity:** EASY — a 12-line helper plus an annotated Pydantic type — but a hard-earned invariant; trivial code, simple verification.

## Summary

The DB stores naive `DateTime` columns whose value is **Asia/Tashkent local time** (Postgres server timezone is `Asia/Tashkent` and SQLAlchemy `DateTime(timezone=False)` strips offsets on read). Without an explicit conversion, a JSON response containing such a value is interpreted by the frontend's `new Date()` differently across environments — Telegram Android WebView in particular treats the offset-less ISO string as UTC, shifting every "Today" item to "Tomorrow" and producing negative `formatTimeAgo` deltas (every notification renders as "только что").

The invariant: **every datetime crossing the API boundary is serialised as UTC ISO with a `Z` suffix.**

## Mechanism

`backend/app/schemas/common.py`:

```python
_DB_NAIVE_TZ = ZoneInfo("Asia/Tashkent")

def serialize_datetime_utc(dt: datetime) -> str:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_DB_NAIVE_TZ)
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

UTCDateTime = Annotated[datetime, PlainSerializer(serialize_datetime_utc, return_type=str)]
```

Every Pydantic response that exposes a datetime declares it as `UTCDateTime`, not `datetime`. Replacing all of `notifications`, `listings`, `users`, `comments`, `sellers`, `saved_searches`, `crawler`, `unified`, `admin`, `housing_complexes`, `seller`, `notification_settings` schemas. See grep:

```
grep -rn UTCDateTime backend/app
```

## Frontend pairing

`frontend/src/shared/lib/date.ts` — `parseDate(s)` → `new Date(s)`. Because the backend always emits `Z`-suffixed UTC, every browser environment (including Telegram Android WebView) parses correctly. Local conversions in `formatDate` / `formatDateTime` / `formatTime` use `timeZone: "Asia/Tashkent"`.

The notifications page grouping (`Сегодня` / `Вчера` / `Ранее`) compares `dateStart` (date with time zeroed) against `today` derived the same way — both running in browser-local time, which matches Tashkent on the user's device.

## Behaviour & invariants

- **Naive in, UTC-Z out.** A naive datetime is *assumed* to be Asia/Tashkent. This is the single point of conversion. New schemas adding date columns must use `UTCDateTime`.
- **Aware datetimes** are honoured as-is — `astimezone(UTC)` works whether the source is Tashkent-aware, UTC-aware, or anything else.
- **No naive datetimes leak.** If a future endpoint serialises a `datetime` directly (raw `dict`-style), the invariant breaks. Linter rule (B4 in the local guardian) flags `datetime.now()` / `utcnow()` calls without `tz=` in workers/services to keep ingestion clean.
- **DB-side `func.now()`** still returns Tashkent-naive — this is the source of truth, not a bug. The serialiser absorbs the gap.

## Why this is in the Spec Kit

The fix touches every API consumer. Future work that adds new datetime fields, new endpoints, or new clients must respect this invariant. Putting it in the kit makes the contract explicit.

## References

- `backend/app/schemas/common.py:1-30`
- `frontend/src/shared/lib/date.ts`
- `frontend/src/modules/buyer/pages/notifications/ui/page/Page.tsx` — date grouping consumer.
- Commit history: `fix(notifications): timezone, source field, match transparency` introduced this.

## Known gaps

- DB columns themselves remain `DateTime(timezone=False)` for now. Migrating to `timezone=True` would remove the assumption-based shim entirely; not worth the migration cost yet, and the shim handles all currently-known clients.
