"""
Repository pattern for database operations.

Provides clean abstractions for CRUD operations on accounting entities.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    Account,
    AccountType,
    Balance,
    ExchangeRate,
    Transaction,
    Posting,
    TransactionLink,
    TransactionTag,
)


class AccountRepository:
    """Repository for Account operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        open_date: date,
        currency: str = "USD",
        description: str | None = None,
        meta: dict | None = None,
    ) -> Account:
        """
        Create a new account.

        Args:
            name: Full account name (e.g., "Assets:Bank:Checking")
            open_date: Date the account was opened
            currency: Default currency for the account
            description: Optional description
            meta: Optional metadata dictionary

        Returns:
            The created Account instance
        """
        # Derive account type from the first component
        first_component = name.split(":")[0]
        try:
            account_type = AccountType(first_component)
        except ValueError:
            raise ValueError(
                f"Invalid account type '{first_component}'. "
                f"Must be one of: {[t.value for t in AccountType]}"
            )

        account = Account(
            name=name,
            account_type=account_type,
            currency=currency,
            open_date=open_date,
            description=description,
            meta=meta,
        )
        self.session.add(account)
        await self.session.flush()
        return account

    async def get_by_id(self, account_id: str) -> Account | None:
        """Get an account by ID."""
        result = await self.session.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Account | None:
        """Get an account by its full name."""
        result = await self.session.execute(
            select(Account).where(Account.name == name)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        name: str,
        open_date: date,
        currency: str = "USD",
        description: str | None = None,
    ) -> tuple[Account, bool]:
        """
        Get an existing account or create a new one.

        Returns:
            Tuple of (account, created) where created is True if new
        """
        account = await self.get_by_name(name)
        if account:
            return account, False
        account = await self.create(name, open_date, currency, description)
        return account, True

    async def list_all(
        self,
        account_type: AccountType | None = None,
        is_active: bool | None = None,
    ) -> list[Account]:
        """
        List all accounts with optional filters.

        Args:
            account_type: Filter by account type
            is_active: Filter by active status

        Returns:
            List of Account instances
        """
        query = select(Account).order_by(Account.name)

        if account_type is not None:
            query = query.where(Account.account_type == account_type)
        if is_active is not None:
            query = query.where(Account.is_active == is_active)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_prefix(self, prefix: str) -> list[Account]:
        """
        List accounts matching a name prefix.

        Args:
            prefix: Account name prefix (e.g., "Assets:Bank")

        Returns:
            List of Account instances
        """
        result = await self.session.execute(
            select(Account)
            .where(Account.name.startswith(prefix))
            .order_by(Account.name)
        )
        return list(result.scalars().all())

    async def close_account(self, account_id: str, close_date: date) -> Account | None:
        """
        Close an account.

        Args:
            account_id: Account ID to close
            close_date: Date to close the account

        Returns:
            Updated Account or None if not found
        """
        account = await self.get_by_id(account_id)
        if account:
            account.close_date = close_date
            account.is_active = False
            await self.session.flush()
        return account

    async def get_balance(
        self,
        account_id: str,
        as_of_date: date | None = None,
        currency: str = "USD",
    ) -> Decimal:
        """
        Calculate account balance from postings.

        Args:
            account_id: Account ID
            as_of_date: Calculate balance as of this date (default: today)
            currency: Currency to sum

        Returns:
            Account balance as Decimal
        """
        if as_of_date is None:
            as_of_date = date.today()

        result = await self.session.execute(
            select(func.coalesce(func.sum(Posting.amount), 0))
            .join(Transaction)
            .where(
                and_(
                    Posting.account_id == account_id,
                    Posting.currency == currency,
                    Transaction.date <= as_of_date,
                )
            )
        )
        return result.scalar() or Decimal(0)

    async def delete(self, account_id: str) -> bool:
        """
        Delete an account.

        Args:
            account_id: Account ID to delete

        Returns:
            True if deleted, False if not found
        """
        account = await self.get_by_id(account_id)
        if account:
            await self.session.delete(account)
            await self.session.flush()
            return True
        return False


