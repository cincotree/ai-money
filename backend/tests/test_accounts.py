import uuid
from datetime import date

import pytest

from database.models import AccountType
from database.repository import AccountRepository


@pytest.mark.asyncio
class TestAccountCreation:

    async def test_create_account(self, account_repo: AccountRepository):
        account = await account_repo.create(
            name="Assets:Bank:Checking",
            open_date=date(2024, 1, 1),
            currency="EUR",
            description="Main checking account",
            meta={"bank_number": "123456"},
        )

        assert account.id is not None
        assert account.name == "Assets:Bank:Checking"
        assert account.account_type == AccountType.ASSETS
        assert account.currency == "EUR"
        assert account.open_date == date(2024, 1, 1)
        assert account.description == "Main checking account"
        assert account.meta == {"bank_number": "123456"}
        assert account.is_active is True
        assert account.close_date is None

    @pytest.mark.parametrize("name,expected_type", [
        ("Assets:Cash", AccountType.ASSETS),
        ("Liabilities:CreditCard:Visa", AccountType.LIABILITIES),
        ("Equity:OpeningBalance", AccountType.EQUITY),
        ("Income:Salary", AccountType.INCOME),
        ("Expenses:Food:Groceries", AccountType.EXPENSES),
    ])
    async def test_account_types(self, account_repo: AccountRepository, name: str, expected_type: AccountType):
        account = await account_repo.create(
            name=name,
            open_date=date(2024, 1, 1),
        )

        assert account.account_type == expected_type

    async def test_account_hierarchy(self, account_repo: AccountRepository):
        account = await account_repo.create(
            name="Assets:Bank:Chase:Checking",
            open_date=date(2024, 1, 1),
        )

        assert account.parent_name == "Assets:Bank:Chase"
        assert account.short_name == "Checking"

        top_level = await account_repo.create(
            name="Assets",
            open_date=date(2024, 1, 1),
        )

        assert top_level.parent_name is None
        assert top_level.short_name == "Assets"

    async def test_invalid_account_type(self, account_repo: AccountRepository):
        with pytest.raises(ValueError) as exc_info:
            await account_repo.create(
                name="InvalidType:Account",
                open_date=date(2024, 1, 1),
            )

        assert "Invalid account type" in str(exc_info.value)


@pytest.mark.asyncio
class TestAccountRetrieval:

    async def test_get_by_id(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        checking = sample_accounts["Checking"]
        retrieved = await account_repo.get_by_id(checking.id)

        assert retrieved is not None
        assert retrieved.id == checking.id
        assert retrieved.name == checking.name

    async def test_get_by_name(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        account = await account_repo.get_by_name("Assets:Bank:Checking")

        assert account is not None
        assert account.name == "Assets:Bank:Checking"

    async def test_get_nonexistent_account(self, account_repo: AccountRepository):
        account = await account_repo.get_by_id(str(uuid.uuid4()))
        assert account is None

        account = await account_repo.get_by_name("Nonexistent:Account")
        assert account is None

    async def test_get_or_create_existing(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        account, created = await account_repo.get_or_create(
            name="Assets:Bank:Checking",
            open_date=date(2024, 1, 1),
        )

        assert created is False
        assert account.id == sample_accounts["Checking"].id

    async def test_get_or_create_new(self, account_repo: AccountRepository):
        account, created = await account_repo.get_or_create(
            name="Assets:Cash:Wallet",
            open_date=date(2024, 1, 1),
        )

        assert created is True
        assert account.name == "Assets:Cash:Wallet"


@pytest.mark.asyncio
class TestAccountListing:

    async def test_list_all(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        accounts = await account_repo.list_all()

        assert len(accounts) == len(sample_accounts)

    async def test_list_by_type(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        expense_accounts = await account_repo.list_all(account_type=AccountType.EXPENSES)

        assert len(expense_accounts) == 3  # Groceries, Restaurant, Transport
        for account in expense_accounts:
            assert account.account_type == AccountType.EXPENSES

    async def test_list_by_prefix(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        food_accounts = await account_repo.list_by_prefix("Expenses:Food")

        assert len(food_accounts) == 2  # Groceries and Restaurant
        for account in food_accounts:
            assert account.name.startswith("Expenses:Food")

    async def test_list_active_only(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        await account_repo.close_account(
            sample_accounts["Savings"].id,
            date(2024, 6, 1),
        )

        active_accounts = await account_repo.list_all(is_active=True)
        inactive_accounts = await account_repo.list_all(is_active=False)

        assert len(active_accounts) == len(sample_accounts) - 1
        assert len(inactive_accounts) == 1


@pytest.mark.asyncio
class TestAccountOperations:

    async def test_close_account(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        checking = sample_accounts["Checking"]
        closed = await account_repo.close_account(checking.id, date(2024, 12, 31))

        assert closed is not None
        assert closed.is_active is False
        assert closed.close_date == date(2024, 12, 31)

    async def test_delete_account(
        self, account_repo: AccountRepository, sample_accounts: dict
    ):
        checking = sample_accounts["Checking"]
        deleted = await account_repo.delete(checking.id)

        assert deleted is True

        retrieved = await account_repo.get_by_id(checking.id)
        assert retrieved is None

    async def test_delete_nonexistent_account(self, account_repo: AccountRepository):
        deleted = await account_repo.delete(str(uuid.uuid4()))
        assert deleted is False
