# Block D — Telegram-native mechanics (V2.0)

Five tasks that turn UcharMarket from "a TWA that happens to live in Telegram"
into "a Telegram-native product." Without these the app technically works but
loses the positioning advantage over Joymee, BirBir, OLX — competitors that
are either standalone apps or websites.

| ID | Task | Difficulty | Phase-1 value |
|----|------|------------|---------------|
| [D1](medium/D1-menu-button-language.md) | Menu Button + first-/start language picker | Easy-Medium | Highest ROI in block — UX win for every session |
| [D2](medium/D2-push-inline-keyboard.md) | Inline keyboard in push notifications | Medium | Low-friction action + personalization signal |
| [D3](hard/D3-deep-links.md) | Deep Links for marketing | Hard | Unlocks marketing funnel + B2B onboarding |
| [D4](hard/D4-bot-autoposting.md) | Bot autoposting with auto-update / auto-delete | Hard | **Anchor feature of Cabinet subscription** (99 000 sum/mo) |
| [D5](hard/D5-bot-search.md) | In-bot search (form + Inline Mode) with fuzzy | Hard | Main Telegram-native search path for habitual bot users |

---

## Cross-cutting principle: language consistency

Every outbound surface (push, channel post, bot reply, prefilled chat,
inline result) uses `User.language` exclusively. No mixed-language UIs, no
Russian fragments in an Uzbek interface, no Cyrillic-in-Latin bleed.

- **First `/start`**: bot shows 3-language welcome and **3 buttons**
  ("Русский", "O'zbekcha", "Ўзбекча"). Today only 2 are wired
  (see TRUTH_LAYER_AUDIT §1).
- **Fallback before explicit choice**: `from_user.language_code` from
  Telegram (`ru→ru`, `uz→uz-cyrl`, anything else→ru).
- **Change**: `/language` in bot, or TWA Settings → Language (D1 ships this).
- **History**: past push messages stay in their original language; future
  ones switch immediately.
- **Cross-user messages** (the prefilled "Написать продавцу" string in
  D2): always the **sender's** language. The recipient learns to read the
  language their leads send in; we don't translate between users.

---

## Reading order

0. [SOURCE_SPEC_V2.md](SOURCE_SPEC_V2.md) — дословный исходный текст
   функциональной спецификации V2.0 (продуктовый source of truth).
   Для текущих доделок см. [FOLLOWUP_PLAN.md](FOLLOWUP_PLAN.md) —
   план FU1–FU8 с живым чек-листом статусов.
1. [TRUTH_LAYER_AUDIT.md](TRUTH_LAYER_AUDIT.md) — what already exists vs
   what needs building. **Start here.**
2. [READINESS_REPORT.md](READINESS_REPORT.md) — risk register, open
   questions, blockers before implementation.
3. [EXECUTION_PLAN.md](EXECUTION_PLAN.md) — task ordering by real
   dependencies (PR-D1 ships first, PR-D5 last).
4. Individual specs in `easy/`, `medium/`, `hard/`.
5. `decision-pass/` — populated after the user runs the
   decision-resolution pass; converts OPEN QUESTIONS into DECIDED rules.

---

## Discipline lessons applied (from Block A/B/C)

- **No spec writing before audit.** Done above.
- **No implementation before decision-pass.** This kit ships with explicit
  OPEN QUESTIONS instead of silent assumptions.
- **No silent product assumptions.** Where the V2.0 spec text leaves room
  (e.g. `obj_` vs existing `listing_`, query-parser approach for D5, the
  `agent_<channel_id>` semantics), the spec calls it out instead of
  picking arbitrarily.
- **Existing code is ground truth.** Where infra exists it is reused
  verbatim (callback_query router, AI description columns, init_data
  verification, claims model). Where it doesn't, the spec says MISSING
  with the file the new code goes into.