class TransactionRepository:
    """Repository for Transaction operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        date: date,
        narration: str,
        postings: list[dict[str, Any]],
        payee: str | None = None,
        flag: str = "*",
        tags: list[str] | None = None,
        links: list[str] | None = None,
        meta: dict | None = None,
    ) -> Transaction:
        """
        Create a new transaction with postings.

        Args:
            date: Transaction date
            narration: Transaction description
            postings: List of posting dicts with keys:
                - account_id: Account ID
                - amount: Decimal amount (can be None for auto-balance)
                - currency: Currency code (default: USD)
            payee: Optional payee name
            flag: Transaction flag (* or !)
            tags: Optional list of tags
            links: Optional list of links
            meta: Optional metadata dictionary

        Returns:
            The created Transaction instance

        Raises:
            ValueError: If postings don't balance
        """
        # Create transaction
        transaction = Transaction(
            date=date,
            narration=narration,
            payee=payee,
            flag=flag,
            meta=meta,
        )
        self.session.add(transaction)
        await self.session.flush()  # Get transaction ID

        # Calculate auto-balance if needed
        total = Decimal(0)
        auto_balance_posting = None
        for i, posting_data in enumerate(postings):
            amount = posting_data.get("amount")
            if amount is None:
                if auto_balance_posting is not None:
                    raise ValueError("Only one posting can have auto-balance (None amount)")
                auto_balance_posting = i
            else:
                total += Decimal(str(amount))

        # Create postings
        for i, posting_data in enumerate(postings):
            amount = posting_data.get("amount")
            if i == auto_balance_posting:
                amount = -total  # Auto-balance

            posting = Posting(
                transaction_id=transaction.id,
                account_id=posting_data["account_id"],
                amount=amount,
                currency=posting_data.get("currency", "USD"),
                position=i,
            )
            self.session.add(posting)

        # Validate balance
        if auto_balance_posting is None and abs(total) >= Decimal("0.001"):
            raise ValueError(f"Transaction postings do not balance: {total}")

        # Add tags
        if tags:
            for tag in tags:
                tag_obj = TransactionTag(transaction_id=transaction.id, tag=tag)
                self.session.add(tag_obj)

        # Add links
        if links:
            for link in links:
                link_obj = TransactionLink(transaction_id=transaction.id, link=link)
                self.session.add(link_obj)

        await self.session.flush()

        # Re-fetch with eager loading to avoid lazy loading issues
        return await self.get_by_id(transaction.id)

    async def get_by_id(
        self, transaction_id: str, include_postings: bool = True
    ) -> Transaction | None:
        """
        Get a transaction by ID.

        Args:
            transaction_id: Transaction ID
            include_postings: Whether to eagerly load postings

        Returns:
            Transaction or None if not found
        """
        query = select(Transaction).where(Transaction.id == transaction_id)

        if include_postings:
            query = query.options(
                selectinload(Transaction.postings).selectinload(Posting.account),
                selectinload(Transaction.tags),
                selectinload(Transaction.links),
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_link(self, link: str) -> list[Transaction]:
        """
        Get all transactions with a specific link.

        Args:
            link: Link value to search for

        Returns:
            List of Transaction instances
        """
        result = await self.session.execute(
            select(Transaction)
            .join(TransactionLink)
            .where(TransactionLink.link == link)
            .options(
                selectinload(Transaction.postings).selectinload(Posting.account),
                selectinload(Transaction.tags),
                selectinload(Transaction.links),
            )
        )
        return list(result.scalars().all())

    async def list_by_date_range(
        self,
        start_date: date,
        end_date: date,
        account_id: str | None = None,
    ) -> list[Transaction]:
        """
        List transactions in a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            account_id: Optional filter by account

        Returns:
            List of Transaction instances ordered by date
        """
        query = (
            select(Transaction)
            .where(
                and_(
                    Transaction.date >= start_date,
                    Transaction.date <= end_date,
                )
            )
            .options(
                selectinload(Transaction.postings).selectinload(Posting.account),
                selectinload(Transaction.tags),
                selectinload(Transaction.links),
            )
            .order_by(Transaction.date)
        )

        if account_id:
            query = query.join(Posting).where(Posting.account_id == account_id)

        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def search(
        self,
        query_text: str | None = None,
        payee: str | None = None,
        tag: str | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """
        Search transactions with various filters.

        Args:
            query_text: Search in narration and payee
            payee: Exact payee match
            tag: Filter by tag
            min_amount: Minimum absolute posting amount
            max_amount: Maximum absolute posting amount
            limit: Maximum results to return

        Returns:
            List of Transaction instances
        """
        query = (
            select(Transaction)
            .options(
                selectinload(Transaction.postings).selectinload(Posting.account),
                selectinload(Transaction.tags),
                selectinload(Transaction.links),
            )
            .order_by(Transaction.date.desc())
            .limit(limit)
        )

        if query_text:
            query = query.where(
                or_(
                    Transaction.narration.ilike(f"%{query_text}%"),
                    Transaction.payee.ilike(f"%{query_text}%"),
                )
            )

        if payee:
            query = query.where(Transaction.payee == payee)

        if tag:
            query = query.join(TransactionTag).where(TransactionTag.tag == tag)

        if min_amount is not None or max_amount is not None:
            query = query.join(Posting)
            if min_amount is not None:
                query = query.where(func.abs(Posting.amount) >= min_amount)
            if max_amount is not None:
                query = query.where(func.abs(Posting.amount) <= max_amount)

        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def update_posting_account(
        self,
        transaction_id: str,
        old_account_id: str,
        new_account_id: str,
    ) -> Transaction | None:
        """
        Update a posting's account (useful for recategorization).

        Args:
            transaction_id: Transaction ID
            old_account_id: Current account ID
            new_account_id: New account ID

        Returns:
            Updated Transaction or None if not found
        """
        transaction = await self.get_by_id(transaction_id)
        if not transaction:
            return None

        for posting in transaction.postings:
            if posting.account_id == old_account_id:
                posting.account_id = new_account_id
                break

        await self.session.flush()
        return transaction

    async def delete(self, transaction_id: str) -> bool:
        """
        Delete a transaction and its postings.

        Args:
            transaction_id: Transaction ID to delete

        Returns:
            True if deleted, False if not found
        """
        transaction = await self.get_by_id(transaction_id, include_postings=False)
        if transaction:
            await self.session.delete(transaction)
            await self.session.flush()
            return True
        return False

    async def get_account_statement(
        self,
        account_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """
        Get account statement with running balance.

        Args:
            account_id: Account ID
            start_date: Start date
            end_date: End date

        Returns:
            List of statement entries with running balance
        """
        # Get opening balance
        opening_balance = await self._calculate_balance_before_date(
            account_id, start_date
        )

        # Get transactions in date range
        transactions = await self.list_by_date_range(start_date, end_date, account_id)

        # Build statement with running balance
        statement = []
        running_balance = opening_balance

        for txn in transactions:
            for posting in txn.postings:
                if posting.account_id == account_id:
                    running_balance += posting.amount or Decimal(0)
                    statement.append({
                        "date": txn.date,
                        "narration": txn.narration,
                        "payee": txn.payee,
                        "amount": posting.amount,
                        "currency": posting.currency,
                        "balance": running_balance,
                        "transaction_id": txn.id,
                    })

        return statement

    async def _calculate_balance_before_date(
        self, account_id: str, before_date: date
    ) -> Decimal:
        """Calculate account balance before a given date."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(Posting.amount), 0))
            .join(Transaction)
            .where(
                and_(
                    Posting.account_id == account_id,
                    Transaction.date < before_date,
                )
            )
        )
        return result.scalar() or Decimal(0)


class BalanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update(
        self,
        account_id: str,
        date: date,
        amount: Decimal,
        currency: str,
    ) -> Balance:
        existing = await self.session.execute(
            select(Balance).where(
                and_(
                    Balance.account_id == account_id,
                    Balance.date == date,
                    Balance.currency == currency,
                )
            )
        )
        balance = existing.scalar_one_or_none()

        if balance:
            balance.amount = amount
        else:
            balance = Balance(
                account_id=account_id,
                date=date,
                amount=amount,
                currency=currency,
                is_verified=True,
            )
            self.session.add(balance)

        await self.session.flush()
        return balance

    async def get_latest_balances(
        self, as_of_date: date | None = None
    ) -> list[Balance]:
        if as_of_date is None:
            as_of_date = date.today()

        subquery = (
            select(
                Balance.account_id,
                Balance.currency,
                func.max(Balance.date).label("max_date"),
            )
            .where(Balance.date <= as_of_date)
            .group_by(Balance.account_id, Balance.currency)
            .subquery()
        )

        result = await self.session.execute(
            select(Balance)
            .join(
                subquery,
                and_(
                    Balance.account_id == subquery.c.account_id,
                    Balance.currency == subquery.c.currency,
                    Balance.date == subquery.c.max_date,
                ),
            )
            .options(selectinload(Balance.account))
        )
        return list(result.scalars().all())

    async def delete(self, balance_id: str) -> bool:
        result = await self.session.execute(
            select(Balance).where(Balance.id == balance_id)
        )
        balance = result.scalar_one_or_none()
        if balance:
            await self.session.delete(balance)
            await self.session.flush()
            return True
        return False


class ExchangeRateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update(
        self,
        date: date,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        source: str | None = None,
    ) -> ExchangeRate:
        existing = await self.session.execute(
            select(ExchangeRate).where(
                and_(
                    ExchangeRate.date == date,
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                )
            )
        )
        exchange_rate = existing.scalar_one_or_none()

        if exchange_rate:
            exchange_rate.rate = rate
            if source:
                exchange_rate.source = source
        else:
            exchange_rate = ExchangeRate(
                date=date,
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                source=source,
            )
            self.session.add(exchange_rate)

        await self.session.flush()
        return exchange_rate

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        as_of_date: date | None = None,
    ) -> Decimal | None:
        if as_of_date is None:
            as_of_date = date.today()

        result = await self.session.execute(
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.date <= as_of_date,
                )
            )
            .order_by(ExchangeRate.date.desc())
            .limit(1)
        )
        rate_obj = result.scalar_one_or_none()
        return rate_obj.rate if rate_obj else None

    async def list_all(
        self,
        from_currency: str | None = None,
        to_currency: str | None = None,
    ) -> list[ExchangeRate]:
        query = select(ExchangeRate).order_by(
            ExchangeRate.date.desc(),
            ExchangeRate.from_currency,
            ExchangeRate.to_currency,
        )

        if from_currency:
            query = query.where(ExchangeRate.from_currency == from_currency)
        if to_currency:
            query = query.where(ExchangeRate.to_currency == to_currency)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, exchange_rate_id: str) -> bool:
        result = await self.session.execute(
            select(ExchangeRate).where(ExchangeRate.id == exchange_rate_id)
        )
        rate = result.scalar_one_or_none()
        if rate:
            await self.session.delete(rate)
            await self.session.flush()
            return True
        return False
