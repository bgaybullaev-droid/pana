# 09 — Admin & Moderation

**Status:** DONE (queues + dashboard); listing-edit polish flagged in vision §2.2 is partial.
**Complexity:** MEDIUM — multi-resource queues, audit log, role-gated routes; broader than easy but no exotic mechanics.

## Summary

Admin role gets a separate area with moderation queues for users and listings, a dashboard with counters, and full search/filter over the listing table including crawled-source rows.

## Data model

Reuses `User.role = ADMIN`, `User.approval_status`, `Listing.status`. Admin events written to a generic audit table:

- `AuditLog` (`backend/app/db/models.py` ~line 1180) — `entity_type`, `entity_id`, `action`, `actor_id`, `payload`, `created_at`. Used for moderation traces, listing approve/reject, user approve/reject.

## API surface

`backend/app/api/v1/admin.py`.

| Verb | Path | Purpose |
|---|---|---|
| POST | `/auth/admin-login` | Username + password against `settings.admin_username` / `admin_password` config. Issues `scope="admin"` JWT. |
| GET | `/admin/dashboard` | Aggregated counters (active users, pending approvals, listings by status, etc.). |
| GET | `/admin/users` | Paginated user list with filters (role, approval_status, search). |
| POST | `/admin/users/{id}/approve` | Set `approval_status=APPROVED`. |
| POST | `/admin/users/{id}/reject` | Set `approval_status=REJECTED` with optional notes. |
| GET | `/admin/listings` | Paginated listing list including parsed sources and admin-only filters. |
| POST | `/admin/listings/{id}/approve` | `PENDING → ACTIVE`. |
| POST | `/admin/listings/{id}/reject` | `PENDING → REJECTED` with notes. |
| PATCH | `/admin/listings/{id}` | Admin edit (full schema). |
| GET | `/api/v1/activity-log` | Recent AuditLog rows (added in this iteration). |

All admin routes are gated by a `require_admin` dependency that asserts `current_user.role == ADMIN`.

## Behaviour & invariants

- **Auto-approve mode** — when `settings.auto_approve_users` / `settings.auto_approve_listings` is true, queues stay empty and approval steps are no-ops; the admin module still works for retrospective edits.
- **Listing edit** — admin uses the same validators as seller edit (matrix gate). No "force-bypass" flag.
- **Audit trail** — every approve / reject / admin-edit writes one `AuditLog` row.

## Frontend

`frontend/src/modules/admin/` — separate route tree mounted at `/admin/*`. Pages: dashboard, users queue, listings queue, listing-edit, audit log. Animated counters and progress rings on the dashboard.

## References

- `backend/app/api/v1/admin.py`
- `backend/app/api/v1/activity_log.py`
- `backend/app/db/models.py` — `AuditLog`.
- `frontend/src/modules/admin/`

## Known gaps

- §2.2 calls out admin listing-edit polish — separate from this spec; tracked in `../../partial/medium/pre-launch-fixes.md`.
