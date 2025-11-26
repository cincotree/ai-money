"""
SQLAlchemy models for Beancount-compatible double-entry accounting.

This module defines the database schema for:
- Accounts (chart of accounts with hierarchy support)
- Transactions (transaction headers with metadata)
- Postings (individual debit/credit entries)
- Balances (balance assertions)
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class AccountType(enum.Enum):
    """Account types following Beancount conventions."""
    ASSETS = "Assets"
    LIABILITIES = "Liabilities"
    EQUITY = "Equity"
    INCOME = "Income"
    EXPENSES = "Expenses"


class Account(Base):
    """
    Account in the chart of accounts.

    Supports hierarchical account names like 'Assets:Bank:Checking'.
    """
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    open_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    postings: Mapped[list["Posting"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    balances: Mapped[list["Balance"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account(name={self.name}, type={self.account_type.value})>"

    @property
    def parent_name(self) -> str | None:
        """Get parent account name (e.g., 'Assets:Bank' for 'Assets:Bank:Checking')."""
        parts = self.name.rsplit(":", 1)
        return parts[0] if len(parts) > 1 else None

    @property
    def short_name(self) -> str:
        """Get the last component of the account name."""
        return self.name.rsplit(":", 1)[-1]


class Transaction(Base):
    """
    Transaction header containing metadata.

    A transaction contains multiple postings that must balance to zero.
    """
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Transaction flag (* for complete, ! for incomplete)
    flag: Mapped[str] = mapped_column(String(1), default="*", nullable=False)
    payee: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    postings: Mapped[list["Posting"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    links: Mapped[list["TransactionLink"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    tags: Mapped[list["TransactionTag"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_transactions_date_payee", "date", "payee"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(date={self.date}, narration={self.narration[:50]})>"

    @property
    def is_balanced(self) -> bool:
        """Check if transaction postings balance to zero."""
        total = sum(p.amount for p in self.postings if p.amount is not None)
        return abs(total) < Decimal("0.001")


class Posting(Base):
    """
    Individual posting (debit/credit) within a transaction.

    Each posting represents a change to an account balance.
    """
    __tablename__ = "postings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    # Foreign keys
    transaction_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    # Amount (positive for debits, negative for credits in expense/asset accounts)
    # Can be None if auto-computed to balance
    amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )
    # Currency
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    # Cost basis (for investments)
    cost_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )
    cost_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    cost_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Price (for currency conversions)
    price_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )
    price_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # Posting order within transaction
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="postings")
    account: Mapped["Account"] = relationship(back_populates="postings")

    __table_args__ = (
        Index("ix_postings_account_id", "account_id"),
        Index("ix_postings_transaction_id", "transaction_id"),
    )

    def __repr__(self) -> str:
        return f"<Posting(account={self.account_id}, amount={self.amount} {self.currency})>"


class Balance(Base):
    """
    Balance assertion for an account on a specific date.

    Used to verify that the account balance matches expectations.
    """
    __tablename__ = "balances"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    # Foreign key to account
    account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    # Balance assertion date
    date: Mapped[date] = mapped_column(Date, nullable=False)
    # Expected balance amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False
    )
    # Currency
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    # Whether the assertion passed
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="balances")

    __table_args__ = (
        UniqueConstraint("account_id", "date", "currency", name="uq_balance_account_date_currency"),
        Index("ix_balances_account_date", "account_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<Balance(account={self.account_id}, date={self.date}, amount={self.amount})>"


class TransactionLink(Base):
    """
    Link identifier for a transaction (Beancount ^link syntax).

    Links connect related transactions across time.
    """
    __tablename__ = "transaction_links"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    transaction_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    # Link value (without the ^ prefix)
    link: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="links")

    __table_args__ = (
        UniqueConstraint("transaction_id", "link", name="uq_transaction_link"),
    )


class TransactionTag(Base):
    """
    Tag for a transaction (Beancount #tag syntax).

    Tags categorize transactions.
    """
    __tablename__ = "transaction_tags"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    transaction_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    # Tag value (without the # prefix)
    tag: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="tags")

    __table_args__ = (
        UniqueConstraint("transaction_id", "tag", name="uq_transaction_tag"),
    )
