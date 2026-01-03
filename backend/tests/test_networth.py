import pytest
import pytest_asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from database.repository import AccountRepository, BalanceRepository, ExchangeRateRepository
from database.models import AccountType


@pytest_asyncio.fixture
async def balance_repo(session: AsyncSession) -> BalanceRepository:
    return BalanceRepository(session)


@pytest_asyncio.fixture
async def exchange_rate_repo(session: AsyncSession) -> ExchangeRateRepository:
    return ExchangeRateRepository(session)


@pytest.mark.asyncio
async def test_create_asset_account(account_repo: AccountRepository, session: AsyncSession):
    account = await account_repo.create(
        name="Assets:Bank:TestBank",
        open_date=date(2024, 1, 1),
        currency="USD",
        description="Test bank account",
    )
    await session.commit()

    assert account.id is not None
    assert account.name == "Assets:Bank:TestBank"
    assert account.account_type == AccountType.ASSETS
    assert account.currency == "USD"
    assert account.is_active is True


@pytest.mark.asyncio
async def test_create_liability_account(account_repo: AccountRepository, session: AsyncSession):
    account = await account_repo.create(
        name="Liabilities:CreditCard:TestCard",
        open_date=date(2024, 1, 1),
        currency="USD",
        description="Test credit card",
    )
    await session.commit()

    assert account.account_type == AccountType.LIABILITIES


@pytest.mark.asyncio
async def test_create_balance_entry(
    account_repo: AccountRepository,
    balance_repo: BalanceRepository,
    session: AsyncSession,
):
    account = await account_repo.create(
        name="Assets:Bank:TestSavings",
        open_date=date(2024, 1, 1),
        currency="USD",
    )
    await session.commit()

    balance = await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 6, 1),
        amount=Decimal("10000.50"),
        currency="USD",
    )
    await session.commit()

    assert balance.id is not None
    assert balance.account_id == account.id
    assert balance.amount == Decimal("10000.50")
    assert balance.currency == "USD"
    assert balance.date == date(2024, 6, 1)
    assert balance.is_verified is True


@pytest.mark.asyncio
async def test_update_existing_balance(
    account_repo: AccountRepository,
    balance_repo: BalanceRepository,
    session: AsyncSession,
):
    account = await account_repo.create(
        name="Assets:Bank:UpdateTest",
        open_date=date(2024, 1, 1),
        currency="USD",
    )
    await session.commit()

    balance1 = await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 6, 1),
        amount=Decimal("5000"),
        currency="USD",
    )
    await session.commit()
    balance1_id = balance1.id

    balance2 = await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 6, 1),
        amount=Decimal("7500"),
        currency="USD",
    )
    await session.commit()

    assert balance2.id == balance1_id
    assert balance2.amount == Decimal("7500")


@pytest.mark.asyncio
async def test_get_latest_balances(
    account_repo: AccountRepository,
    balance_repo: BalanceRepository,
    session: AsyncSession,
):
    account = await account_repo.create(
        name="Assets:Bank:LatestTest",
        open_date=date(2024, 1, 1),
        currency="USD",
    )
    await session.commit()

    await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 1, 1),
        amount=Decimal("1000"),
        currency="USD",
    )
    await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 6, 1),
        amount=Decimal("2000"),
        currency="USD",
    )
    await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 12, 1),
        amount=Decimal("3000"),
        currency="USD",
    )
    await session.commit()

    balances = await balance_repo.get_latest_balances(as_of_date=date(2024, 12, 31))
    assert len(balances) == 1
    assert balances[0].amount == Decimal("3000")

    balances_june = await balance_repo.get_latest_balances(as_of_date=date(2024, 6, 30))
    assert len(balances_june) == 1
    assert balances_june[0].amount == Decimal("2000")


@pytest.mark.asyncio
async def test_multi_currency_balances(
    account_repo: AccountRepository,
    balance_repo: BalanceRepository,
    session: AsyncSession,
):
    account = await account_repo.create(
        name="Assets:MultiCurrency:Test",
        open_date=date(2024, 1, 1),
        currency="USD",
    )
    await session.commit()

    await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 6, 1),
        amount=Decimal("10000"),
        currency="USD",
    )
    await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 6, 1),
        amount=Decimal("500000"),
        currency="INR",
    )
    await session.commit()

    balances = await balance_repo.get_latest_balances()
    assert len(balances) == 2

    currencies = {b.currency for b in balances}
    assert currencies == {"USD", "INR"}


@pytest.mark.asyncio
async def test_net_worth_calculation(
    account_repo: AccountRepository,
    balance_repo: BalanceRepository,
    session: AsyncSession,
):
    asset_account = await account_repo.create(
        name="Assets:Bank:NetWorthTest",
        open_date=date(2024, 1, 1),
        currency="USD",
    )
    liability_account = await account_repo.create(
        name="Liabilities:Loan:NetWorthTest",
        open_date=date(2024, 1, 1),
        currency="USD",
    )
    await session.commit()

    await balance_repo.create_or_update(
        account_id=asset_account.id,
        date=date(2024, 6, 1),
        amount=Decimal("50000"),
        currency="USD",
    )
    await balance_repo.create_or_update(
        account_id=liability_account.id,
        date=date(2024, 6, 1),
        amount=Decimal("20000"),
        currency="USD",
    )
    await session.commit()

    balances = await balance_repo.get_latest_balances()

    total_assets = sum(
        b.amount for b in balances if b.account.account_type == AccountType.ASSETS
    )
    total_liabilities = sum(
        b.amount for b in balances if b.account.account_type == AccountType.LIABILITIES
    )
    net_worth = total_assets - total_liabilities

    assert total_assets == Decimal("50000")
    assert total_liabilities == Decimal("20000")
    assert net_worth == Decimal("30000")


