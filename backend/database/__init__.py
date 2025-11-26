"""
Database package for PostgreSQL-backed accounting system.

This package provides:
- SQLAlchemy models for double-entry accounting (Beancount-compatible)
- Async database session management
- Repository pattern for CRUD operations
"""

from database.config import get_settings, Settings
from database.models import (
    Account,
    AccountType,
    Transaction,
    Posting,
    Balance,
    TransactionLink,
    TransactionTag,
)
from database.repository import AccountRepository, TransactionRepository
from database.session import get_session, init_db, AsyncSessionLocal

__all__ = [
    # Config
    "get_settings",
    "Settings",
    # Session
    "get_session",
    "init_db",
    "AsyncSessionLocal",
    # Models
    "Account",
    "AccountType",
    "Transaction",
    "Posting",
    "Balance",
    "TransactionLink",
    "TransactionTag",
    # Repositories
    "AccountRepository",
    "TransactionRepository",
]
