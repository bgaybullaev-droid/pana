# Ребрендинг → **PANA** (план замены имён)

> Цель: заменить разнобой в названиях проекта (`Ucharmarket` / `UcharMarket` /
> `Real Estate`) на единый бренд **PANA** (заглавными буквами) во всех местах,
> где это **отображается пользователю**.
>
> Источник: research 5 агентов по всему репозиторию (frontend, backend, i18n,
> html/config, docs/deploy/db). Дата: 2026-06-25.

---

## ⚠️ Главное различие, которое надо держать в голове

Слово **«Real Estate» встречается в ДВУХ разных смыслах** — и менять надо
по-разному:

1. **Как название бренда/приложения** (например в welcome-сообщении бота
   «Добро пожаловать в **Real Estate**!») → это и есть бренд → **меняем на PANA**.
2. **Как обычный отраслевой термин** = «недвижимость» (класс `RealEstateException`,
   schema.org `RealEstateListing`, «real estate marketplace», файл
   `real_estate.yaml`, промпты «real estate listing translator») → это **НЕ бренд**,
   это просто слово «недвижимость» → **НЕ трогаем**.

Аналогично `Ucharmarket` бывает: (а) видимый бренд-текст и (б) инфраструктура
(домен `ucharmarket.uz`, имя репозитория, БД, бот `@ucharmarket_bot`). Менять
безопасно только (а).

---

## 🟢 ГРУППА 1 — Пользовательский бренд-текст → меняем на **PANA**

Это безопасно, видно пользователю, не ломает прод.

### 1.1 i18n переводы (4 языка × файлы) — `UcharMarket` → `PANA`
`frontend/src/shared/i18n/locales/{ru,uz,uz-cyrl,uz-latn}/`

| Файл | Строки (ключи) |
|------|----------------|
| `admin.json` | `header.brand` |
| `buyer.json` | `mobileOnly.description`, `search.onboarding.title`, `profile.version` («UcharMarket v1.0.0» → «PANA v1.0.0»), `menu.shareText`, `about.description`, `faq.q1`, `faq.a1`, `settings.shareText`, `realtors.description`, `privacy.intro`, `terms.intro`, `terms.section1Text`, `terms.section4Text`, `terms.section5Text` |
| `seller.json` | `referrals.shareCta` |

