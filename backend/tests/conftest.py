"""
Pytest fixtures for database testing with PostgreSQL.
"""

import asyncio
from datetime import date
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from database.config import get_settings
from database.models import Base, Account
from database.repository import AccountRepository, TransactionRepository

# Test database configuration
settings = get_settings()
TEST_DB_NAME = f"{settings.postgres_db}_test"
TEST_DATABASE_URL = (
    f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{TEST_DB_NAME}"
)
ADMIN_DATABASE_URL = (
    f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_test_database():
    """Create test database at session start, drop at session end."""
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")

    async with admin_engine.connect() as conn:
        # Drop test database if exists
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        # Create fresh test database
        await conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))

    await admin_engine.dispose()

    yield

    # Teardown: drop test database
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")

    async with admin_engine.connect() as conn:
        # Terminate existing connections
        await conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
            AND pid <> pg_backend_pid()
        """))
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))

    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def engine(setup_test_database):
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def account_repo(session: AsyncSession) -> AccountRepository:
    return AccountRepository(session)


@pytest_asyncio.fixture
async def transaction_repo(session: AsyncSession) -> TransactionRepository:
    return TransactionRepository(session)


@pytest_asyncio.fixture
async def sample_accounts(account_repo: AccountRepository) -> dict[str, Account]:
    accounts = {}

    account_data = [
        ("Assets:Bank:Checking", "USD", "Main checking account"),
        ("Assets:Bank:Savings", "USD", "Savings account"),
        ("Liabilities:CreditCard:Visa", "USD", "Visa credit card"),
        ("Expenses:Food:Groceries", "USD", "Grocery expenses"),
        ("Expenses:Food:Restaurant", "USD", "Restaurant expenses"),
        ("Expenses:Transport", "USD", "Transportation"),
        ("Income:Salary", "USD", "Monthly salary"),
        ("Equity:OpeningBalance", "USD", "Opening balances"),
    ]

    for name, currency, description in account_data:
        account = await account_repo.create(
            name=name,
            open_date=date(2024, 1, 1),
            currency=currency,
            description=description,
        )
        key = name.split(":")[-1]
        accounts[key] = account

    return accounts
