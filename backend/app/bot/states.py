"""FSM states for seller registration bot."""

from aiogram.fsm.state import State, StatesGroup


class SellerRegistration(StatesGroup):
    """States for the seller registration flow."""

    first_name = State()  # Step 1
    last_name = State()  # Step 2
    phone = State()  # Step 3
    company_name = State()  # Step 4
    description = State()  # Step 5
    telegram_username = State()  # Step 6
    instagram_url = State()  # Step 7
    website_url = State()  # Step 8
    email = State()  # Step 9
    logo = State()  # Step 10
    confirm = State()  # Summary & confirm
    edit_field = State()  # Editing a field from summary


class ProfileEdit(StatesGroup):
    """States for editing seller profile after approval."""

    select_field = State()
    edit_value = State()


# Step numbers for progress indicator
STEP_NUMBERS = {
    "first_name": 1,
    "last_name": 2,
    "phone": 3,
    "company_name": 4,
    "description": 5,
    "telegram_username": 6,
    "instagram_url": 7,
    "website_url": 8,
    "email": 9,
    "logo": 10,
}

TOTAL_STEPS = 10
