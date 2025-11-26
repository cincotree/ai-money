from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from database.models import Transaction
from database.repository import AccountRepository, TransactionRepository


@pytest.mark.asyncio
class TestTransactionCreation:

    async def test_create_transaction(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        meta = {"invoice": "INV-001", "receipt": "path/to/receipt.pdf"}
        transaction = await transaction_repo.create(
            date=date(2024, 3, 15),
            narration="Business lunch at Italian restaurant",
            payee="The Italian Place",
            flag="!",
            tags=["business", "tax-deductible"],
            links=["trip-2024-nyc"],
            meta=meta,
            postings=[
                {
                    "account_id": sample_accounts["Restaurant"].id,
                    "amount": Decimal("75.00"),
                    "currency": "USD",
                },
                {
                    "account_id": sample_accounts["Checking"].id,
                    "amount": Decimal("-75.00"),
                    "currency": "USD",
                },
            ],
        )

        assert transaction.id is not None
        assert transaction.date == date(2024, 3, 15)
        assert transaction.narration == "Business lunch at Italian restaurant"
        assert transaction.payee == "The Italian Place"
        assert transaction.flag == "!"
        assert transaction.meta == meta
        assert len(transaction.postings) == 2
        assert len(transaction.tags) == 2
        assert {t.tag for t in transaction.tags} == {"business", "tax-deductible"}
        assert len(transaction.links) == 1
        assert transaction.links[0].link == "trip-2024-nyc"

    async def test_auto_balance(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        transaction = await transaction_repo.create(
            date=date(2024, 3, 15),
            narration="Restaurant dinner",
            postings=[
                {
                    "account_id": sample_accounts["Restaurant"].id,
                    "amount": Decimal("75.00"),
                },
                {
                    "account_id": sample_accounts["Visa"].id,
                    "amount": None,
                },
            ],
        )

        auto_posting = next(
            p for p in transaction.postings if p.account_id == sample_accounts["Visa"].id
        )
        assert auto_posting.amount == Decimal("-75.00")

    async def test_multi_posting_transaction(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        transaction = await transaction_repo.create(
            date=date(2024, 3, 15),
            narration="Costco shopping - split",
            postings=[
                {"account_id": sample_accounts["Groceries"].id, "amount": Decimal("150.00")},
                {"account_id": sample_accounts["Transport"].id, "amount": Decimal("50.00")},
                {"account_id": sample_accounts["Visa"].id, "amount": Decimal("-200.00")},
            ],
        )

        assert len(transaction.postings) == 3
        assert transaction.is_balanced

    async def test_validation_errors(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        with pytest.raises(ValueError, match="do not balance"):
            await transaction_repo.create(
                date=date(2024, 3, 15),
                narration="Unbalanced",
                postings=[
                    {"account_id": sample_accounts["Groceries"].id, "amount": Decimal("100.00")},
                    {"account_id": sample_accounts["Checking"].id, "amount": Decimal("-50.00")},
                ],
            )

        with pytest.raises(ValueError, match="Only one posting"):
            await transaction_repo.create(
                date=date(2024, 3, 15),
                narration="Multiple auto-balance",
                postings=[
                    {"account_id": sample_accounts["Groceries"].id, "amount": Decimal("100.00")},
                    {"account_id": sample_accounts["Checking"].id, "amount": None},
                    {"account_id": sample_accounts["Visa"].id, "amount": None},
                ],
            )


@pytest.mark.asyncio
class TestTransactionRetrieval:

    async def test_get_by_id(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        created = await transaction_repo.create(
            date=date(2024, 3, 15),
            narration="Test transaction",
            postings=[
                {
                    "account_id": sample_accounts["Groceries"].id,
                    "amount": Decimal("50.00"),
                },
                {
                    "account_id": sample_accounts["Checking"].id,
                    "amount": Decimal("-50.00"),
                },
            ],
        )

        retrieved = await transaction_repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.narration == "Test transaction"
        assert len(retrieved.postings) == 2

    async def test_get_by_link(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        for amount in [Decimal("100.00"), Decimal("200.00")]:
            await transaction_repo.create(
                date=date(2024, 3, 15),
                narration=f"Trip expense {amount}",
                links=["trip-2024-nyc"],
                postings=[
                    {
                        "account_id": sample_accounts["Transport"].id,
                        "amount": amount,
                    },
                    {
                        "account_id": sample_accounts["Checking"].id,
                        "amount": -amount,
                    },
                ],
            )

        transactions = await transaction_repo.get_by_link("trip-2024-nyc")

        assert len(transactions) == 2

    async def test_get_nonexistent_transaction(
        self, transaction_repo: TransactionRepository
    ):
        transaction = await transaction_repo.get_by_id("nonexistent-id")
        assert transaction is None


@pytest.mark.asyncio
class TestTransactionListing:

    @pytest_asyncio.fixture
    async def sample_transactions(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ) -> list[Transaction]:
        transactions = []

        test_data = [
            (date(2024, 3, 1), "Grocery 1", sample_accounts["Groceries"].id, "100.00"),
            (date(2024, 3, 5), "Restaurant 1", sample_accounts["Restaurant"].id, "45.00"),
            (date(2024, 3, 10), "Grocery 2", sample_accounts["Groceries"].id, "80.00"),
            (date(2024, 3, 15), "Gas", sample_accounts["Transport"].id, "50.00"),
            (date(2024, 3, 20), "Restaurant 2", sample_accounts["Restaurant"].id, "65.00"),
        ]

        for txn_date, narration, expense_id, amount in test_data:
            txn = await transaction_repo.create(
                date=txn_date,
                narration=narration,
                postings=[
                    {
                        "account_id": expense_id,
                        "amount": Decimal(amount),
                    },
                    {
                        "account_id": sample_accounts["Checking"].id,
                        "amount": -Decimal(amount),
                    },
                ],
            )
            transactions.append(txn)

        return transactions

    async def test_list_by_date_range(
        self,
        transaction_repo: TransactionRepository,
        sample_transactions: list[Transaction],
    ):
        transactions = await transaction_repo.list_by_date_range(
            start_date=date(2024, 3, 5),
            end_date=date(2024, 3, 15),
        )

        assert len(transactions) == 3
        for txn in transactions:
            assert date(2024, 3, 5) <= txn.date <= date(2024, 3, 15)

    async def test_list_by_date_range_with_account(
        self,
        transaction_repo: TransactionRepository,
        sample_transactions: list[Transaction],
        sample_accounts: dict,
    ):
        transactions = await transaction_repo.list_by_date_range(
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31),
            account_id=sample_accounts["Groceries"].id,
        )

        assert len(transactions) == 2

    async def test_search_by_narration(
        self,
        transaction_repo: TransactionRepository,
        sample_transactions: list[Transaction],
    ):
        transactions = await transaction_repo.search(query_text="Restaurant")

        assert len(transactions) == 2

    async def test_search_by_amount_range(
        self,
        transaction_repo: TransactionRepository,
        sample_transactions: list[Transaction],
    ):
        transactions = await transaction_repo.search(
            min_amount=Decimal("60.00"),
            max_amount=Decimal("100.00"),
        )

        assert len(transactions) == 3

    async def test_search_with_tag(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        await transaction_repo.create(
            date=date(2024, 3, 15),
            narration="Business expense",
            tags=["business"],
            postings=[
                {
                    "account_id": sample_accounts["Restaurant"].id,
                    "amount": Decimal("100.00"),
                },
                {
                    "account_id": sample_accounts["Checking"].id,
                    "amount": Decimal("-100.00"),
                },
            ],
        )

        transactions = await transaction_repo.search(tag="business")

        assert len(transactions) == 1


@pytest.mark.asyncio
class TestTransactionOperations:

    async def test_update_posting_account(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        transaction = await transaction_repo.create(
            date=date(2024, 3, 15),
            narration="Coffee shop",
            postings=[
                {
                    "account_id": sample_accounts["Groceries"].id,
                    "amount": Decimal("5.00"),
                },
                {
                    "account_id": sample_accounts["Checking"].id,
                    "amount": Decimal("-5.00"),
                },
            ],
        )

        updated = await transaction_repo.update_posting_account(
            transaction_id=transaction.id,
            old_account_id=sample_accounts["Groceries"].id,
            new_account_id=sample_accounts["Restaurant"].id,
        )

        assert updated is not None
        restaurant_posting = next(
            p for p in updated.postings if p.account_id == sample_accounts["Restaurant"].id
        )
        assert restaurant_posting.amount == Decimal("5.00")

    async def test_delete_transaction(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        transaction = await transaction_repo.create(
            date=date(2024, 3, 15),
            narration="To be deleted",
            postings=[
                {
                    "account_id": sample_accounts["Groceries"].id,
                    "amount": Decimal("10.00"),
                },
                {
                    "account_id": sample_accounts["Checking"].id,
                    "amount": Decimal("-10.00"),
                },
            ],
        )

        deleted = await transaction_repo.delete(transaction.id)
        assert deleted is True

        retrieved = await transaction_repo.get_by_id(transaction.id)
        assert retrieved is None


@pytest.mark.asyncio
class TestAccountBalance:

    async def test_account_balance_after_transactions(
        self,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        amounts = [Decimal("100.00"), Decimal("50.00"), Decimal("75.00")]

        for amount in amounts:
            await transaction_repo.create(
                date=date(2024, 3, 15),
                narration=f"Expense {amount}",
                postings=[
                    {
                        "account_id": sample_accounts["Groceries"].id,
                        "amount": amount,
                    },
                    {
                        "account_id": sample_accounts["Checking"].id,
                        "amount": -amount,
                    },
                ],
            )

        grocery_balance = await account_repo.get_balance(sample_accounts["Groceries"].id)
        assert grocery_balance == sum(amounts)

        checking_balance = await account_repo.get_balance(sample_accounts["Checking"].id)
        assert checking_balance == -sum(amounts)

    async def test_account_balance_as_of_date(
        self,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        await transaction_repo.create(
            date=date(2024, 3, 1),
            narration="Early expense",
            postings=[
                {"account_id": sample_accounts["Groceries"].id, "amount": Decimal("100.00")},
                {"account_id": sample_accounts["Checking"].id, "amount": Decimal("-100.00")},
            ],
        )

        await transaction_repo.create(
            date=date(2024, 3, 15),
            narration="Later expense",
            postings=[
                {"account_id": sample_accounts["Groceries"].id, "amount": Decimal("200.00")},
                {"account_id": sample_accounts["Checking"].id, "amount": Decimal("-200.00")},
            ],
        )

        balance = await account_repo.get_balance(
            sample_accounts["Groceries"].id,
            as_of_date=date(2024, 3, 10),
        )
        assert balance == Decimal("100.00")

        balance = await account_repo.get_balance(
            sample_accounts["Groceries"].id,
            as_of_date=date(2024, 3, 20),
        )
        assert balance == Decimal("300.00")


@pytest.mark.asyncio
class TestAccountStatement:

    async def test_get_account_statement(
        self,
        transaction_repo: TransactionRepository,
        sample_accounts: dict,
    ):
        await transaction_repo.create(
            date=date(2024, 3, 1),
            narration="First purchase",
            postings=[
                {"account_id": sample_accounts["Groceries"].id, "amount": Decimal("100.00")},
                {"account_id": sample_accounts["Checking"].id, "amount": Decimal("-100.00")},
            ],
        )

        await transaction_repo.create(
            date=date(2024, 3, 10),
            narration="Second purchase",
            postings=[
                {"account_id": sample_accounts["Groceries"].id, "amount": Decimal("50.00")},
                {"account_id": sample_accounts["Checking"].id, "amount": Decimal("-50.00")},
            ],
        )

        statement = await transaction_repo.get_account_statement(
            account_id=sample_accounts["Groceries"].id,
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31),
        )

        assert len(statement) == 2

        assert statement[0]["amount"] == Decimal("100.00")
        assert statement[0]["balance"] == Decimal("100.00")

        assert statement[1]["amount"] == Decimal("50.00")
        assert statement[1]["balance"] == Decimal("150.00")
