# PostgreSQL Accounting System

A Beancount-compatible double-entry accounting system backed by PostgreSQL.

## Core Concepts

### Account Types
Following Beancount conventions:
- **Assets** - Bank accounts, cash, investments
- **Liabilities** - Credit cards, loans
- **Equity** - Opening balances, retained earnings
- **Income** - Salary, interest, dividends
- **Expenses** - Food, transport, utilities

### Hierarchical Accounts
Accounts use colon-separated names for hierarchy:
```
Assets:Bank:Checking
Expenses:Food:Groceries
Liabilities:CreditCard:Visa
```

### Double-Entry Transactions
Every transaction must balance - debits equal credits:
```
2024-03-15 * "Whole Foods" "Grocery shopping"
  Expenses:Food:Groceries    52.50 USD
  Assets:Bank:Checking      -52.50 USD
```

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `accounts` | Chart of accounts with type, currency, open/close dates |
| `transactions` | Transaction headers with date, payee, narration |
| `postings` | Individual debit/credit entries linking transactions to accounts |
| `balances` | Balance assertions for account verification |
| `transaction_links` | Links connecting related transactions (^link syntax) |
| `transaction_tags` | Tags for categorizing transactions (#tag syntax) |

## Usage

### Creating Accounts

```python
from database.repository import AccountRepository
from database.session import session_context
from datetime import date

async with session_context() as session:
    repo = AccountRepository(session)

    account = await repo.create(
        name="Assets:Bank:Checking",
        open_date=date(2024, 1, 1),
        currency="USD",
        description="Main checking account"
    )
```

### Creating Transactions

```python
from database.repository import TransactionRepository
from decimal import Decimal

async with session_context() as session:
    repo = TransactionRepository(session)

    txn = await repo.create(
        date=date(2024, 3, 15),
        narration="Grocery shopping",
        payee="Whole Foods",
        postings=[
            {
                "account_id": expense_account.id,
                "amount": Decimal("52.50"),
                "currency": "USD"
            },
            {
                "account_id": checking_account.id,
                "amount": Decimal("-52.50"),
                "currency": "USD"
            }
        ],
        tags=["groceries"],
        links=["shopping-march-2024"]
    )
```

### Auto-Balance

One posting can omit the amount for automatic balancing:

```python
txn = await repo.create(
    date=date(2024, 3, 15),
    narration="Restaurant dinner",
    postings=[
        {"account_id": expense_id, "amount": Decimal("75.00")},
        {"account_id": credit_card_id, "amount": None}  # Auto-balanced to -75.00
    ]
)
```

### Querying

```python
# Get account balance
balance = await account_repo.get_balance(
    account_id,
    as_of_date=date(2024, 3, 31)
)

# List transactions by date range
transactions = await txn_repo.list_by_date_range(
    start_date=date(2024, 3, 1),
    end_date=date(2024, 3, 31),
    account_id=checking_account.id
)

# Search transactions
results = await txn_repo.search(
    query_text="restaurant",
    tag="business",
    min_amount=Decimal("50.00")
)

# Get account statement with running balance
statement = await txn_repo.get_account_statement(
    account_id=checking_account.id,
    start_date=date(2024, 3, 1),
    end_date=date(2024, 3, 31)
)
```

## Configuration

Set environment variables or create `.env`:

```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aimoney
```

**Connection URL**:
```
postgresql://postgres:postgres@localhost:5432/aimoney
```

## Running Tests

Tests require PostgreSQL and automatically create/drop a test database:

```bash
uv run pytest tests/ -v
```

- Test database: `aimoney_test` (created at session start, dropped at session end)
- Each test gets fresh tables (created/dropped per test)
- Requires PostgreSQL running with credentials from `.env` or defaults

## Key Features

- Full double-entry accounting with balance validation
- Multiple currencies per posting
- Transaction tags and links for organization
- Account hierarchy support
- Balance assertions
- Account statements with running balance
- Async/await throughout for performance
