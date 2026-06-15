# Блок D — FOLLOWUP_PLAN: план доводки до полного соответствия спецификации

> **Роль документа:** операционный план доделок Блока D (Telegram-механики V2.0)
> по итогам аудита кода от **2026-06-12**. Исходная спецификация:
> [SOURCE_SPEC_V2.md](SOURCE_SPEC_V2.md). Решения по умолчанию наследуются из
> [decision-pass/DECISION_MATRIX.md](decision-pass/DECISION_MATRIX.md).
>
> **Как пользоваться в новой сессии:** сказать «работаем по FOLLOWUP_PLAN Блока D»
> → взять первый незакрытый PR из чек-листа ниже → реализовать по его разделу →
> прогнать тест-гейт → смержить → **обновить статус в чек-листе этим же PR-ом
> или следующим**. Один PR = один завершённый кусок работы.
>
> Все file:line-ссылки проверены по коду 2026-06-12. Если код уехал — ориентиры
> искать по именам функций, они стабильнее номеров строк.

---

## Статус работ (живой чек-лист — обновлять при каждом merge)

| PR | Название | Оценка | Статус |
|----|----------|--------|--------|
| FU1 | Быстрые фиксы (is_personal, «неактуально», RU-строки) | 0.5 д | ✅ смержен (#86) |
| FU2 | D4 «последняя миля»: publish_to_channel + stale в «Моих объявлениях» | 2 д | ✅ выполнено (сверено с кодом 2026-06-15) |
| FU3 | Rate limits бот-поиска и inline | 0.5 д | ⬜ не начат |
| FU4 | Тесты Блока D (golden-корпус парсера и др.) | 1.5 д | ⬜ не начат |
| FU5 | Телеметрия парсера запросов | 1 д | ⬜ не начат |
| FU6 | Filter-дип-линки: фикс гидрации + маркетинговые слаги | 1 д | ⬜ не начат |
| FU7 | Дайджест push-уведомлений по сохранённым поискам | 1.5 д | ⬜ не начат |
| FU8 | Доки/ops: BotFather-док, e2e чек-лист, 48h-spike | 0.5 д | ⬜ не начат |

Статусы: ⬜ не начат · 🟨 в работе · ✅ смержен (`#номер PR`).

**Порядок:** FU1 → FU2 → FU3 → FU4 → FU5 → FU6 → FU7 → FU8.
Жёсткие зависимости: **FU4 после FU2/FU3** (тестирует их поверхности) и
**до FU7** (parity-тест переводов охраняет новые ключи FU7). FU5 и FU6
независимы, можно менять местами. Каждый PR проходит стандартный цикл из
CLAUDE.md: тест-гейт → squash-merge в `main` → авто-зеркало → авто-деплой
(+ alembic на VPS — миграции в FU2/FU5 применятся сами).

---

## Что уже есть — НЕ переделывать

Проверено по коду; при реализации переиспользовать, а не строить заново:

| Готовый механизм | Где | Используется в |
|---|---|---|
| Per-channel замок 1 edit/sec (Redis SETNX, TTL 1с, wait 5с) | `backend/app/services/channel_publisher.py:99-127` | (решение D4-Q7 уже выполнено — из плана исключено) |
| Дебаунс-группировка push (RPUSH pending + SETNX scheduled + flush c countdown) | `backend/app/workers/tasks/crawled_match.py:65-82, 266-319` (окно 60с) | FU7 (зеркалировать для покупателя) |
| Direct-link Mini App `?startapp=` | `backend/app/services/deeplink.py` (`build_listing_link`, `build_filter_link`) | FU6 (рекомендация «использовать startapp» уже выполнена) |
| i18n-ключи `autopost.*` ВКЛЮЧАЯ `checkbox_publish`, `badge_stale`, `update_btn`, `media_modal_*` | `frontend/src/shared/i18n/locales/{ru,uz,uz-cyrl,uz-latn}/seller.json` | FU2 (переводы заведены заранее — нужен только UI) |
| Redis-клиент async/sync + паттерны NX+EX | `backend/app/db/redis.py` (`get_redis`), примеры: `services/behavioral_signals.py:169`, `crawled_match.py:75-82` | FU3, FU5, FU7 |
| Гидрация фильтров главной из URL-параметров (`district`, `rooms`, `type`, `price_min/max`) | `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:322-361` + `HomeFilters` (`model/types/index.ts:7-44`) | FU6 |
| Словарь районов с алиасами (лат/кир/опечатки) | `backend/app/core/regions.py` (`_DISTRICT_ALIASES`, `infer_region`) | FU6 |
| Спека клавиатуры push | `backend/app/services/listing_push.py:37` (`build_listing_action_kb_spec`) | FU7 |

---

## Найденные скрытые баги (чинятся в FU1, FU2, FU6)

1. **Inline Mode отдаёт кэш чужого языка.** `bot/inline.py:126` —
   `is_personal=False` при языкозависимой выдаче: Telegram кэширует ответ на
   запрос для всех пользователей → узбекоязычный получает русскую выдачу. → FU1.
2. **Заклеймленные объявления автопостятся.** Пути claim-olx / claim-telegram
   (`api/v1/listings.py:2688-2690, 2880-2882` → `services/crawler_service.py:
   convert_olx_to_listing:532/566, convert_telegram_to_listing:613/649`,
   `source_type=CLAIMED`) переводят объявление в `PENDING_GENERATION`; по
   завершении F1 `ai_generation.py:614` вызывает `_enqueue_autopost` — и пост
   уходит в канал, хотя по решению D4-Q2 для claimed дефолт «не публиковать». → FU2.
3. **Дип-линки фильтров не работают на фронте.** Событие `filtersApplied`
   (эмит в `Router.tsx:92`) **никем не слушается** — `filter_<id>` тихо no-op,
   включая кнопку бота «Открыть все в приложении». → FU6.

---

## PR-FU1 — Быстрые фиксы (0.5 дня)

**Цель:** закрыть баг кэша inline, тупиковые push-сообщения и нарушение
языковой консистентности.

**Изменения:**

1. `backend/app/bot/inline.py:126` (и аналогичный answer на :133) —
   `is_personal=True`. Комментарий в коде: выдача зависит от языка пользователя.
2. `backend/app/bot/handlers.py:2091-2112` — ветка колбэка по снятому
   объявлению: вместо только `edit_reply_markup(None)` (:2105) редактировать и
   тело: если `call.message.caption is not None` → `edit_caption(caption=старый
   + "\n\n" + t(lang, "push_listing_unavailable"), reply_markup=None)` (caption
   обрезать до 1024), иначе `edit_text(...)` по той же схеме. Тост (:2109)
   оставить.
3. Вынести 4 жёстких RU-строки в переводы (`bot/translations/{ru,uz,uz_cyrl}.json`,
   плоские snake_case ключи по конвенции файла):
   - `handlers.py:269` → `link_already_linked`
   - `handlers.py:276-278` (f-string с `{phone}`) → `link_success` (kwargs `phone`)
   - `handlers.py:282-283` → `link_user_not_found`
   - `handlers.py:2079` → `fav_open_app_hint`

**Критерии приёмки:**
- В групповом чате два пользователя с разными языками видят inline-выдачу
  каждый на своём языке.
- Тап «В избранное» по снятому объявлению: сообщение получает локализованную
  приписку «уже неактуально», клавиатура исчезает (соответствие edge case
  SOURCE_SPEC_V2 → D2).
- `rg -n '[А-Яа-яЁё]' backend/app/bot/handlers.py` не находит пользовательских
  литералов вне форматирования поисковой выдачи (:2268-2274 — форматирование
  данных, известное исключение; локализация этих строк — за рамками FU1).

**Тесты:** ручной смоук бота; parity-тест переводов приедет в FU4.

---

## PR-FU2 — D4 «последняя миля» (2 дня)

> **Статус: ✅ выполнено** (сверено с кодом 2026-06-15). Все 11 пунктов ниже
> реализованы и смержены: бэкенд 1–7, фронт 8–11, тесты
> (`test_autopost_dispatch_gate.py`, `test_sellers_routes.py`). Чек-лист
> оставлен для истории. Доделано сверх плана: авто-публикация при включении
> тумблера (`_maybe_publish_optin_listing`), диагностика «Последняя публикация»
> в кабинете (`autopost_last_result`), отправка фото в канал файлом/с диска
> (`channel_publisher._photo_input`). **Следующий незакрытый PR — FU3.**

**Цель:** per-listing контроль публикации (чекбокс из спеки, D4-Q2) и
индикация устаревшего поста + кнопка «Обновить» на карточках «Мои объявления»
(спека требует в обоих местах).

### Бэкенд

1. **Миграция** `backend/alembic/versions/20260612_add_listing_publish_to_channel.py`
   (именование по образцу `20260610_add_user_seller_profile.py`):
   `listings.publish_to_channel BOOLEAN NOT NULL server_default=true` +
   backfill `UPDATE listings SET publish_to_channel = FALSE WHERE source_type
   IN ('CLAIMED','PARSED')` — **сверить регистр литералов enum с существующей
   миграцией перед написанием**.
2. `backend/app/db/models.py` — колонка на `Listing` (класс :373, рядом с
   `version` :632).
3. Проставление `publish_to_channel=False` при клейме — **во всех 4 точках**:
   - `backend/app/services/crawler_service.py` — конструкторы в
     `convert_olx_to_listing` (:566) и `convert_telegram_to_listing` (:649)
     (та же транзакция, закрывает гонку с F1);
   - `backend/app/api/v1/claims.py:108-110` (phone-match) и `:229-231` (OTP).
4. **Гейты публикации** (⚠️ НЕ в `services/autopost.py:decide_transition` —
   это мёртвый код без вызовов, гейт там = тихий no-op):
   - `api/v1/listings.py:108` (publish-ветка `_dispatch_autopost_for_status_change`):
     `if not listing.publish_to_channel: return` — только для новых публикаций;
     ветки mark_sold/delete не трогать (жизненный цикл уже существующих постов
     сохраняется);
   - `workers/tasks/ai_generation.py:634` (`_enqueue_autopost`) — тот же guard
     после загрузки listing (именно он чинит claim-путь);
   - defense-in-depth: skip+log в начале таска `publish_listing_to_channel`
     (`workers/tasks/autopost.py:128`).
5. **Exclude из version-bump:** `api/v1/listings.py:3922` —
   `if set(update_data) - {"publish_to_channel"}: listing.version += 1`
   (иначе переключение чекбокса ложно пометит живой пост устаревшим).
6. Схемы `backend/app/schemas/listing.py`: `ListingCreate` (:208) /
   `ListingUpdate` (:217) — `publish_to_channel: Optional[bool]`; протащить в
   конструкторы create/draft в `listings.py`.
7. `GET /sellers/me/listings` (`backend/app/api/v1/sellers.py:241-315`,
   `get_seller_listings`) — **второй сгруппированный запрос, не JOIN** (JOIN
   ломает count-подзапрос :262): после выборки страницы
   `select(BotChannelPost.listing_id, id, last_listing_version).where(seller_id=…,
   status=="live", listing_id.in_(ids))` (едет по индексу
   `idx_bot_channel_posts_seller_status`, models.py:2247-2251);
   `autopost_is_stale = listing.version > last_listing_version` в Python
   (та же семантика, что в `/seller/autopost/status`). В
   `SellerListingListResponse` (`schemas/listing.py:515-520`) добавить
   `autopost_post_id: Optional[UUID] = None`, `autopost_is_stale: bool = False`.

### Фронтенд

8. Поднять `fetchAutopostStatusFx` + тип `AutopostStatus` из
   `modules/seller/pages/autoposting/model/effects/index.ts:4-48` в
   `modules/seller/shared/state/model/{effects,stores,types}` (+ стор
   `$autopostStatus`, initial null); из модуля autoposting — ре-экспорт, чтобы
   его импорты не менялись.
9. Чекбокс: `publish_to_channel: true` по умолчанию в `ListingFormValues`
   (`modules/seller/feature/listing-form/ui/useListingForm.ts`), включить в
   `buildListingData`; добавить в `ListingCreateData`
   (`shared/state/listing/model/types`). UI — Mantine `Switch` на шаге
   публикации create- и edit-форм, **виден только при
   `$autopostStatus?.connected && enabled`** (fetch на маунте, если стор пуст).
   Ключ `seller:autopost.checkbox_publish` уже есть во всех 4 локалях.
10. «Мои объявления» (`modules/seller/pages/listings/ui/page/Page.tsx`,
    карточки :235-283): расширить `SellerListingItem`
    (`modules/seller/shared/state/model/types/index.ts:28`) **опциональными**
    `autopost_post_id?`, `autopost_is_stale?` (деплой-skew); при
    `autopost_post_id && autopost_is_stale` — бейдж `autopost.badge_stale` +
    кнопка `autopost.update_btn` → `updateChannelPostFx({postId})`; ответ
    `media_too_old` открывает общий модал (п. 11); после успеха — рефетч списка.
11. Вынести 48h-модал из `autoposting/ui/page/Page.tsx:299-342` в
    `modules/seller/feature/media-cutoff-modal/` (props: `opened`,
    `postAgeHours`, `onTextOnly`, `onRecreate`, `onCancel`); подключить на
    обеих страницах.

**Критерии приёмки:**
- Клейм любым путём (OTP, phone-match, claim-olx, claim-telegram) не порождает
  пост в канале, даже когда F1 завершается после клейма.
- Новое ручное объявление со снятым Switch → поста нет; со включённым → пост есть.
- Переключение одного Switch не меняет `Listing.version` (нет ложного stale).
- Устаревший пост виден бейджем в «Моих объявлениях»; «Обновить» ставит правку
  в очередь; для поста старше 48ч с изменённым фото модал с 3 вариантами
  работает на обеих страницах.

**Тесты (минимум в этом PR, остальное FU4):** unit на гейт
`_dispatch_autopost_for_status_change` (mock `.delay`); integration на
`/sellers/me/listings` с полями autopost.

---

## PR-FU3 — Rate limits бота (0.5 дня)

**Цель:** защита поиска в боте и Inline Mode от спама (требование SOURCE_SPEC_V2 → D5).

**Дизайн:** новый модуль `backend/app/bot/rate_limit.py`:
`async def hit(scope: str, user_id: int, limit: int, window: int) -> bool` —
Redis `INCR` + `EXPIRE` на первом инкременте, ключи `bot:rl:{scope}:{tg_id}`,
**fail-open** при ошибках Redis (философия «Redis non-fatal», `bot/main.py:150-156`).
Middleware сознательно НЕ используем: каталога `bot/middlewares/` нет,
единственный `DbSessionMiddleware` (`bot/main.py:36-42`) зарегистрирован только
на message/callback (:97-98) — **inline-хэндлеры живут без DB-сессии**, и
поведение при превышении на двух поверхностях разное.

**Точки врезки:**
- начало `_run_bot_search_reply` (`bot/handlers.py`, def перед :2240) — одна
  точка покрывает и `/search` (:2316), и свободный текст (:2342). Лимит
  **10/60с**; при превышении `message.answer(t(lang, "search_rate_limited"))`
  и `return True` (чтобы `cmd_search` не добавил «не понял запрос»);
- начало `handle_inline_query` (`bot/inline.py:102`). Лимит **30/60с**; при
  превышении `query.answer([], cache_time=5, is_personal=True)` (короткий
  cache_time, чтобы не закэшировать пустоту на 60с).

Новый ключ `search_rate_limited` ×3 локали бота.

**Критерии приёмки:** 11-й текстовый запрос за минуту получает локализованный
ответ «слишком часто» (и `/search` не дублирует «не понял»); 31-й inline-запрос
за минуту — пустой ответ с cache_time=5; при недоступном Redis поиск работает
(fail-open).

**Тесты:** unit лимитера со стабом Redis (сброс окна, fail-open).

---

## PR-FU4 — Тесты Блока D (1.5 дня)

**Цель:** закрыть главный системный пробел — ноль автотестов на модули блока.
Конвенции: `pytest.ini` (`asyncio_mode=auto`, маркеры unit/integration),
стиль `tests/unit/test_saved_search_matcher.py` (классы, inline-фабрика
`_mk(**over)`, `pytestmark = pytest.mark.unit`).

1. **`tests/unit/test_query_parser.py` — golden-корпус 60–100 запросов**,
   таблично: районы кириллицей/латиницей/с опечатками («Чилонзар», «Chilanzar»,
   «Чнланзр»), комнаты ru/uz («2комн», «двухкомнатная», «2 xona»), цены
   («до 35тыс», «до $40k» → currency USD, голое число → UZS по D5-Q8), типы
   сделки/объекта incl. «sotiladi», «ijara», «xonadon», негативы («привет»,
   «ужин» → `is_empty`). Корпус — живой актив: пополнять из телеметрии FU5.
2. **`tests/unit/test_autopost_domain.py`**: матрица `decide_transition`,
   `is_post_stale`, граница 48ч `media_edit_allowed`, обрезка
   `render_post_body` (1024/700) + футер по 3 локалям, `is_autopost_ready`.
   **Плюс обязательно** тесты `_dispatch_autopost_for_status_change`
   (api-слой) — домен-функция мертва, тестировать то, что выполняется в проде.
3. **Deeplink:** unit — формат `build_listing_link`, длина/чарсет short-id,
   round-trip `build_filter_link`; integration —
   `GET /api/v1/deep-links/{id}` (found / 404 / wrong-kind) в
   `tests/integration/api/`.
4. **Parity переводов:** key-set бота равен по `{ru,uz,uz_cyrl}.json`; фронт —
   равенство наборов ключей `seller.json` по 4 локалям (чистый pytest, читающий
   JSON из репо; без FE-тулинга).

**Критерии приёмки:** `pytest -m unit` и `-m integration` зелёные; parity-тест
падает при дрейфе любой локали.

---

## PR-FU5 — Телеметрия парсера запросов (1 день)

**Цель:** данные для итерации словаря и для решения rule-based → LLM из
DECISION_MATRIX (порог пересмотра: >10% промахов за месяц).

1. Миграция + модель `BotSearchQuery`: `id`, `user_telegram_id BIGINT NULL`,
   `source` (`bot`|`inline`), `raw_text VARCHAR(200)`, `extracted_fields`
   (JSONB или ARRAY), `results_count INT`, `created_at` (index).
2. Запись **через Celery-таск** `record_bot_search_query.delay(...)`
   (новый `workers/tasks/telemetry.py`) — fire-and-forget; прямой DB-вызов
   невозможен: inline-хэндлеры без сессии (см. FU3). Вызовы: из
   `_run_bot_search_reply` после `search()` и из `handle_inline_query`
   (только непустой raw).
3. Beat-prune 90 дней — зеркало `prune-behavioral-signals`
   (`workers/celery_app.py:99-102`, таск в `workers/tasks/maintenance.py`
   по образцу `prune_behavioral_signals`), например daily 04:50.
4. Примеры SQL для продакт-анализа (включить в FU8-док): топ нераспознанных
   `raw_text` (`extracted_fields = '[]'`), доля пустых выдач по source.

**Критерии приёмки:** оба пути поиска пишут строки; сбой таска не ломает ответ
пользователю; prune удаляет старые строки.

---

## PR-FU6 — Filter-дип-линки: фикс гидрации + маркетинговые слаги (1 день)

**Цель:** починить мёртвую проводку `filter_<id>` (баг №3) и дать маркетингу
человекочитаемые ссылки `t.me/<bot>?startapp=filter_chilonzor_2rooms_rent`
(закрывает `spec-kit/not-started/easy/deep-links-filter-prefill.md`).

### Бэкенд

1. `services/deeplink.py` — `parse_filter_slug(slug) -> dict | None`:
   грамматика `<district>[_<N>rooms][_buy|_rent]` (синонимы: `buy|sale → sell`),
   район через `core/regions.py:_DISTRICT_ALIASES` (понимает chilanzar/чиланзар
   и опечатки); возвращает payload в том же словаре ключей, что строит бот в
   `handlers.py:2280-2289` (`district`, `rooms_min/rooms_max`, `deal_type`).
2. `api/v1/deep_links.py` — **ослабить валидацию :51** (сейчас isalnum ≤16) до
   `^[a-z0-9_]{1,32}$`; при отсутствии short-id в таблице — fallback на
   `parse_filter_slug` → синтезированный `DeepLinkResponse(kind="filter")`;
   `record_event` c outcome `resolved_slug`.
3. `bot/handlers.py` `_start_payload_filter` (:331-341) — тот же fallback перед
   `OUTCOME_REJECTED_UNKNOWN`.

### Фронтенд

4. `app/router/Router.tsx` — в `StartParamHandler` заменить мёртвый вызов
   `filtersApplied(coerceFilterPayload(...))` (:92) на сборку URLSearchParams и
   `navigate('/?'+qs, {replace:true})`: `district→district=<key>`,
   `deal_type→type=sell|rent`, `rooms_min..rooms_max→rooms=2,3` (cap 5),
   `price_min/price_max`, `property_type` — passthrough. Главная уже гидрирует
   всё это из URL (`home/ui/page/Page.tsx:322-361`). Удалить
   `coerceFilterPayload` (:27-41).

**Критерии приёмки:**
- `?startapp=filter_chilonzor_3rooms_rent` открывает ленту с district=chilonzor,
  rooms=3, type=rent (бейдж фильтра виден).
- Существующие short-id ссылки и кнопка бота «Открыть все в приложении»
  **реально применяют фильтры** (регресс-фикс).
- Неизвестный слаг: лента без фильтров, 404 от резолвера, событие в аналитике.

**Тесты:** unit slug-парсера (алиасы chilanzar/чиланзар, голый район,
только комнаты, мусор); расширить integration deeplink-тесты. Примеры ссылок
для маркетинга — в FU8-доке.

---

## PR-FU7 — Дайджест сохранённых поисков (1.5 дня)

**Цель:** «5 поисков сработали разом → одно сообщение, не пять» (edge case
SOURCE_SPEC_V2 → D2; в decision-pass отдан A4 — реализуем по паттерну A4).

**Дизайн (минимальный дифф):** вся логика в `_match_saved_searches`
(`workers/tasks/notifications.py:525+`) — матчинг, paused-check (:620),
дневной лимит (:628-636), in-app `Notification`-строки (:667-675), временное
окно (:692) — **не трогается**. Заменяется только немедленная отправка в
финальной ветке (:700+) на дебаунс-зеркало `crawled_match`:

- `RPUSH saved_search:pending:{user_id}` (TTL окно+60) +
  `SET NX saved_search:scheduled:{user_id}` → при первом хите
  `flush_pending_saved_search_pushes.apply_async(countdown=_BATCH_WINDOW_SEC)`;
- `_BATCH_WINDOW_SEC = 600` (осознанное отличие от 60с у A4: всплески импорта
  краулера растянуты на минуты; зафиксировать в docstring модуля);
- flush: dedupe listing_ids; **1 объявление** → текущий rich-push (вынести
  существующий рендер тела + `build_listing_action_kb_spec` в хелпер и
  переиспользовать); **>1** → дайджест `t(lang, "push_saved_search_digest",
  count=N)` + кнопка открытия TWA (существующая спека open-app клавиатуры);
- `TelegramForbiddenError` → log+return (как в crawled_match);
- примечание в docstring: дневной лимит списывается по-объектно в момент
  матча (консервативно; дайджест шлёт ≤ бюджета).

Новый ключ `push_saved_search_digest` ×3 локали бота.

**Критерии приёмки:** 5 объявлений за 10 минут для одного пользователя →
ровно 1 дайджест-push и 5 in-app Notification-строк; одиночный матч → прежний
rich-push с клавиатурой; заблокировавший бота пользователь не валит flush.

**Тесты:** unit решения flush (1 vs N) со стабами redis/sender.

---

## PR-FU8 — Доки/ops (0.5 дня)

1. **`docs/telegram-bot-setup.md`** — критерий готовности D1 «конфигурация
   задокументирована»: Menu Button ставится кодом (`bot/setup.py`, текст
   «UcharMarket»); BotFather: `/setinline` placeholder «Район, комнаты, цена»
   (упоминается в `bot/main.py:200-204`), список команд, отдельный тестовый бот
   и его env; что НЕ настраивается в BotFather.
2. **Чек-лист e2e перед запуском** (в тот же док или рядом): прогон «Критериев
   готовности» из SOURCE_SPEC_V2 по D1–D5 на iOS/Android/Desktop.
3. **Инструкция ручного spike 48h:** на тестовом канале опубликовать пост ботом,
   через 49ч попробовать `editMessageMedia` — подтвердить/опровергнуть лимит, на
   котором стоит модал FU2/D4 (формулировки Bot API тоньше, чем «нельзя после
   48ч»). По результату — оставить или упростить модал.
4. SQL-примеры телеметрии (из FU5) и примеры маркетинговых ссылок (из FU6).
5. Актуализация `spec-kit/UNFINISHED_TASKS.md` (если не сделана раньше).

---

## Топ-риски и подводные камни (сводно)

1. **Гейт в `decide_transition` = тихий no-op** — функция без вызовов; гейтить
   диспатчер/`_enqueue_autopost`/таск (FU2 п.4) и тестировать диспатчер (FU4).
2. **Пропуск конвертеров `crawler_service`** при проставлении
   `publish_to_channel=False` → заклеймленный контент уезжает в канал после F1.
3. **Забытый exclude version-bump** (`listings.py:3922`) → ложные stale-бейджи
   у живых постов.
4. **Ослабление валидации резолвера** (`deep_links.py:51`) — только по строгому
   регэкспу слага, до любых обращений к БД; `record_event` уже обрезает payload
   до 64.
5. **Deploy skew:** новые поля ответов (`autopost_*` в списке объявлений) на
   фронте строго optional.
6. **Inline-хэндлеры без DB-сессии** (`bot/main.py:97-98`) — лимитер FU3 только
   Redis, телеметрия FU5 только через Celery-таск.
7. **Кэш Telegram при rate-limit:** пустой inline-ответ отдавать с
   `cache_time=5`, иначе пустота закэшируется на 60с.
8. **Backfill миграции FU2:** сверить регистр значений enum `SourceType` в БД
   по существующей миграции до написания UPDATE.

## Решения по умолчанию (можно переопределить до старта соответствующего PR)

| Параметр | Значение | Обоснование |
|---|---|---|
| Окно дайджеста FU7 | 600 с | всплески краулера растянуты; 10 мин задержки приемлемы для алертов |
| Лимит бот-поиска FU3 | 10/мин/пользователь | человек столько руками не печатает |
| Лимит inline FU3 | 30/мин/пользователь | inline шлёт запрос на каждое изменение текста |
| Retention телеметрии FU5 | 90 дней | достаточно для итерации словаря |
| Грамматика слага FU6 | `<district>[_<N>rooms][_buy\|_rent]` | покрывает рекламные сценарии E4; расширяемо |

---

## Кратко (простыми словами)

Это дорожная карта доделок Telegram-блока: 8 пулл-реквестов на ~8–9 дней.
Сначала быстрые фиксы (час работы — например, баг, из-за которого inline-поиск
может показать выдачу на чужом языке), затем самое ценное для риелторов —
чекбокс «публиковать в моём канале» и значок «пост устарел» прямо в «Моих
объявлениях», дальше защита от спама, автотесты, телеметрия качества поиска,
человекочитаемые рекламные ссылки (заодно чинится баг — ссылки с фильтрами
сейчас вообще не применяют фильтры), дайджест уведомлений («5 новых объявлений»
одним сообщением вместо пяти) и финальная документация с чек-листом перед
запуском. По каждому шагу расписано: какие файлы, что именно менять, как
проверить и где грабли. Вверху — таблица статусов: новая сессия берёт первый
незакрытый пункт и двигает план дальше.