> ~60 строк суммарно. Везде заменяем только слово «UcharMarket» → «PANA».
> Текст вокруг (недвижимость/ko'chmas mulk) — без изменений.

### 1.2 Хардкод в коде фронтенда
| Файл | Что | Замена |
|------|-----|--------|
| `frontend/index.html:19` | `<title>Ucharmarket - Вся недвижимость…</title>` | `PANA - …` |
| `frontend/index.html:7` | `<meta name="description" content="Ucharmarket - …">` | `PANA - …` |
| `frontend/src/app/pages/auth/AuthPage.tsx:119` | логотип-текст `UcharMarket` | `PANA` |
| `frontend/src/modules/buyer/pages/about/ui/page/Page.tsx:45` | заголовок `UcharMarket` | `PANA` |
| `frontend/src/modules/admin/app/ui/layout/AdminLayout.tsx:21` | `document.title = "Ucharmarket - Вся недвижимость Узбекистана"` | `PANA - …` |
| `frontend/src/modules/seller/pages/referrals/ui/page/Page.tsx:106,117,122,158` | fallback `"Присоединяйся к UcharMarket!"` | `…PANA!` |
| `frontend/src/modules/buyer/pages/settings/ui/page/Page.tsx:142` | share `title: "UcharMarket"` | `"PANA"` |

### 1.3 Бэкенд — видимые тексты (Telegram-бот, SEO, шаблоны)
| Файл | Что |
|------|-----|
| `backend/app/bot/translations/{ru,uz,uz_cyrl}.json` | `notification_approved`, `registration_auto_approved`, `welcome`, `welcome_trilingual`, `search_open_in_app` — «Real Estate»/«UcharMarket» как бренд → `PANA` |
| `backend/app/api/v1/seo.py:155-182` | `cta`, `open_app` — «Открыть в UcharMarket» → «Открыть в PANA» |
| `backend/app/services/seo_meta.py:122` | `_BRAND_NAME = "UcharMarket"` → `"PANA"` (один источник правды для SEO-заголовков) |
| `backend/app/services/seller_contact.py:42,46,50` | шаблоны «Увидел в UcharMarket…» → PANA |
| `backend/app/templates/seo/gone.html:7`, `base.html:66` | `<title>… — UcharMarket`, footer `UcharMarket © {year}` → PANA |
| `backend/app/bot/setup.py:33` | `MENU_BUTTON_TEXT = "UcharMarket"` → `"PANA"` |

### 1.4 Документация/README (видимый бренд)
| Файл | Что |
|------|-----|
| `frontend/README.md:1,3` | заголовок и «Frontend for UcharMarket — a real estate marketplace» → «Frontend for PANA — a real estate marketplace» (слово real estate тут = термин, оставляем) |
| `frontend/.env.example:1,7` | `# Real Estate Frontend…` / `VITE_APP_NAME=Real Estate` → `PANA` (видимое имя приложения) |
| `backend/.env.example:2` | `# UcharMarket Backend Configuration` → `PANA` |

---

## 🔴 ГРУППА 2 — Инфраструктура → **НЕ менять** (сломает прод)

Это технические идентификаторы; смена названия бренда их не меняет. Менять = положить прод.

- **Домен:** `ucharmarket.uz` — nginx `server_name`, SSL-сертификаты
  (`/etc/letsencrypt/live/ucharmarket.uz/…`), `netlify.toml`, `_redirects`,
  `config.py f3_public_web_host`, `index.html` preconnect `api.realestate.uz`,
  все `https://ucharmarket.uz/...` в коде/тестах/spec-kit.
- **GitHub-репозитории:** `hasanoff507/ucharmarket-frontend`,
  `bgaybullaev-droid/ucharmarket-frontend` (deploy.yml, mirror.yml, CLAUDE.md).
- **База данных:** `real_estate` (alembic.ini, config.py, .env), `ucharmarket`
  (init-db.sql owner/grant), `ucharmarket_test` (conftest).
- **Telegram-бот username:** `@ucharmarket_bot`, `@ucharmarket_support`,
  `ucharTestMarket_bot`, дефолты `UcharMarketBot` — это реальные хэндлы в Telegram.
- **S3 bucket:** `realestate-images`. **npm package:** `realestate-frontend`.
  **APP_NAME=ucharmarket**, Celery queue `realestate`, OSM user-agent
  `ucharmarket-seed/1.0`, хэштеги `#ucharmarket` в seed-шаблонах.
- **Email:** `support@ucharmarket.uz`.

> Эти места меняются ТОЛЬКО когда реально мигрируют домен/репо/БД/бота — отдельной
> большой задачей с DNS, сертификатами, ботом и т.д. Не в рамках текстового ребрендинга.

---

## 🟡 ГРУППА 3 — Generic «real estate» = «недвижимость» → **НЕ трогаем**

Это не бренд, это термин. Замена на PANA сломает смысл.

- `RealEstateException` (класс), `realestate_exception_handler`, `RealEstateListing`
  (schema.org `@type` в JSON-LD), FastAPI `title="Real Estate API"` (внутреннее
  имя API), docstrings «Real Estate Backend Application».
- Промпты LLM: «real estate listing translator», «real-estate copywriter».
- Файлы-схемы краулера: `real_estate.yaml`, `olx_real_estate.yaml`.
- `db/real_estate.sql` (дамп БД), seed permission `REAL ESTATE / admin_real_estate`.
- Комментарии «# for any real-estate listing» и т.п.

---

## 🟠 ГРУППА 4 — Внутренние тех-идентификаторы/комментарии (опционально, косметика)

Не видно пользователю; можно причесать ради консистентности, но необязательно и
безопасно. Решение — на ваше усмотрение:

- Комментарии с «UcharMarket» (`config.py:103`, `handlers.py:2072`, `inline.py`,
  `RootPage.tsx:8`, `theme.ts:3 // Real Estate brand colors`).
- LLM-промпты, где «UcharMarket» — часть текста для модели (`prompts.py:21`,
  миграции `…prompt_v2/v3.py`). ⚠️ Менять имя в промпте может слегка изменить
  генерацию описаний — лучше обсудить отдельно.
- Дефолтные fallback-значения бот-username в коде (это инфра, см. Группу 2).

---

## ✅ Итог-таблица решения

| Группа | Что | Делаем |
|--------|-----|--------|
| 1 | Пользовательский бренд-текст (i18n, заголовки, бот-сообщения, SEO-метки, About/Auth/Settings) | **Меняем на PANA** |
| 2 | Домен, репо, БД, бот-username, S3, npm, email | **НЕ трогаем** (отдельная инфра-миграция) |
| 3 | Generic «real estate» = недвижимость | **НЕ трогаем** |
| 4 | Внутренние комментарии/промпты/идентификаторы | **Опционально**, по согласованию |

---

### Кратко (простыми словами)

5 агентов прочесали весь проект и нашли, где написано «Ucharmarket» и «Real Estate».
Я разложил всё на 4 кучки:

1. **Видимый бренд-текст** (то, что юзер реально читает: переводы, заголовок
   вкладки, сообщения бота, страницы About/Auth/Settings) — **это меняем на PANA**.
2. **Инфраструктура** (домен ucharmarket.uz, гитхаб-репо, база данных, юзернейм
   бота, сертификаты) — **трогать нельзя**, иначе прод ляжет; это меняется только
   при реальном переезде домена/бота отдельной большой задачей.
3. **Слово «real estate» в смысле «недвижимость»** (не бренд, а просто термин) —
   **оставляем как есть**.
4. **Внутренние комментарии и промпты** — можно причесать, но необязательно;
   решаем отдельно.

Дальше нужен ваш ответ по объёму (см. вопрос), и после «гоу» я меняю Группу 1.