@pytest.mark.asyncio
async def test_delete_balance(
    account_repo: AccountRepository,
    balance_repo: BalanceRepository,
    session: AsyncSession,
):
    account = await account_repo.create(
        name="Assets:DeleteTest",
        open_date=date(2024, 1, 1),
        currency="USD",
    )
    await session.commit()

    balance = await balance_repo.create_or_update(
        account_id=account.id,
        date=date(2024, 6, 1),
        amount=Decimal("1000"),
        currency="USD",
    )
    await session.commit()
    balance_id = balance.id

    deleted = await balance_repo.delete(balance_id)
    await session.commit()

    assert deleted is True

    balances = await balance_repo.get_latest_balances()
    assert len(balances) == 0


@pytest.mark.asyncio
async def test_create_exchange_rate(
    exchange_rate_repo: ExchangeRateRepository,
    session: AsyncSession,
):
    rate = await exchange_rate_repo.create_or_update(
        date=date(2024, 6, 1),
        from_currency="USD",
        to_currency="INR",
        rate=Decimal("83.5"),
        source="manual",
    )
    await session.commit()

    assert rate.id is not None
    assert rate.from_currency == "USD"
    assert rate.to_currency == "INR"
    assert rate.rate == Decimal("83.5")
    assert rate.source == "manual"


@pytest.mark.asyncio
async def test_update_exchange_rate(
    exchange_rate_repo: ExchangeRateRepository,
    session: AsyncSession,
):
    rate1 = await exchange_rate_repo.create_or_update(
        date=date(2024, 6, 1),
        from_currency="USD",
        to_currency="EUR",
        rate=Decimal("0.92"),
    )
    await session.commit()
    rate1_id = rate1.id

    rate2 = await exchange_rate_repo.create_or_update(
        date=date(2024, 6, 1),
        from_currency="USD",
        to_currency="EUR",
        rate=Decimal("0.93"),
    )
    await session.commit()

    assert rate2.id == rate1_id
    assert rate2.rate == Decimal("0.93")


@pytest.mark.asyncio
async def test_get_exchange_rate(
    exchange_rate_repo: ExchangeRateRepository,
    session: AsyncSession,
):
    await exchange_rate_repo.create_or_update(
        date=date(2024, 1, 1),
        from_currency="USD",
        to_currency="GBP",
        rate=Decimal("0.79"),
    )
    await exchange_rate_repo.create_or_update(
        date=date(2024, 6, 1),
        from_currency="USD",
        to_currency="GBP",
        rate=Decimal("0.80"),
    )
    await exchange_rate_repo.create_or_update(
        date=date(2024, 12, 1),
        from_currency="USD",
        to_currency="GBP",
        rate=Decimal("0.81"),
    )
    await session.commit()

    rate_june = await exchange_rate_repo.get_rate(
        from_currency="USD",
        to_currency="GBP",
        as_of_date=date(2024, 6, 30),
    )
    assert rate_june == Decimal("0.80")

    rate_latest = await exchange_rate_repo.get_rate(
        from_currency="USD",
        to_currency="GBP",
        as_of_date=date(2024, 12, 31),
    )
    assert rate_latest == Decimal("0.81")


@pytest.mark.asyncio
async def test_list_exchange_rates(
    exchange_rate_repo: ExchangeRateRepository,
    session: AsyncSession,
):
    await exchange_rate_repo.create_or_update(
        date=date(2024, 6, 1),
        from_currency="USD",
        to_currency="INR",
        rate=Decimal("83.5"),
    )
    await exchange_rate_repo.create_or_update(
        date=date(2024, 6, 1),
        from_currency="USD",
        to_currency="EUR",
        rate=Decimal("0.92"),
    )
    await exchange_rate_repo.create_or_update(
        date=date(2024, 6, 1),
        from_currency="EUR",
        to_currency="INR",
        rate=Decimal("90.5"),
    )
    await session.commit()

    all_rates = await exchange_rate_repo.list_all()
    assert len(all_rates) == 3

    usd_rates = await exchange_rate_repo.list_all(from_currency="USD")
    assert len(usd_rates) == 2

    inr_rates = await exchange_rate_repo.list_all(to_currency="INR")
    assert len(inr_rates) == 2


@pytest.mark.asyncio
async def test_delete_exchange_rate(
    exchange_rate_repo: ExchangeRateRepository,
    session: AsyncSession,
):
    rate = await exchange_rate_repo.create_or_update(
        date=date(2024, 6, 1),
        from_currency="USD",
        to_currency="CAD",
        rate=Decimal("1.35"),
    )
    await session.commit()
    rate_id = rate.id

    deleted = await exchange_rate_repo.delete(rate_id)
    await session.commit()

    assert deleted is True

    all_rates = await exchange_rate_repo.list_all()
    assert len(all_rates) == 0
