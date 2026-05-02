"""
Test configuration and fixtures.

Provides isolated database sessions, test client, and auth helpers.
All tests run in transactions that are rolled back after each test.
"""

import asyncio
import os
from typing import AsyncGenerator, Dict
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Set test environment BEFORE importing app modules
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-minimum-32-characters!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-pytest-min-32-chars!!")
os.environ.setdefault("POSTGRES_HOST", os.environ.get("POSTGRES_HOST", "localhost"))
os.environ.setdefault("POSTGRES_PORT", os.environ.get("POSTGRES_PORT", "5432"))
os.environ.setdefault("POSTGRES_USER", os.environ.get("POSTGRES_USER", "postgres"))
os.environ.setdefault(
    "POSTGRES_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "test_password")
)
os.environ.setdefault("POSTGRES_DB", os.environ.get("POSTGRES_DB", "ucharmarket_test"))
os.environ.setdefault("REDIS_HOST", os.environ.get("REDIS_HOST", "localhost"))
os.environ.setdefault("REDIS_PORT", os.environ.get("REDIS_PORT", "6379"))
os.environ.setdefault("REDIS_DB", "15")
os.environ.setdefault("MEILISEARCH_HOST", "http://localhost:7700")
os.environ.setdefault("MEILISEARCH_API_KEY", "test-meili-key")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/14")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/13")
os.environ.setdefault(
    "TELEGRAM_BOT_TOKEN", "0000000000:AAFakeTokenForTestingOnly000000000"
)
os.environ.setdefault("TELEGRAM_BOT_USERNAME", "test_bot")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("ADMIN_USERNAME", "test_admin")
os.environ.setdefault("ADMIN_PASSWORD", "test_admin_password")
os.environ.setdefault("AUTO_APPROVE_LISTINGS", "true")
os.environ.setdefault("AUTO_APPROVE_USERS", "true")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost"]')
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("SENTRY_DSN", "")

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, create_refresh_token
from app.db.database import Base, get_db
from app.db.models import (
    Currency,
    Listing,
    ListingImage,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
    Seller,
    SourceType,
    User,
    UserApprovalStatus,
    UserRole,
)
from app.main import app

# ---------------------------------------------------------------------------
# Settings override
# ---------------------------------------------------------------------------


def get_test_settings() -> Settings:
    """Create settings for test environment."""
    return Settings(
        _env_file=None,  # Don't read .env in tests
    )


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide test settings."""
    return get_test_settings()


# ---------------------------------------------------------------------------
# Database engine and session (session-scoped for performance)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_settings: Settings) -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine and tables."""
    engine = create_async_engine(
        test_settings.async_database_url,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create session factory."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db_session(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional database session with SAVEPOINT isolation.

    Uses the standard SQLAlchemy "join an external transaction" pattern so
    that application-level ``db.commit()`` calls inside API handlers only
    commit a SAVEPOINT, not the outer connection transaction. The outer
    transaction is rolled back at the end of each test, leaving the
    database clean for the next test even when endpoints commit.
    """
    async with test_engine.connect() as connection:
        outer_transaction = await connection.begin()
        await connection.begin_nested()

        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        async with session_factory() as session:

            @event.listens_for(session.sync_session, "after_transaction_end")
            def _restart_savepoint(sess, trans):
                if trans.nested and not trans._parent.nested:
                    sess.begin_nested()

            yield session

        await outer_transaction.rollback()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP test client.

    Overrides the database session and settings dependencies
    so all requests use the test transaction.
    """

    async def override_get_db():
        yield db_session

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a basic test user."""
    user = User(
        id=uuid4(),
        telegram_id=123456789,
        first_name="Test",
        last_name="User",
        username="testuser",
        role=UserRole.USER,
        approval_status=UserApprovalStatus.APPROVED,
        auth_source="telegram",
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_seller_user(db_session: AsyncSession) -> User:
    """Create a test user with seller role."""
    user = User(
        id=uuid4(),
        telegram_id=987654321,
        first_name="Seller",
        last_name="Test",
        username="testseller",
        phone="+998901234567",
        role=UserRole.SELLER,
        approval_status=UserApprovalStatus.APPROVED,
        auth_source="olx_phone",
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_seller(
    db_session: AsyncSession,
    test_seller_user: User,
) -> Seller:
    """Create a test seller profile."""
    seller = Seller(
        id=uuid4(),
        user_id=test_seller_user.id,
        company_name="Test Company",
        phone="+998901234567",
        is_verified=False,
    )
    db_session.add(seller)
    await db_session.flush()
    return seller


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        id=uuid4(),
        telegram_id=111111111,
        first_name="Admin",
        last_name="Test",
        username="testadmin",
        role=UserRole.ADMIN,
        approval_status=UserApprovalStatus.APPROVED,
        auth_source="admin",
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_listing(
    db_session: AsyncSession,
    test_seller: Seller,
    test_seller_user: User,
) -> Listing:
    """Create a test listing."""
    listing = Listing(
        id=uuid4(),
        seller_id=test_seller.id,
        title="Test Apartment",
        title_ru="Тестовая квартира",
        description="A nice test apartment",
        description_ru="Хорошая тестовая квартира",
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        price=50000,
        currency=Currency.USD,
        rooms=3,
        area=75.0,
        floor=5,
        total_floors=9,
        region="tashkent",
        district="yunusabad",
        address="Test Street 1",
        phone="+998901234567",
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


def auth_headers(user: User, scope: str = "buyer") -> Dict[str, str]:
    """Generate auth headers for a user."""
    token = create_access_token(data={"sub": str(user.id), "scope": scope})
    return {"Authorization": f"Bearer {token}"}


def admin_auth_headers(user: User) -> Dict[str, str]:
    """Generate admin auth headers."""
    return auth_headers(user, scope="admin")


def seller_auth_headers(user: User) -> Dict[str, str]:
    """Generate seller auth headers."""
    return auth_headers(user, scope="seller")


@pytest.fixture
def user_headers(test_user: User) -> Dict[str, str]:
    """Auth headers for regular user."""
    return auth_headers(test_user)


@pytest.fixture
def seller_headers(test_seller_user: User) -> Dict[str, str]:
    """Auth headers for seller."""
    return seller_auth_headers(test_seller_user)


@pytest.fixture
def admin_headers(test_admin_user: User) -> Dict[str, str]:
    """Auth headers for admin."""
    return admin_auth_headers(test_admin_user)
