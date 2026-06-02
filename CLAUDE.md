# Ucharmarket Frontend — Claude Code Instructions

## Session Setup (run at the start of EVERY new session)

1. **Add the deploy repo to this session's scope.**
   Call `mcp__claude-code-remote__list_repos` to see available repos, then call
   `mcp__claude-code-remote__add_repo` with `hasanoff507/ucharmarket-frontend`.
   This is required so that GitHub Actions deploy can be triggered directly from
   this session (see Deploy section below).

## Project Structure

- `frontend/` — React + TypeScript + Vite SPA (Mantine UI, Effector, i18next, React Router)
- `backend/` — Python/FastAPI backend
- `db/` — SQL migrations / schema snapshots

## Deploy Pipeline

Production VPS deploys are triggered by pushing to **`main`** on
`hasanoff507/ucharmarket-frontend` via GitHub Actions (`.github/workflows/deploy.yml`).

This repo (`bgaybullaev-droid/ucharmarket-frontend`) is the **mirror** used for
development. After pushing here, sync to hasanoff507 to trigger the VPS deploy:

```bash
# On your local machine — sync mirror → main repo
git remote add bgaybullaev https://github.com/bgaybullaev-droid/ucharmarket-frontend.git
git fetch bgaybullaev main
git merge bgaybullaev/main
git push origin main   # origin = hasanoff507
```

Or, if hasanoff507 is in session scope, trigger `workflow_dispatch` directly:
```
mcp__github__actions_run_trigger(method=run_workflow, owner=hasanoff507,
  repo=ucharmarket-frontend, workflow_id=deploy.yml, ref=main)
```

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/modules/buyer/pages/settings/ui/page/Page.tsx` | Settings page (buyer + seller) |
| `frontend/src/modules/admin/app/ui/layout/AdminLayout.tsx` | Admin panel layout |
| `frontend/index.html` | Browser tab title, meta description |
| `frontend/src/shared/i18n/locales/ru/seller.json` | Seller namespace translations |
| `.github/workflows/deploy.yml` | VPS deploy (only runs on hasanoff507 repo) |

## Dev Commands

```bash
cd frontend
npm run dev          # start dev server
npm run type-check   # TypeScript check
npm run build        # production build
npm run lint         # ESLint
```

## Claude Behaviour Rules

В КАЖДОМ ответе сначала идёт основной текст, а в самом конце — отдельный
короткий блок **«Кратко»**: простыми словами, суть всего написанного выше,
без потери ключевых моментов.

Каждый план (файл плана в plan mode) завершается разделом
**«Кратко (простыми словами)»** с кратким изложением плана обычным языком.
