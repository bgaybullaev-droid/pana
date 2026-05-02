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
from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ContentType, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.analytics import check_rate_limit, track_event
from app.bot.i18n import DEFAULT_LANGUAGE, get_language, t
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
        return get_language(telegram_lang)
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
# /start — Language selection for new users, status for returning
# =============================================================================


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()

    telegram_lang = message.from_user.language_code
    telegram_id = message.from_user.id

    # Handle deep link: /start link_PHONE — links telegram_id to phone-only user
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("link_"):
        phone_suffix = args[1].replace("link_", "")
        phone = f"+998{phone_suffix}"
        lang = get_language(telegram_lang)

        # Find user by phone (created by OTP auth)
        phone_user_q = await session.execute(
            select(User).where(
                User.phone == phone,
                User.deleted_at.is_(None),
            )
        )
        phone_user = phone_user_q.scalar_one_or_none()

        if phone_user:
            if phone_user.telegram_id == telegram_id:
                await message.answer(
                    "✅ Telegram уже привязан. Вернитесь в приложение."
                )
            else:
                # Remove telegram_id from any other user that has it
                old_user = await _find_user_by_telegram_id(session, telegram_id)
                if old_user and old_user.id != phone_user.id:
                    old_user.telegram_id = None

                phone_user.telegram_id = telegram_id
                await session.commit()
                await message.answer(
                    f"✅ Telegram привязан к номеру {phone}. Вернитесь в приложение и попробуйте снова."
                )
        else:
            await message.answer(
                "❌ Пользователь не найден. Сначала введите номер телефона в приложении."
            )
        return

    user = await _find_user_by_telegram_id(session, telegram_id)

    # Returning user — use saved language
    if user:
        lang = (
            get_language(user.language)
            if user.language
            else get_language(telegram_lang)
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

    # New user — show language selection first
    await message.answer(
        t(DEFAULT_LANGUAGE, "choose_language"),
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
    new_lang = callback.data.split("_")[1]
    await _set_lang(state, new_lang)

    user = await _find_user_by_telegram_id(session, callback.from_user.id)
    if user:
        user.language = get_language(new_lang)
        await session.commit()

    # After language selection — show welcome with register button
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
