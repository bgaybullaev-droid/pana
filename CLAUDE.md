# Ucharmarket Frontend — Claude Code Instructions

## Session Setup (run at the start of EVERY new session)

1. **Switch to main branch immediately.**
   Run `git checkout main && git pull origin main` before doing anything else.
   All commits and pushes go directly to `main` — never work on a `claude/...`
   feature branch unless the user explicitly asks for it.

2. **Add the deploy repo to this session's scope.**
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

`bgaybullaev-droid/ucharmarket-frontend` настроен как **автоматическое зеркало**:
пуш в `main` здесь → автоматически синхронизируется в `hasanoff507/main` → триггерит деплой на VPS.

**Ручная синхронизация не нужна.** Достаточно запушить изменения в `main` этого репо.

### Что делает слово «пуш» — полный цикл (запомнить, чтобы не путаться)

Когда пользователь пишет **«пуш»**, моих действий ровно два:
1. Перевести текущий PR из draft в ready (`update_pull_request`, `draft: false`).
2. Смержить PR в `main` (`merge_pull_request`, обычно `squash`).

Дальше всё происходит **АВТОМАТИЧЕСКИ — вручную запускать НИЧЕГО не нужно**:
3. Push в `main` (bgaybullaev-droid) → workflow «Mirror to hasanoff507» зеркалит
   коммит в `hasanoff507/main`.
4. В `hasanoff507` срабатывает `deploy.yml` (триггер: push в `main` по путям
   `frontend/** | backend/** | db/** | .github/workflows/deploy.yml`; job идёт
   только при `github.repository == 'hasanoff507/ucharmarket-frontend'`).
5. На VPS `deploy.yml` синкает код **и сам применяет миграции БД** — шаг
   `docker compose run --rm api alembic upgrade head`.

Важно (это было источником прошлой путаницы):
- **НЕ предлагать и НЕ пытаться запускать `alembic upgrade head` вручную** —
  деплой делает это сам. После merge миграции применяются автоматически.
- Продакшен-БД сидит на LAN VPS (`192.168.0.187:5432`) и **из контейнера Claude
  недоступна** (нет ни сети, ни кред) — миграции гоняются только на VPS через
  `deploy.yml`. Не пытаться подключаться к БД из сессии.
- Сам job деплоя крутится в репозитории `hasanoff507`, который **вне скоупа**
  сессии bgaybullaev-droid, поэтому финальный статус деплоя из сессии не виден.
  Проверка при необходимости: Actions в hasanoff507 (job «Deploy to VPS» → шаг
  «Apply database migrations») либо на VPS команда `alembic current`.
- Деплой запускается **только** при изменениях `frontend/** | backend/** | db/**
  | deploy.yml`. Правки только в `CLAUDE.md`/доках деплой НЕ триггерят.

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

### Структура каждого ответа (визуальное разделение)

Ответ всегда делится горизонтальными линиями `---` на зоны, чтобы взгляд сразу
ловил, где главное:

1. **Рабочий процесс** (сверху): рассуждения, что делаю/проверяю, ход работы,
   команды, промежуточные находки.
2. `---` — линия-разделитель.
3. **Блок результата** — что уже сделано / итог. Заголовок делать КРУПНЫМ и
   заметным: уровень `##` + эмодзи (например `## ✅ Готово` или `## Итог`), чтобы
   он выделялся среди текста. Внутри — только итог: что сделано, ссылки, статусы.
4. `---` — линия-разделитель.
5. **Блок «Кратко (простыми словами)»** — заголовком `###`, простыми словами,
   суть всего сказанного выше без потери ключевых моментов.

Главное правило: весь процесс работы (мысли/действия) **отделён линией `---`** от
блока результата, а блок результата — линией от «Кратко». Так пользователь быстро
находит, что именно сделано, не вычитывая весь процесс. (Если ответ совсем
короткий — допускается только блок результата + «Кратко».)

### План в plan mode

Каждый план (файл плана) завершается разделом **«Кратко (простыми словами)»** с
кратким изложением плана обычным языком.

### Тестирование перед пушем и мержем

Перед каждым пушем и мержем — обязательно провести тестирование согласно
стандартам отрасли:
- `npm run type-check` — проверка типов TypeScript
- `npm run lint` — проверка ESLint
- `npm run build` — убедиться, что сборка проходит без ошибок
Если хотя бы одна проверка упала — пуш и мердж запрещены до устранения ошибок.

### Авто-деплой в облачной сессии (когда работаю «в облаке»)

Контекст: в облачной сессии пользователь не может посмотреть результат глазами
(он уже на проде / работает удалённо), поэтому ручное звено «пуш» убирается —
правки уезжают в прод сами.

**Когда применяется.** В любой *облачной/удалённой* сессии — web / mobile /
desktop app, GitHub Action, т.е. managed remote execution environment. В
*локальной* сессии на машине пользователя (где можно глянуть глазами) авто-деплой
НЕ включается — там остаётся ручной «пуш».

**Триггер — «после каждой задачи»** (НЕ после каждой отдельной правки файла).
Закончив все правки по запросу пользователя, я автоматически, без слова «пуш»,
прогоняю полный цикл:
1. Закоммитить изменения.
2. **Тест-гейт (обязателен всегда):** `npm run type-check` → `npm run lint` →
   `npm run build`.
3. Если **все** проверки зелёные → перевести PR из draft в ready +
   `squash`-merge в `main` → дальше авто-зеркало в `hasanoff507/main` →
   авто-деплой на VPS (+ миграции). Полный цикл описан в **Deploy Pipeline**.
4. Если **хоть одна** проверка упала → **деплой НЕ делать**, остановиться,
   починить и сообщить пользователю об ошибке. Сломанный код в прод не уезжает.

**Важно:**
- Один деплой = один завершённый запрос. Промежуточные/недоделанные состояния в
  прод не уезжают.
- Изменения только в `CLAUDE.md`/доках тоже мержатся в `main`, но VPS-деплой не
  триггерят (см. Deploy Pipeline) — это нормально.
- Тест-гейт отключать нельзя ни при каких условиях (см. «Тестирование перед
  пушем и мержем»). Авто-деплой не отменяет тесты, а идёт строго после них.

### Слово «пуш»

Когда пользователь пишет слово **«пуш»** — перевести текущий PR из draft в ready и
смержить (полный цикл и авто-миграция БД описаны выше в разделе **Deploy Pipeline →
«Что делает слово „пуш"»**). Вручную после merge ничего запускать не нужно.

В *облачной* сессии этого слова можно не ждать — мерж в `main` происходит
автоматически после каждой завершённой задачи (см. **«Авто-деплой в облачной
сессии»**). Слово «пуш» остаётся как ручной способ форсировать мерж: например, в
локальной сессии или чтобы задеплоить прямо сейчас, не дожидаясь конца задачи.
