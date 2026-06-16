"""Seller registration bot handlers with i18n support.

Supports Russian (ru) and Uzbek (uz) languages.
Features: language selection, progress indicator, back navigation,
edit from summary, invalid input handling, cancel button, rate limiting,
URL validation, email collection, logo upload, analytics, profile view/edit,
auto-approve mode, admin notifications.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    ContentType,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import deeplink

from app.bot.analytics import check_rate_limit, track_event
from app.bot.i18n import (
    DEFAULT_LANGUAGE,
    get_language,
    language_from_telegram_code,
    t,
)
from app.bot.keyboards import (
    get_back_kb,
    get_cancel_kb,
    get_confirm_kb,
    get_edit_fields_kb,
    get_language_kb,
    get_phone_kb,
    get_profile_edit_kb,
    get_profile_kb,
    get_rejected_kb,
    get_skip_kb,
    get_start_kb,
    remove_kb,
)
from app.bot.notifications import get_bot_instance, notify_admins_new_registration
from app.bot.states import STEP_NUMBERS, TOTAL_STEPS, ProfileEdit, SellerRegistration
from app.core.config import settings
from app.db.models import Seller, User, UserApprovalStatus, UserRole

logger = logging.getLogger(__name__)

router = Router()

PHONE_RE = re.compile(r"^\+998\d{9}$")
INSTAGRAM_RE = re.compile(r"^(https?://)?(www\.)?instagram\.com/[a-zA-Z0-9_.]+/?$")
URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Upload directory for logos
LOGO_DIR = Path(settings.upload_dir) / "logos"


# =============================================================================
# Helpers
# =============================================================================


async def _find_user_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def _link_telegram_to_phone_user(
    session: AsyncSession, phone: str, telegram_id: int
) -> bool:
    """If a user was created from the UI with this phone but no telegram_id,
    link the telegram_id to them. Returns True if linked."""
    result = await session.execute(
        select(User).where(
            User.phone == phone,
            User.telegram_id.is_(None),
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if user:
        user.telegram_id = telegram_id
        await session.commit()
        return True
    return False


async def _get_lang(state: FSMContext) -> str:
    data = await state.get_data()
    return get_language(data.get("lang"))


async def _get_user_language(
    state: FSMContext, user: User | None = None, telegram_lang: str | None = None
) -> str:
    data = await state.get_data()
    if lang := data.get("lang"):
        return get_language(lang)
    if user and user.language:
        return get_language(user.language)
    if telegram_lang:
        return language_from_telegram_code(telegram_lang)
    return DEFAULT_LANGUAGE


async def _set_lang(state: FSMContext, lang: str) -> None:
    await state.update_data(lang=get_language(lang))


def _step(lang: str, step_name: str) -> str:
    """Get step indicator prefix."""
    num = STEP_NUMBERS.get(step_name, 1)
    return t(lang, "step_indicator", current=num, total=TOTAL_STEPS)


def _normalize_phone(phone: str) -> str:
    """Normalize phone number - strip spaces, dashes, parentheses."""
    phone = re.sub(r"[\s\-\(\)]+", "", phone)
    if re.match(r"^\d{9}$", phone):
        phone = f"+998{phone}"
    elif re.match(r"^998\d{9}$", phone):
        phone = f"+{phone}"
    return phone


def _is_valid_instagram(url: str) -> bool:
    """Validate Instagram URL or @username."""
    if url.startswith("@") and len(url) > 1:
        return True
    return bool(INSTAGRAM_RE.match(url))


def _is_valid_url(url: str) -> bool:
    """Validate website URL."""
    return bool(URL_RE.match(url))


def _format_summary(data: dict, lang: str) -> str:
    lines = [
        t(lang, "summary_title"),
        f"👤 {t(lang, 'summary_name', name=data['first_name'])}",
    ]
    if data.get("last_name"):
        lines.append(t(lang, "summary_lastname", lastname=data["last_name"]))
    lines.append(f"📱 {t(lang, 'summary_phone', phone=data['phone'])}")
    if data.get("company_name"):
        lines.append(f"🏢 {t(lang, 'summary_company', company=data['company_name'])}")
    if data.get("description"):
        lines.append(
            f"📝 {t(lang, 'summary_description', description=data['description'])}"
        )
    if data.get("telegram_username"):
        lines.append(
            f"💬 {t(lang, 'summary_telegram', username=data['telegram_username'])}"
        )
    if data.get("instagram_url"):
        lines.append(f"📸 {t(lang, 'summary_instagram', url=data['instagram_url'])}")
    if data.get("website_url"):
        lines.append(f"🌐 {t(lang, 'summary_website', url=data['website_url'])}")
    if data.get("email"):
        lines.append(f"📧 {t(lang, 'summary_email', email=data['email'])}")
    if data.get("logo_url"):
        lines.append(f"🖼 {t(lang, 'summary_logo')}")
    lines.append(t(lang, "summary_confirm_question"))
    return "\n".join(lines)


async def _show_summary(target, state: FSMContext) -> None:
    """Show summary and set confirm state. Works with Message or CallbackQuery."""
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    msg = target if isinstance(target, Message) else target.message
    await msg.answer(
        _format_summary(data, lang),
        reply_markup=get_confirm_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.confirm)


def _format_profile(user: User, seller: Seller, lang: str) -> str:
    """Format seller profile for /profile command."""
    status_map = {
        UserApprovalStatus.APPROVED: t(lang, "profile_status_approved"),
        UserApprovalStatus.PENDING: t(lang, "profile_status_pending"),
        UserApprovalStatus.REJECTED: t(lang, "profile_status_rejected"),
    }
    lines = [
        t(lang, "profile_title"),
        f"👤 {t(lang, 'profile_name', name=user.first_name)}",
    ]
    if user.last_name:
        lines.append(f"   {t(lang, 'profile_lastname', lastname=user.last_name)}")
    lines.append(f"📱 {t(lang, 'profile_phone', phone=user.phone or seller.phone)}")
    if seller.company_name:
        lines.append(f"🏢 {t(lang, 'profile_company', company=seller.company_name)}")
    if seller.description:
        lines.append(
            f"📝 {t(lang, 'profile_description', description=seller.description)}"
        )
    if seller.telegram_username:
        lines.append(
            f"💬 {t(lang, 'profile_telegram', username=seller.telegram_username)}"
        )
    if seller.instagram_url:
        lines.append(f"📸 {t(lang, 'profile_instagram', url=seller.instagram_url)}")
    if seller.website_url:
        lines.append(f"🌐 {t(lang, 'profile_website', url=seller.website_url)}")
    if seller.email:
        lines.append(f"📧 {t(lang, 'profile_email', email=seller.email)}")
    lines.append(
        f"\n{t(lang, 'profile_status', status=status_map.get(user.approval_status, '—'))}"
    )
    return "\n".join(lines)


# =============================================================================
# /start — registry-based deep-link dispatcher
# =============================================================================
#
# Block D V2.0 (D3). The bot accepts ``/start <prefix>_<body>`` for seven
# prefixes. Each prefix has a handler that returns True if it fully
# handled the message; False means the dispatcher falls through to the
# normal "no payload" flow (language picker / status).
#
# The dispatcher always writes one row to ``deep_link_events`` before
# delegation so analytics see every attempted entry, valid or not.


async def _start_payload_link(
    *,
    body: str,
    message: Message,
    session: AsyncSession,
    lang: str,
    user: User | None,
    telegram_id: int,
) -> tuple[bool, str]:
    """``/start link_<phone_suffix>`` — preserved verbatim from pre-D3a.

    Returns (handled, outcome). ``user`` arg is unused; this is a phone
    flow, not telegram_id-based.
    """
    del user  # unused — this is a phone flow, not telegram_id-based
    phone = f"+998{body}"
    phone_user_q = await session.execute(
        select(User).where(User.phone == phone, User.deleted_at.is_(None))
    )
    phone_user = phone_user_q.scalar_one_or_none()

    if phone_user:
        if phone_user.telegram_id == telegram_id:
            await message.answer(t(lang, "link_already_linked"))
            return True, deeplink.OUTCOME_RESOLVED
        old_user = await _find_user_by_telegram_id(session, telegram_id)
        if old_user and old_user.id != phone_user.id:
            old_user.telegram_id = None
        phone_user.telegram_id = telegram_id
        await session.commit()
        await message.answer(t(lang, "link_success", phone=phone))
        return True, deeplink.OUTCOME_RESOLVED

    await message.answer(t(lang, "link_user_not_found"))
    return True, deeplink.OUTCOME_REJECTED_UNKNOWN


def _twa_open_kb(payload: str, lang: str) -> InlineKeyboardMarkup:
    """Inline keyboard that re-opens the chat via ``?startapp=<payload>``.

    Telegram routes the click back to itself which then opens the Mini
    App with ``initDataUnsafe.start_param`` populated — the existing
    frontend ``StartParamHandler`` (Router.tsx) consumes it.
    """
    username = settings.telegram_bot_username or "UcharMarketBot"
    url = f"https://t.me/{username}?startapp={payload}"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_open_app"), url=url)]]
    )


async def _start_payload_listing(
    *,
    body: str,
    message: Message,
    session: AsyncSession,
    lang: str,
    user: User | None,
    telegram_id: int,
) -> tuple[bool, str]:
    """``/start listing_<uuid>`` (or ``obj_<uuid>`` alias) — hand off to TWA."""
    del session, user, telegram_id
    # Emit on the canonical ``listing_`` form so deep-link share targets
    # keep matching what notifications.py already emits.
    await message.answer(
        t(lang, "deep_link_open_listing"),
        reply_markup=_twa_open_kb(f"listing_{body}", lang),
    )
    return True, deeplink.OUTCOME_RESOLVED


async def _start_payload_filter(
    *,
    body: str,
    message: Message,
    session: AsyncSession,
    lang: str,
    user: User | None,
    telegram_id: int,
) -> tuple[bool, str]:
    """``/start filter_<short_id>`` — verify the payload exists, hand off to TWA.

    Falls back to decoding a human marketing slug (FU6) such as
    ``filter_chilonzor_2rooms_rent`` when no stored short-id matches. In
    that case we hand off on the same ``filter_<body>`` payload — the
    frontend re-decodes it through ``GET /deep-links/{body}``.
    """
    del user, telegram_id
    payload = await deeplink.resolve_filter_payload(body, session)
    if payload is not None:
        await session.commit()
        outcome = deeplink.OUTCOME_RESOLVED
    elif deeplink.parse_filter_slug(body) is not None:
        outcome = deeplink.OUTCOME_RESOLVED_SLUG
    else:
        return False, deeplink.OUTCOME_REJECTED_UNKNOWN
    await message.answer(
        t(lang, "deep_link_open_filter"),
        reply_markup=_twa_open_kb(f"filter_{body}", lang),
    )
    return True, outcome


async def _start_payload_claim(
    *,
    body: str,
    message: Message,
    session: AsyncSession,
    lang: str,
    user: User | None,
    telegram_id: int,
    kind: str = "claim",
) -> tuple[bool, str]:
    """``/start claim_<id>`` and ``/start agent_<id>`` — single-use B2B tickets."""
    del user
    invite, outcome = await deeplink.consume_claim_invite(
        body, telegram_id, session, expected_kind=kind
    )
    if invite is None:
        # Soft failure: log and fall through to normal welcome flow.
        return False, outcome
    await session.commit()
    # Minimal acknowledgement; the actual "redirect to Found" UX lands
    # with E5 (manual B2B onboarding). For PR-D3a we record consumption
    # and let the user reach Found via the Menu Button.
    await message.answer(
        t(lang, "deep_link_claim_accepted"),
        reply_markup=_twa_open_kb("found", lang),
    )
    return True, deeplink.OUTCOME_RESOLVED


async def _start_payload_agent(**kwargs) -> tuple[bool, str]:
    return await _start_payload_claim(kind="agent", **kwargs)


async def _start_payload_ref(
    *,
    body: str,
    message: Message,
    session: AsyncSession,
    lang: str,
    user: User | None,
    telegram_id: int,
) -> tuple[bool, str]:
    """``/start ref_<id>`` — attribute referral on first registration only.

    Returns (False, outcome) so the dispatcher continues into the normal
    welcome flow; the attribution itself is a side-effect applied when
    the User row is later created by an /auth/* endpoint.

    Implementation: stash ``(telegram_id → referrer_user_id)`` in Redis
    with a 7-day TTL. The auth endpoints check this on new-user
    creation via ``deeplink.consume_pending_referral`` and write
    ``User.referred_by_user_id`` if present.
    """
    del message
    payload = await deeplink.resolve_referral_payload(body, session)
    if payload is None:
        return False, deeplink.OUTCOME_REJECTED_UNKNOWN
    if user is not None:
        # Existing user — D3-Q3: silently ignore retroactive attribution.
        logger.info(
            "deeplink.ref.ignored existing_user=%s payload_id=%s",
            user.id,
            body,
        )
        return False, deeplink.OUTCOME_REJECTED_MISMATCH

    referrer_id = payload.get("referrer_user_id")
    if not referrer_id:
        return False, deeplink.OUTCOME_REJECTED_UNKNOWN

    # Stash for the eventual /auth/* user-create path to consume.
    # Fail-soft on Redis outage — referral attribution is observational.
    await deeplink.stash_pending_referral(
        telegram_id=telegram_id,
        referrer_user_id=referrer_id,
        source=payload.get("source"),
    )
    await deeplink.record_event(
        "ref",
        f"ref_{body}",
        session,
        user_id=None,
        is_new_user=True,
        outcome=deeplink.OUTCOME_RESOLVED,
    )
    logger.info(
        "deeplink.ref.pending payload=%s referrer=%s tg=%s",
        body,
        referrer_id,
        telegram_id,
    )
    # Fall through to normal welcome.
    return False, deeplink.OUTCOME_RESOLVED


async def _start_payload_inv(
    *,
    body: str,
    message: Message,
    session: AsyncSession,
    lang: str,
    user: User | None,
    telegram_id: int,
) -> tuple[bool, str]:
    """``/start inv_*`` — Phase-2 invoice stub."""
    del body, session, user, telegram_id
    await message.answer(t(lang, "deep_link_inv_soon"))
    return True, deeplink.OUTCOME_RESOLVED


# Registry. Both ``listing`` and ``obj`` map to the same handler
# (D3-Q1 — accept both forms inbound; emit ``listing_`` outbound).
_START_PAYLOAD_HANDLERS: dict[str, callable] = {
    "link": _start_payload_link,
    "listing": _start_payload_listing,
    "obj": _start_payload_listing,
    "filter": _start_payload_filter,
    "claim": _start_payload_claim,
    "agent": _start_payload_agent,
    "ref": _start_payload_ref,
    "inv": _start_payload_inv,
}


def _parse_start_payload(text: str | None) -> tuple[str, str, str] | None:
    """Split ``/start <prefix>_<body>`` into ``(payload, prefix, body)``.

    Returns ``None`` for plain ``/start`` (no payload). The prefix is
    extracted up to the first underscore; body is everything after.
    """
    if not text:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) <= 1 or not parts[1]:
        return None
    payload = parts[1].strip()
    if "_" not in payload:
        return None
    prefix, body = payload.split("_", 1)
    if not body:
        return None
    return payload, prefix, body


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()

    telegram_lang = message.from_user.language_code
    telegram_id = message.from_user.id

    user = await _find_user_by_telegram_id(session, telegram_id)

    # Resolve language up front so every downstream message respects
    # the user's preference (or the best fallback we have).
    lang = (
        get_language(user.language)
        if (user and user.language)
        else language_from_telegram_code(telegram_lang)
    )

    parsed = _parse_start_payload(message.text)
    if parsed is not None:
        payload_str, prefix, body = parsed
        handler = _START_PAYLOAD_HANDLERS.get(prefix)
        if handler is None:
            await deeplink.record_event(
                prefix,
                payload_str,
                session,
                user_id=(user.id if user else None),
                is_new_user=user is None,
                outcome=deeplink.OUTCOME_REJECTED_UNKNOWN,
            )
            await session.commit()
            # Unknown prefix → fall through to the standard welcome flow
            # (quiet degradation per D3 spec).
        else:
            handled, outcome = await handler(
                body=body,
                message=message,
                session=session,
                lang=lang,
                user=user,
                telegram_id=telegram_id,
            )
            await deeplink.record_event(
                prefix,
                payload_str,
                session,
                user_id=(user.id if user else None),
                is_new_user=user is None,
                outcome=outcome,
            )
            await session.commit()
            if handled:
                return
            # Handler asked us to continue with normal flow (e.g. ref_
            # when no user exists yet — the welcome still applies).

    # Returning user — use saved language
    if user:
        lang = (
            get_language(user.language)
            if user.language
            else language_from_telegram_code(telegram_lang)
        )
        await _set_lang(state, lang)

        seller_q = select(Seller).where(Seller.user_id == user.id)
        seller = (await session.execute(seller_q)).scalar_one_or_none()

        if seller:
            if user.approval_status == UserApprovalStatus.PENDING:
                await message.answer(f"⏳ {t(lang, 'status_pending')}")
                return
            elif user.approval_status == UserApprovalStatus.APPROVED:
                await message.answer(f"✅ {t(lang, 'status_approved')}")
                return
            elif user.approval_status == UserApprovalStatus.REJECTED:
                reason = user.approval_notes
                if reason:
                    text = t(lang, "status_rejected_reason", reason=reason)
                else:
                    text = t(lang, "status_rejected")
                await message.answer(f"❌ {text}", reply_markup=get_rejected_kb(lang))
                return

        # User exists but no seller — show welcome
        await message.answer(
            f"👋 {t(lang, 'welcome')}",
            reply_markup=get_start_kb(lang),
            parse_mode="HTML",
        )
        return

    # New user — show trilingual welcome with the 3-language picker.
    # Per Block D D1 spec: same content visible to every new user in
    # all three locales so the choice is informed.
    await message.answer(
        t(DEFAULT_LANGUAGE, "welcome_trilingual"),
        reply_markup=get_language_kb(),
    )


# =============================================================================
# Language selection
# =============================================================================


@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext):
    lang = await _get_lang(state)
    await message.answer(t(lang, "language_select"), reply_markup=get_language_kb())


@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.answer()
    # split("_", 1) so multi-segment codes like "uz_cyrl" survive intact.
    new_lang = callback.data.split("_", 1)[1]
    await _set_lang(state, new_lang)

    user = await _find_user_by_telegram_id(session, callback.from_user.id)
    if user:
        user.language = get_language(new_lang)
        await session.commit()

        # Already-registered sellers should see their current status after
        # changing language, not the new-user "welcome + register" flow.
        seller_q = select(Seller).where(Seller.user_id == user.id)
        seller = (await session.execute(seller_q)).scalar_one_or_none()
        if seller:
            if user.approval_status == UserApprovalStatus.PENDING:
                await callback.message.answer(f"⏳ {t(new_lang, 'status_pending')}")
                return
            if user.approval_status == UserApprovalStatus.APPROVED:
                await callback.message.answer(f"✅ {t(new_lang, 'status_approved')}")
                return
            if user.approval_status == UserApprovalStatus.REJECTED:
                reason = user.approval_notes
                if reason:
                    text = t(new_lang, "status_rejected_reason", reason=reason)
                else:
                    text = t(new_lang, "status_rejected")
                await callback.message.answer(
                    f"❌ {text}", reply_markup=get_rejected_kb(new_lang)
                )
                return

    # New user or existing user without a seller record — show welcome
    # with register button.
    await callback.message.answer(
        f"👋 {t(new_lang, 'welcome')}",
        reply_markup=get_start_kb(new_lang),
        parse_mode="HTML",
    )


# =============================================================================
# Re-apply after rejection
# =============================================================================


@router.callback_query(F.data == "reapply")
async def reapply_registration(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.answer()
    lang = await _get_lang(state)

    # Delete old seller record so they can re-register
    user = await _find_user_by_telegram_id(session, callback.from_user.id)
    if user:
        seller_q = select(Seller).where(Seller.user_id == user.id)
        seller = (await session.execute(seller_q)).scalar_one_or_none()
        if seller:
            await session.delete(seller)
        user.approval_status = None
        user.role = UserRole.USER
        await session.commit()

    await callback.message.answer(
        _step(lang, "first_name") + t(lang, "enter_first_name"),
        reply_markup=get_cancel_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.first_name)


# =============================================================================
# /help, /cancel, /profile commands
# =============================================================================


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    lang = await _get_user_language(
        state, telegram_lang=message.from_user.language_code
    )
    await message.answer(
        t(lang, "help_title") + t(lang, "help_text"),
        parse_mode="HTML",
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    lang = await _get_user_language(
        state, telegram_lang=message.from_user.language_code
    )
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(t(lang, "cancel_nothing"))
    else:
        await track_event("cancelled")
        await state.clear()
        await _set_lang(state, lang)
        await message.answer(t(lang, "cancel_message"), reply_markup=remove_kb)


@router.callback_query(F.data == "cancel")
async def process_cancel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    await track_event("cancelled")
    await state.clear()
    await _set_lang(state, lang)
    await callback.message.answer(t(lang, "cancel_message"), reply_markup=remove_kb)


# --- /profile — View seller profile ---
@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext, session: AsyncSession):
    lang = await _get_user_language(
        state, telegram_lang=message.from_user.language_code
    )
    await _set_lang(state, lang)

    user = await _find_user_by_telegram_id(session, message.from_user.id)
    if not user or user.role not in (UserRole.SELLER, UserRole.ADMIN):
        await message.answer(t(lang, "profile_not_available"))
        return

    seller = (
        await session.execute(select(Seller).where(Seller.user_id == user.id))
    ).scalar_one_or_none()

    if not seller:
        await message.answer(t(lang, "profile_not_found"))
        return

    text = _format_profile(user, seller, lang)
    await message.answer(text, reply_markup=get_profile_kb(lang), parse_mode="HTML")


# =============================================================================
# Profile edit flow
# =============================================================================


@router.callback_query(F.data == "profile_edit")
async def profile_edit_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.answer()
    lang = await _get_lang(state)

    user = await _find_user_by_telegram_id(session, callback.from_user.id)
    if not user or user.approval_status != UserApprovalStatus.APPROVED:
        await callback.message.answer(t(lang, "profile_not_available"))
        return

    await callback.message.answer(
        t(lang, "edit_select_field"),
        reply_markup=get_profile_edit_kb(lang),
    )
    await state.set_state(ProfileEdit.select_field)


@router.callback_query(F.data == "profile_language")
async def profile_change_language(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        t(DEFAULT_LANGUAGE, "choose_language"),
        reply_markup=get_language_kb(),
    )


@router.callback_query(F.data == "profile_back")
async def profile_back(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.answer()
    lang = await _get_lang(state)
    await state.clear()
    await _set_lang(state, lang)

    user = await _find_user_by_telegram_id(session, callback.from_user.id)
    if user:
        seller = (
            await session.execute(select(Seller).where(Seller.user_id == user.id))
        ).scalar_one_or_none()
        if seller:
            text = _format_profile(user, seller, lang)
            await callback.message.answer(
                text, reply_markup=get_profile_kb(lang), parse_mode="HTML"
            )
            return

    await callback.message.answer(t(lang, "profile_not_found"))


@router.callback_query(ProfileEdit.select_field, F.data.startswith("pedit_"))
async def profile_edit_field(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)

    field = callback.data.replace("pedit_", "")
    await state.update_data(_profile_field=field)

    prompt_map = {
        "company_name": "enter_company",
        "description": "enter_description",
        "telegram_username": "enter_telegram",
        "instagram_url": "enter_instagram",
        "website_url": "enter_website",
        "email": "enter_email",
    }

    prompt_key = prompt_map.get(field, "profile_edit_prompt")
    await callback.message.answer(
        t(lang, prompt_key),
        reply_markup=get_cancel_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(ProfileEdit.edit_value)


@router.message(ProfileEdit.edit_value)
async def profile_edit_value(
    message: Message, state: FSMContext, session: AsyncSession
):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    data = await state.get_data()
    field = data.get("_profile_field")
    value = message.text.strip()

    # Validate based on field
    if field == "email" and not EMAIL_RE.match(value):
        await message.answer(t(lang, "error_email_format"))
        return
    if field == "instagram_url" and not _is_valid_instagram(value):
        await message.answer(t(lang, "error_instagram_format"))
        return
    if field == "website_url" and not _is_valid_url(value):
        await message.answer(t(lang, "error_website_format"))
        return

    user = await _find_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer(t(lang, "profile_not_found"))
        return

    seller = (
        await session.execute(select(Seller).where(Seller.user_id == user.id))
    ).scalar_one_or_none()

    if not seller:
        await message.answer(t(lang, "profile_not_found"))
        return

    # Update the field
    if hasattr(seller, field):
        setattr(seller, field, value)
    await session.commit()

    await state.clear()
    await _set_lang(state, lang)

    await message.answer(t(lang, "profile_updated"))

    # Show updated profile
    await session.refresh(seller)
    await session.refresh(user)
    text = _format_profile(user, seller, lang)
    await message.answer(text, reply_markup=get_profile_kb(lang), parse_mode="HTML")


# =============================================================================
# Back navigation
# =============================================================================

# Map each state to its previous state: (step_name, prompt_key, is_optional)
_BACK_MAP = {
    SellerRegistration.last_name: ("first_name", "enter_first_name", False),
    SellerRegistration.phone: ("last_name", "enter_last_name", True),
    SellerRegistration.company_name: ("phone", "enter_phone", False),
    SellerRegistration.description: ("company_name", "enter_company", True),
    SellerRegistration.telegram_username: ("description", "enter_description", True),
    SellerRegistration.instagram_url: ("telegram_username", "enter_telegram", True),
    SellerRegistration.website_url: ("instagram_url", "enter_instagram", True),
    SellerRegistration.email: ("website_url", "enter_website", True),
    SellerRegistration.logo: ("email", "enter_email", True),
}


@router.callback_query(F.data == "back")
async def process_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    current = await state.get_state()

    # Find the current state in the back map
    for state_obj, (step_name, prompt_key, is_optional) in _BACK_MAP.items():
        if current == state_obj.state:
            if step_name == "phone":
                kb = get_phone_kb(lang)
            elif is_optional:
                kb = get_skip_kb(lang)
            elif step_name == "first_name":
                kb = get_cancel_kb(lang)
            else:
                kb = get_back_kb(lang)

            await callback.message.answer(
                _step(lang, step_name) + t(lang, prompt_key),
                reply_markup=kb,
                parse_mode="HTML",
            )
            prev_state = getattr(SellerRegistration, step_name)
            await state.set_state(prev_state)
            return

    # If we can't go back, just ignore
    await callback.message.answer(t(lang, "enter_first_name"), parse_mode="HTML")
    await state.set_state(SellerRegistration.first_name)


# =============================================================================
# Invalid input handler (photos, voice, stickers, etc.)
# NOTE: SellerRegistration.logo is EXCLUDED — photos are valid there
# =============================================================================

_NON_TEXT_TYPES = {
    ContentType.PHOTO,
    ContentType.VIDEO,
    ContentType.VOICE,
    ContentType.AUDIO,
    ContentType.DOCUMENT,
    ContentType.STICKER,
    ContentType.VIDEO_NOTE,
    ContentType.ANIMATION,
}

# Text-only states that should reject non-text input
_TEXT_ONLY_STATES = [
    SellerRegistration.first_name,
    SellerRegistration.last_name,
    SellerRegistration.company_name,
    SellerRegistration.description,
    SellerRegistration.telegram_username,
    SellerRegistration.instagram_url,
    SellerRegistration.website_url,
    SellerRegistration.email,
    SellerRegistration.edit_field,
]

for _st in _TEXT_ONLY_STATES:

    @router.message(_st, F.content_type.in_(_NON_TEXT_TYPES))
    async def invalid_input_handler(message: Message, state: FSMContext):
        lang = await _get_lang(state)
        await message.answer(t(lang, "error_invalid_input"))


# =============================================================================
# Registration flow
# =============================================================================


@router.callback_query(F.data == "register")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)

    # Rate limiting
    if await check_rate_limit(callback.from_user.id):
        await callback.message.answer(t(lang, "error_rate_limited"))
        return

    await track_event("started")

    await callback.message.answer(
        _step(lang, "first_name") + t(lang, "enter_first_name"),
        reply_markup=get_cancel_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.first_name)


# --- First name ---
@router.message(SellerRegistration.first_name)
async def process_first_name(message: Message, state: FSMContext):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    name = message.text.strip()
    if len(name) < 1 or len(name) > 100:
        await message.answer(t(lang, "error_name_length"))
        return

    await state.update_data(first_name=name)
    await track_event("step:first_name")

    # Check if editing from summary
    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "last_name") + t(lang, "enter_last_name"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.last_name)


# --- Last name ---
@router.message(SellerRegistration.last_name)
async def process_last_name(message: Message, state: FSMContext):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    name = message.text.strip()
    if len(name) > 100:
        await message.answer(t(lang, "error_lastname_length"))
        return

    await state.update_data(last_name=name)
    await track_event("step:last_name")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "phone") + f"📱 {t(lang, 'enter_phone')}",
        reply_markup=get_phone_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.phone)


@router.callback_query(SellerRegistration.last_name, F.data == "skip")
async def skip_last_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    await state.update_data(last_name=None)

    await callback.message.answer(
        _step(lang, "phone") + f"📱 {t(lang, 'enter_phone')}",
        reply_markup=get_phone_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.phone)


# --- Phone ---
@router.message(SellerRegistration.phone, F.contact)
async def process_phone_contact(
    message: Message, state: FSMContext, session: AsyncSession
):
    lang = await _get_lang(state)

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = f"+{phone}"

    if not PHONE_RE.match(phone):
        await message.answer(
            t(lang, "error_phone_format"), reply_markup=get_phone_kb(lang)
        )
        return

    # Link telegram_id to UI-created phone-only user if exists
    await _link_telegram_to_phone_user(session, phone, message.from_user.id)

    await state.update_data(phone=phone)
    await track_event("step:phone")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "company_name") + t(lang, "enter_company"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.company_name)


@router.message(SellerRegistration.phone)
async def process_phone_text(
    message: Message, state: FSMContext, session: AsyncSession
):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    phone = _normalize_phone(message.text.strip())

    if not PHONE_RE.match(phone):
        await message.answer(
            t(lang, "error_phone_format_detailed"),
            reply_markup=get_phone_kb(lang),
        )
        return

    # Link telegram_id to UI-created phone-only user if exists
    await _link_telegram_to_phone_user(session, phone, message.from_user.id)

    await state.update_data(phone=phone)
    await track_event("step:phone")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "company_name") + t(lang, "enter_company"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.company_name)


# --- Company name ---
@router.message(SellerRegistration.company_name)
async def process_company_name(message: Message, state: FSMContext):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    name = message.text.strip()
    if len(name) > 200:
        await message.answer(t(lang, "error_company_length"))
        return

    await state.update_data(company_name=name)
    await track_event("step:company_name")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "description") + t(lang, "enter_description"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.description)


@router.callback_query(SellerRegistration.company_name, F.data == "skip")
async def skip_company_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    await state.update_data(company_name=None)

    await callback.message.answer(
        _step(lang, "description") + t(lang, "enter_description"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.description)


# --- Description ---
@router.message(SellerRegistration.description)
async def process_description(message: Message, state: FSMContext):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    desc = message.text.strip()
    if len(desc) > 2000:
        await message.answer(t(lang, "error_description_length"))
        return

    await state.update_data(description=desc)
    await track_event("step:description")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    # Auto-detect telegram username
    tg_username = message.from_user.username
    if tg_username:
        await state.update_data(telegram_username=tg_username)
        await message.answer(
            _step(lang, "instagram_url")
            + t(lang, "telegram_detected", username=tg_username),
            reply_markup=get_skip_kb(lang),
            parse_mode="HTML",
        )
        await state.set_state(SellerRegistration.instagram_url)
    else:
        await message.answer(
            _step(lang, "telegram_username") + t(lang, "enter_telegram"),
            reply_markup=get_skip_kb(lang),
            parse_mode="HTML",
        )
        await state.set_state(SellerRegistration.telegram_username)


@router.callback_query(SellerRegistration.description, F.data == "skip")
async def skip_description(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    await state.update_data(description=None)

    tg_username = callback.from_user.username
    if tg_username:
        await state.update_data(telegram_username=tg_username)
        await callback.message.answer(
            _step(lang, "instagram_url")
            + t(lang, "telegram_detected", username=tg_username),
            reply_markup=get_skip_kb(lang),
            parse_mode="HTML",
        )
        await state.set_state(SellerRegistration.instagram_url)
    else:
        await callback.message.answer(
            _step(lang, "telegram_username") + t(lang, "enter_telegram"),
            reply_markup=get_skip_kb(lang),
            parse_mode="HTML",
        )
        await state.set_state(SellerRegistration.telegram_username)


# --- Telegram username ---
@router.message(SellerRegistration.telegram_username)
async def process_telegram_username(message: Message, state: FSMContext):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    username = message.text.strip().lstrip("@")
    if len(username) > 100:
        await message.answer(t(lang, "error_username_length"))
        return

    await state.update_data(telegram_username=username)
    await track_event("step:telegram_username")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "instagram_url") + t(lang, "enter_instagram"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.instagram_url)


@router.callback_query(SellerRegistration.telegram_username, F.data == "skip")
async def skip_telegram_username(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    await state.update_data(telegram_username=None)

    await callback.message.answer(
        _step(lang, "instagram_url") + t(lang, "enter_instagram"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.instagram_url)


# --- Instagram ---
@router.message(SellerRegistration.instagram_url)
async def process_instagram(message: Message, state: FSMContext):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    url = message.text.strip()
    if len(url) > 500:
        await message.answer(t(lang, "error_url_length"))
        return

    if not _is_valid_instagram(url):
        await message.answer(t(lang, "error_instagram_format"))
        return

    await state.update_data(instagram_url=url)
    await track_event("step:instagram_url")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "website_url") + t(lang, "enter_website"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.website_url)


@router.callback_query(SellerRegistration.instagram_url, F.data == "skip")
async def skip_instagram(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    await state.update_data(instagram_url=None)

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(callback, state)
        return

    await callback.message.answer(
        _step(lang, "website_url") + t(lang, "enter_website"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.website_url)


# --- Website ---
@router.message(SellerRegistration.website_url)
async def process_website(message: Message, state: FSMContext):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    url = message.text.strip()
    if len(url) > 500:
        await message.answer(t(lang, "error_url_length"))
        return

    if not _is_valid_url(url):
        await message.answer(t(lang, "error_website_format"))
        return

    await state.update_data(website_url=url)
    await track_event("step:website_url")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "email") + t(lang, "enter_email"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.email)


@router.callback_query(SellerRegistration.website_url, F.data == "skip")
async def skip_website(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    await state.update_data(website_url=None)

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(callback, state)
        return

    await callback.message.answer(
        _step(lang, "email") + t(lang, "enter_email"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.email)


# --- Email ---
@router.message(SellerRegistration.email)
async def process_email(message: Message, state: FSMContext):
    lang = await _get_lang(state)

    if not message.text or not message.text.strip():
        await message.answer(t(lang, "error_empty_input"))
        return

    email = message.text.strip()
    if not EMAIL_RE.match(email):
        await message.answer(t(lang, "error_email_format"))
        return

    await state.update_data(email=email)
    await track_event("step:email")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await message.answer(
        _step(lang, "logo") + t(lang, "enter_logo"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.logo)


@router.callback_query(SellerRegistration.email, F.data == "skip")
async def skip_email(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)
    await state.update_data(email=None)

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(callback, state)
        return

    await callback.message.answer(
        _step(lang, "logo") + t(lang, "enter_logo"),
        reply_markup=get_skip_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.logo)


# --- Logo upload ---
@router.message(SellerRegistration.logo, F.photo)
async def process_logo(message: Message, state: FSMContext):
    await _get_lang(state)

    # Get the largest photo version
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)

    # Ensure upload directory exists
    LOGO_DIR.mkdir(parents=True, exist_ok=True)

    # Download to local storage
    filename = f"{message.from_user.id}_{uuid4().hex[:8]}.jpg"
    file_path = LOGO_DIR / filename
    await message.bot.download_file(file.file_path, str(file_path))

    logo_url = f"/uploads/logos/{filename}"
    await state.update_data(logo_url=logo_url)
    await track_event("step:logo")

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)
        await _show_summary(message, state)
        return

    await _show_summary(message, state)


@router.callback_query(SellerRegistration.logo, F.data == "skip")
async def skip_logo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(logo_url=None)

    data = await state.get_data()
    if data.get("_editing"):
        await state.update_data(_editing=False)

    await _show_summary(callback, state)


# Reject non-photo content at logo step
@router.message(
    SellerRegistration.logo,
    F.content_type.in_(
        {
            ContentType.VIDEO,
            ContentType.VOICE,
            ContentType.AUDIO,
            ContentType.DOCUMENT,
            ContentType.STICKER,
            ContentType.VIDEO_NOTE,
            ContentType.ANIMATION,
        }
    ),
)
async def logo_invalid_input(message: Message, state: FSMContext):
    lang = await _get_lang(state)
    await message.answer(t(lang, "error_invalid_input"))


@router.message(SellerRegistration.logo)
async def logo_text_input(message: Message, state: FSMContext):
    """Handle text input at logo step — hint that a photo is needed."""
    lang = await _get_lang(state)
    await message.answer(
        t(lang, "enter_logo"), reply_markup=get_skip_kb(lang), parse_mode="HTML"
    )


# =============================================================================
# Edit from summary
# =============================================================================


@router.callback_query(SellerRegistration.confirm, F.data == "edit")
async def edit_from_summary(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)

    await callback.message.answer(
        t(lang, "edit_select_field"),
        reply_markup=get_edit_fields_kb(lang),
    )
    await state.set_state(SellerRegistration.edit_field)


@router.callback_query(SellerRegistration.edit_field, F.data == "back_to_summary")
async def back_to_summary(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(_editing=False)
    await _show_summary(callback, state)


@router.callback_query(SellerRegistration.edit_field, F.data.startswith("edit_"))
async def process_edit_field(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)

    field = callback.data.replace("edit_", "")
    await state.update_data(_editing=True)

    # Map field to its prompt and state
    field_map = {
        "first_name": (
            "enter_first_name",
            SellerRegistration.first_name,
            get_cancel_kb,
        ),
        "last_name": ("enter_last_name", SellerRegistration.last_name, get_skip_kb),
        "phone": ("enter_phone", SellerRegistration.phone, None),
        "company_name": ("enter_company", SellerRegistration.company_name, get_skip_kb),
        "description": (
            "enter_description",
            SellerRegistration.description,
            get_skip_kb,
        ),
        "telegram_username": (
            "enter_telegram",
            SellerRegistration.telegram_username,
            get_skip_kb,
        ),
        "instagram_url": (
            "enter_instagram",
            SellerRegistration.instagram_url,
            get_skip_kb,
        ),
        "website_url": ("enter_website", SellerRegistration.website_url, get_skip_kb),
        "email": ("enter_email", SellerRegistration.email, get_skip_kb),
        "logo": ("enter_logo", SellerRegistration.logo, get_skip_kb),
    }

    if field in field_map:
        prompt_key, target_state, kb_func = field_map[field]

        if field == "phone":
            await callback.message.answer(
                t(lang, prompt_key),
                reply_markup=get_phone_kb(lang),
                parse_mode="HTML",
            )
        else:
            kb = kb_func(lang) if kb_func else get_cancel_kb(lang)
            await callback.message.answer(
                t(lang, prompt_key),
                reply_markup=kb,
                parse_mode="HTML",
            )

        await state.set_state(target_state)


# =============================================================================
# Confirmation
# =============================================================================


@router.callback_query(SellerRegistration.confirm, F.data == "confirm")
async def confirm_registration(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    telegram_id = callback.from_user.id

    existing = await _find_user_by_telegram_id(session, telegram_id)
    if not existing:
        # Check if a user was pre-created from the UI with this phone (no telegram_id yet)
        phone_user_q = select(User).where(
            User.phone == data["phone"],
            User.deleted_at.is_(None),
        )
        phone_user = (await session.execute(phone_user_q)).scalar_one_or_none()
        if phone_user and not phone_user.telegram_id:
            # Link telegram_id to the UI-created user
            phone_user.telegram_id = telegram_id
            existing = phone_user

    if existing:
        seller_q = select(Seller).where(Seller.user_id == existing.id)
        if (await session.execute(seller_q)).scalar_one_or_none():
            await callback.message.answer(
                t(lang, "already_registered"),
                reply_markup=remove_kb,
            )
            await state.clear()
            return

    # Determine approval status
    if settings.auto_approve_users:
        approval_status = UserApprovalStatus.APPROVED
    else:
        approval_status = UserApprovalStatus.PENDING

    user = existing or User(
        id=uuid4(),
        telegram_id=telegram_id,
        first_name=data["first_name"],
        last_name=data.get("last_name"),
        username=callback.from_user.username,
        phone=data["phone"],
        language=lang,
        role=UserRole.SELLER,
        auth_source="bot",
        approval_status=approval_status,
        onboarding_completed=True,
    )

    if existing:
        # Check if phone is taken by another user
        new_phone = data["phone"]
        if new_phone and new_phone != existing.phone:
            phone_check = await session.execute(
                select(User).where(
                    User.phone == new_phone,
                    User.id != existing.id,
                    User.deleted_at.is_(None),
                )
            )
            if phone_check.scalar_one_or_none():
                await callback.message.answer(
                    f"❌ {t(lang, 'error_phone_duplicate')}",
                    reply_markup=remove_kb,
                )
                await state.clear()
                return

        user.first_name = data["first_name"]
        user.last_name = data.get("last_name")
        user.phone = new_phone
        user.language = lang
        user.role = UserRole.SELLER
        user.auth_source = "bot"
        user.approval_status = approval_status
        user.onboarding_completed = True
        if settings.auto_approve_users:
            user.approved_at = datetime.utcnow()
    else:
        # Check if phone is taken by any user
        phone_check = await session.execute(
            select(User).where(
                User.phone == data["phone"],
                User.deleted_at.is_(None),
            )
        )
        if phone_check.scalar_one_or_none():
            await callback.message.answer(
                f"❌ {t(lang, 'error_phone_duplicate')}",
                reply_markup=remove_kb,
            )
            await state.clear()
            return
        if settings.auto_approve_users:
            user.approved_at = datetime.utcnow()
        session.add(user)
        await session.flush()

    seller = Seller(
        user_id=user.id,
        phone=data["phone"],
        company_name=data.get("company_name"),
        description=data.get("description"),
        telegram_username=data.get("telegram_username"),
        instagram_url=data.get("instagram_url"),
        website_url=data.get("website_url"),
        email=data.get("email"),
        logo_url=data.get("logo_url"),
    )
    session.add(seller)
    await session.commit()

    await track_event("completed")

    logger.info(
        f"New seller registered: {data['first_name']} ({data['phone']}) "
        f"tg_id={telegram_id} lang={lang} auto_approved={settings.auto_approve_users}"
    )

    # Send appropriate success message
    if settings.auto_approve_users:
        await callback.message.answer(
            t(lang, "registration_auto_approved"),
            reply_markup=remove_kb,
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            t(lang, "registration_success"),
            reply_markup=remove_kb,
            parse_mode="HTML",
        )

    # Notify admins about new registration
    if settings.admin_chat_ids:
        bot = get_bot_instance()
        if bot:
            try:
                await notify_admins_new_registration(bot, data, settings.admin_chat_ids)
            except Exception as e:
                logger.warning(f"Failed to notify admins: {e}")

    await state.clear()


@router.callback_query(SellerRegistration.confirm, F.data == "restart")
async def restart_registration(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await _get_lang(state)

    await state.clear()
    await _set_lang(state, lang)

    await callback.message.answer(
        t(lang, "restart_registration")
        + "\n\n"
        + _step(lang, "first_name")
        + t(lang, "enter_first_name"),
        reply_markup=get_cancel_kb(lang),
        parse_mode="HTML",
    )
    await state.set_state(SellerRegistration.first_name)


# =============================================================================
# Mini App contact share — caches the phone for the Mini App auth endpoint
# =============================================================================
#
# When the Mini App calls Telegram.WebApp.requestContact() and the user taps
# "Share", Telegram delivers a Contact message to this bot. The message is
# standalone (no FSM state), so we match it with StateFilter(None) to avoid
# colliding with the seller-registration FSM handler at line ~772.
#
# We verify contact.user_id == message.from_user.id so a user can't attach
# someone else's phone to their own account by picking a contact from their
# address book. The phone lands in Redis at contact_share:{telegram_id} with
# a 120-second TTL, to be consumed by POST /auth/telegram on the Mini App's
# next request.


@router.message(StateFilter(None), F.contact)
async def receive_shared_contact(message: Message):
    from app.db.redis import get_redis

    contact = message.contact
    sender_id = message.from_user.id if message.from_user else None

    if sender_id is None or contact.user_id != sender_id:
        # Foreign contact or missing sender — silently ignore.
        logger.warning(
            "Ignored shared contact: sender=%s contact.user_id=%s",
            sender_id,
            contact.user_id,
        )
        return

    raw_phone = contact.phone_number or ""
    phone = raw_phone if raw_phone.startswith("+") else f"+{raw_phone}"
    phone = re.sub(r"[^\d+]", "", phone)

    if not re.match(r"^\+\d{8,15}$", phone):
        logger.warning("Ignored shared contact: invalid phone format %r", raw_phone)
        return

    redis = await get_redis()
    await redis.setex(f"contact_share:{sender_id}", 120, phone)
    logger.info("Cached Mini App shared contact for telegram_id=%s", sender_id)


# =============================================================================
# Block A V2.0 — A4: crawled-match inline callback handlers
# =============================================================================


@router.callback_query(F.data.startswith("claim_crawled:"))
async def handle_claim_crawled(call: CallbackQuery):
    """Telegram inline-button claim. Reuses the OLX/Telegram claim service.

    Flow:
    1. Parse listing_id from callback_data.
    2. Find the user by telegram_id; verify role is SELLER (or admin).
    3. Look up the source row(s) by phone match; call the convert service.
    4. Edit the bot message to a "Confirmed. Open in cabinet" footer.
    """

    from app.db.models import (
        OLXListing,
        Seller,
        TelegramListing,
    )
    from app.db.session import async_session_factory
    from app.services.crawler_service import (
        convert_olx_to_listing,
        convert_telegram_to_listing,
    )

    if call.data is None or call.from_user is None:
        return
    listing_id = call.data.split(":", 1)[1]
    telegram_id = call.from_user.id

    async with async_session_factory() as db:
        user = await _find_user_by_telegram_id(db, telegram_id)
        if not user or user.role not in (UserRole.SELLER, UserRole.ADMIN):
            try:
                await call.answer("Not authorised.", show_alert=True)
            except Exception:
                pass
            return

        seller_row = (
            await db.execute(select(Seller).where(Seller.user_id == user.id))
        ).scalar_one_or_none()
        if seller_row is None:
            await call.answer("Seller profile required.", show_alert=True)
            return

        # Resolve the crawled row. The notification's listing_id refers to
        # the canonical Listing row; A4 fanout was for unclaimed parser
        # rows that already had a Listing — try OLX first, then Telegram.
        from uuid import UUID

        try:
            lid = UUID(listing_id)
        except ValueError:
            await call.answer("Invalid id.", show_alert=True)
            return

        olx = (
            await db.execute(
                select(OLXListing).where(OLXListing.converted_listing_id == lid)
            )
        ).scalar_one_or_none()
        try:
            if olx is not None:
                if olx.converted_listing_id is None:
                    await convert_olx_to_listing(olx, seller_row, db)
            else:
                tg = (
                    await db.execute(
                        select(TelegramListing).where(
                            TelegramListing.converted_listing_id == lid
                        )
                    )
                ).scalar_one_or_none()
                if tg is None:
                    await call.answer("Listing not found.", show_alert=True)
                    return
                if tg.converted_listing_id is None:
                    await convert_telegram_to_listing(tg, seller_row, db)
            await db.commit()
        except Exception as exc:
            logger.warning("Bot claim_crawled failed: %s", exc)
            await db.rollback()
            await call.answer("Could not confirm.", show_alert=True)
            return

    # Edit the message to the confirmed footer. Bot-blocked is silently
    # swallowed — the DB state has been updated, the cabinet will reflect it.
    from aiogram.exceptions import TelegramForbiddenError as _TgForbidden

    try:
        if call.message is not None:
            await call.message.edit_text(
                text="✓ Подтверждено. Открыть в кабинете.",
            )
        await call.answer("Confirmed.")
    except _TgForbidden:
        pass
    except Exception:
        pass


@router.callback_query(F.data.startswith("reject_crawled:"))
async def handle_reject_crawled(call: CallbackQuery):
    """Telegram inline-button reject. Stamps rejected_by_seller_id."""
    from datetime import datetime

    from app.db.models import OLXListing, Seller, TelegramListing
    from app.db.session import async_session_factory

    if call.data is None or call.from_user is None:
        return
    listing_id = call.data.split(":", 1)[1]
    telegram_id = call.from_user.id

    async with async_session_factory() as db:
        user = await _find_user_by_telegram_id(db, telegram_id)
        if not user or user.role not in (UserRole.SELLER, UserRole.ADMIN):
            await call.answer("Not authorised.", show_alert=True)
            return

        seller_row = (
            await db.execute(select(Seller).where(Seller.user_id == user.id))
        ).scalar_one_or_none()
        if seller_row is None:
            await call.answer("Seller profile required.", show_alert=True)
            return

        from uuid import UUID

        try:
            lid = UUID(listing_id)
        except ValueError:
            await call.answer("Invalid id.", show_alert=True)
            return

        olx = (
            await db.execute(
                select(OLXListing).where(OLXListing.converted_listing_id == lid)
            )
        ).scalar_one_or_none()
        if olx is not None:
            olx.rejected_by_seller_id = seller_row.id
            olx.rejected_at = datetime.utcnow()
        else:
            tg = (
                await db.execute(
                    select(TelegramListing).where(
                        TelegramListing.converted_listing_id == lid
                    )
                )
            ).scalar_one_or_none()
            if tg is not None:
                tg.rejected_by_seller_id = seller_row.id
                tg.rejected_at = datetime.utcnow()
        await db.commit()

    # Bot-blocked while editing the message is swallowed — DB state already
    # reflects the reject.
    from aiogram.exceptions import TelegramForbiddenError as _TgForbidden

    try:
        if call.message is not None:
            await call.message.edit_text(text="✗ Отклонено")
        await call.answer("Rejected.")
    except _TgForbidden:
        pass
    except Exception:
        pass


# =============================================================================
# Block D V2.0 (D2) — favorite-toggle inline-button callbacks
# =============================================================================
#
# Handlers for the buyer-facing push keyboard built by
# ``services.listing_push.build_listing_action_kb_spec``. The callback
# data format is ``fav:<verb>:<listing_uuid>``; the verb encodes user
# intent at tap time but the final DB state is reconciled with what
# already exists (idempotent). "Написать продавцу" is a URL button
# so it has no callback; "Подробнее →" routes through the existing
# D3a deep-link plumbing.


def _kb_from_spec(spec: list) -> InlineKeyboardMarkup:
    """Convert keyboard-spec lists back into aiogram markup."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(**btn) for btn in row] for row in spec]
    )


async def _handle_fav_toggle(call: CallbackQuery, *, intent: str) -> None:
    """Shared body for ``fav:add`` and ``fav:remove`` callbacks.

    Idempotent: looks at current DB state, ensures it matches intent,
    flips the keyboard verb, records a behavioral signal. Failures in
    secondary side-effects (signal write, keyboard edit) never break
    the primary favorite write — per "graceful degradation" principle.
    """
    from app.db.database import async_session_maker
    from app.db.models import (
        Favorite,
        Listing,
        ListingStatus,
        Notification,
        NotificationType,
        Seller,
    )
    from app.services import behavioral_signals as signals
    from app.services.listing_push import build_listing_action_kb_spec

    if call.data is None or call.from_user is None or call.message is None:
        return

    parts = call.data.split(":", 2)
    if len(parts) != 3:
        await call.answer()
        return
    _ns, verb, listing_id_str = parts

    try:
        listing_id = UUID(listing_id_str)
    except ValueError:
        await call.answer()
        return

    telegram_id = call.from_user.id

    async with async_session_maker() as db:
        user = await _find_user_by_telegram_id(db, telegram_id)
        if user is None:
            # Push reached a Telegram account with no linked UcharMarket
            # user (account deleted, identity changed). Rare; no
            # behavioral signal recorded — no consumer for it.
            logger.info(
                "fav_toggle: no user for telegram_id=%s listing=%s",
                telegram_id,
                listing_id,
            )
            try:
                # No linked user → no stored language; derive from the
                # Telegram client locale so the toast still localizes.
                hint_lang = language_from_telegram_code(
                    getattr(call.from_user, "language_code", None)
                )
                await call.answer(
                    t(hint_lang, "fav_open_app_hint"),
                    show_alert=False,
                )
            except Exception:
                pass
            return

        lang = user.language or DEFAULT_LANGUAGE

        # Load listing + seller + current favorite state in parallel.
        listing_row = await db.execute(select(Listing).where(Listing.id == listing_id))
        listing = listing_row.scalar_one_or_none()
        if listing is None or listing.status not in (
            ListingStatus.ACTIVE,
            ListingStatus.GENERATION_FAILED,
        ):
            # Listing went away or is unavailable — soft fail. No
            # signal recorded; the recommender has no consumer for
            # stale-tap events.
            logger.info(
                "fav_toggle: stale listing user=%s listing=%s status=%s",
                user.id,
                listing_id,
                getattr(listing, "status", None),
            )
            # Append a localized "no longer available" note to the post
            # body (not just a transient toast) and drop the keyboard so
            # the card visibly reflects the dead state and can't be tapped
            # again. Captions cap at 1024, message text at 4096.
            note = t(lang, "push_listing_unavailable")
            try:
                if call.message.caption is not None:
                    new_caption = f"{call.message.caption}\n\n{note}"[:1024]
                    await call.message.edit_caption(
                        caption=new_caption, reply_markup=None
                    )
                else:
                    base = call.message.text or ""
                    new_text = f"{base}\n\n{note}".strip()[:4096]
                    await call.message.edit_text(new_text, reply_markup=None)
            except Exception:
                pass
            try:
                await call.answer(t(lang, "push_listing_unavailable"), show_alert=False)
            except Exception:
                pass
            return

        seller_row = await db.execute(
            select(Seller).where(Seller.id == listing.seller_id)
        )
        seller = seller_row.scalar_one_or_none() if listing.seller_id else None

        fav_row = await db.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.listing_id == listing_id,
            )
        )
        existing_fav = fav_row.scalar_one_or_none()

        # Reconcile intent vs current state. Intent wins; idempotent if
        # already in the requested state.
        if intent == "add" and existing_fav is None:
            db.add(Favorite(user_id=user.id, listing_id=listing_id))
            if isinstance(listing, Listing):
                listing.favorites_count += 1
                # Mirror the in-app side-effect: notify the listing
                # owner. Skip self-favoriting.
                if listing.seller_id and seller and seller.user_id != user.id:
                    seller_user_q = await db.execute(
                        select(User).where(User.id == seller.user_id)
                    )
                    seller_user = seller_user_q.scalar_one_or_none()
                    owner_lang = (
                        seller_user.language
                        if seller_user and seller_user.language in ("ru", "uz")
                        else "ru"
                    )
                    from app.workers.tasks.notifications import (
                        _FAVORITE_UPDATE_MESSAGE,
                        _FAVORITE_UPDATE_TITLE,
                    )

                    db.add(
                        Notification(
                            user_id=seller.user_id,
                            type=NotificationType.FAVORITE_UPDATE,
                            title=_FAVORITE_UPDATE_TITLE[owner_lang],
                            message=_FAVORITE_UPDATE_MESSAGE[owner_lang].format(
                                name=user.first_name
                            ),
                            listing_id=listing_id,
                            actor_id=user.id,
                        )
                    )
            is_favorited_after = True
            toast_key = "push_fav_added_toast"
            signal_event = signals.EVENT_FAV_ADD
        elif intent == "remove" and existing_fav is not None:
            await db.delete(existing_fav)
            if isinstance(listing, Listing) and listing.favorites_count > 0:
                listing.favorites_count -= 1
            is_favorited_after = False
            toast_key = "push_fav_removed_toast"
            signal_event = signals.EVENT_FAV_REMOVE
        else:
            # Intent already satisfied — flip the keyboard to match
            # actual state and emit no signal (idempotent no-op).
            is_favorited_after = existing_fav is not None
            toast_key = (
                "push_fav_added_toast"
                if is_favorited_after
                else "push_fav_removed_toast"
            )
            signal_event = None

        if signal_event is not None:
            await signals.record_event(
                db,
                event_type=signal_event,
                source=signals.SOURCE_PUSH_INLINE,
                user_id=user.id,
                listing_id=listing_id,
            )

        await db.commit()

    # ── Secondary side effects below run outside the session and never
    # block on each other. ─────────────────────────────────────────────
    try:
        spec = build_listing_action_kb_spec(
            listing, seller, lang, is_favorited=is_favorited_after
        )
        await call.message.edit_reply_markup(reply_markup=_kb_from_spec(spec))
    except Exception:
        # ``MessageNotModified`` and Telegram transients fall here.
        logger.debug("fav: edit_reply_markup failed", exc_info=True)

    try:
        await call.answer(t(lang, toast_key), show_alert=False)
    except Exception:
        pass


@router.callback_query(F.data.startswith("fav:add:"))
async def handle_fav_add(call: CallbackQuery) -> None:
    await _handle_fav_toggle(call, intent="add")


@router.callback_query(F.data.startswith("fav:remove:"))
async def handle_fav_remove(call: CallbackQuery) -> None:
    await _handle_fav_toggle(call, intent="remove")


# =============================================================================
# Block D V2.0 (D5) — /search command + free-text fallback
# =============================================================================
#
# Two entry points share the same execution path:
#   1) ``/search [query]`` — explicit command; empty body shows a prompt.
#   2) Free-text message — parsed; if the parser extracted any filter
#      we treat it as a search. Otherwise (e.g. "Привет, как дела?")
#      we stay silent so we don't interfere with normal chat. This
#      mirrors the spec's conservative heuristic and avoids
#      noise / mis-routed taps.


async def _run_bot_search_reply(
    message: Message, *, raw_query: str, lang: str, session: AsyncSession
) -> bool:
    """Execute a search and reply with up to 10 results + a deep-link CTA.

    Returns True if a reply was sent, False otherwise (caller decides
    whether to fall through to other handlers).
    """
    from app.bot import rate_limit as _rate_limit
    from app.services import bot_search as _search
    from app.services import deeplink as _deeplink
    from app.services import query_parser as _parser
    from app.workers.tasks import telemetry as _telemetry

    # D5 spam guard (FU3): cap bot search per user (admin-configurable). This is
    # the single choke point for both /search and free text. On the limit we
    # reply with the admin-editable message and return True so cmd_search does
    # not also append "search_not_understood".
    if message.from_user and not await _rate_limit.hit(
        "search", message.from_user.id
    ):
        await message.answer(await _rate_limit.limit_message(lang))
        return True

    parsed = _parser.parse(raw_query, lang=lang)

    if not raw_query or parsed.is_empty:
        # Nothing parseable. For /search this is a prompt; for free-text
        # we silently skip (caller returns False).
        return False

    results = await _search.search(parsed, limit=_search.DEFAULT_BOT_LIMIT, lang=lang)

    # FU5 telemetry: record the executed search (fire-and-forget). Placed
    # right after search() so both the empty- and non-empty-result paths
    # below are captured with the right results_count.
    _telemetry.enqueue_search_query(
        user_telegram_id=message.from_user.id if message.from_user else None,
        source="bot",
        raw_text=raw_query,
        extracted_fields=list(parsed.extracted_fields),
        results_count=len(results),
    )

    if not results:
        # Parsed something but the search returned nothing — give the
        # user a helpful next step rather than dead air.
        await message.answer(
            t(lang, "search_no_results"),
            reply_markup=_twa_open_kb("home", lang),
        )
        return True

    # Build a compact text listing. The headline (rooms + property type +
    # district) comes from the shared human title; area/price are appended.
    lines = [t(lang, "search_header", count=len(results))]
    for i, r in enumerate(results, start=1):
        bits: list[str] = [f"{i}. {r.title}" if r.title else f"{i}."]
        if r.area:
            bits.append(f"{int(r.area)} м²" if lang == "ru" else f"{int(r.area)} m²")
        if r.price:
            sym = "$" if r.currency == "USD" else ("сум" if lang == "ru" else "so'm")
            bits.append(f"— {r.price:,} {sym}")
        lines.append(" ".join(bits))

    # "Open all in app" button: materialise a filter link via D3a so
    # the TWA receives the same filter state the bot used.
    filter_payload = {
        "district": parsed.district,
        "rooms_min": parsed.rooms_min,
        "rooms_max": parsed.rooms_max,
        "price_min": parsed.price_min,
        "price_max": parsed.price_max,
        "price_currency": parsed.price_currency,
        "deal_type": parsed.deal_type,
        "property_type": parsed.property_type,
    }
    # Strip None values to keep the JSON tidy.
    filter_payload = {k: v for k, v in filter_payload.items() if v is not None}
    try:
        short_id, _ = await _deeplink.build_filter_link(filter_payload, session)
        await session.commit()
        open_payload = f"filter_{short_id}"
    except Exception:
        logger.warning("bot_search: filter link build failed", exc_info=True)
        open_payload = "home"

    await message.answer(
        "\n".join(lines),
        reply_markup=_twa_open_kb(open_payload, lang),
        disable_web_page_preview=True,
    )

    # Conversion-first hint per D5-Q2: no "Save search" button in
    # the bot; one-line nudge toward the in-app save flow.
    try:
        await message.answer(t(lang, "search_save_hint"))
    except Exception:
        pass

    return True


@router.message(Command("search"))
async def cmd_search(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """``/search`` command — explicit entry point."""
    # If user is in the middle of an FSM flow (e.g. seller registration),
    # let those handlers manage — we shouldn't interrupt mid-form.
    current_state = await state.get_state()
    if current_state is not None:
        return

    lang = await _get_lang(state)
    args = (message.text or "").split(maxsplit=1)
    raw_query = args[1].strip() if len(args) > 1 else ""

    if not raw_query:
        await message.answer(t(lang, "search_prompt"))
        return

    sent = await _run_bot_search_reply(
        message, raw_query=raw_query, lang=lang, session=session
    )
    if not sent:
        await message.answer(t(lang, "search_not_understood"))


@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def free_text_search(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Free-text fallback. Only fires when no FSM state is active.

    Conservative: if the parser extracts zero filters, we stay silent
    so casual chat ("Спасибо", "Привет") doesn't get hijacked. This
    is the second handler for the same message type; aiogram will
    dispatch by registration order, so any state-bound handler that
    matches will preempt this one.
    """
    user = await _find_user_by_telegram_id(session, message.from_user.id)
    lang = (
        get_language(user.language)
        if (user and user.language)
        else language_from_telegram_code(message.from_user.language_code)
    )
    await _run_bot_search_reply(
        message, raw_query=(message.text or ""), lang=lang, session=session
    )
