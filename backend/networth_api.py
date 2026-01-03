from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from database.session import get_session
from database.models import AccountType
from database.repository import AccountRepository, BalanceRepository, ExchangeRateRepository

router = APIRouter(prefix="/networth", tags=["networth"])


class AccountCreate(BaseModel):
    name: str = Field(..., description="Full account name (e.g., 'Assets:Bank:Savings')")
    currency: str = Field(default="USD", description="Account currency")
    description: Optional[str] = Field(None, description="Account description/notes")
    open_date: date_type = Field(default_factory=date_type.today, description="Account opening date")


class AccountResponse(BaseModel):
    id: str
    name: str
    account_type: str
    currency: str
    description: Optional[str]
    open_date: date_type
    close_date: Optional[date_type]
    is_active: bool
    current_balance: Optional[Decimal] = None

    class Config:
        from_attributes = True


class BalanceCreate(BaseModel):
    account_id: str
    amount: Decimal
    currency: str
    date: date_type = Field(default_factory=date_type.today)


class BalanceResponse(BaseModel):
    id: str
    account_id: str
    account_name: str
    account_type: str
    amount: Decimal
    currency: str
    date: date_type

    class Config:
        from_attributes = True


class NetWorthSummary(BaseModel):
    currency: str
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal


class NetWorthResponse(BaseModel):
    as_of_date: date_type
    by_currency: list[NetWorthSummary]
    entries: list[BalanceResponse]


class ExchangeRateCreate(BaseModel):
    from_currency: str
    to_currency: str
    rate: Decimal
    date: date_type = Field(default_factory=date_type.today)
    source: Optional[str] = None


class ExchangeRateResponse(BaseModel):
    id: str
    from_currency: str
    to_currency: str
    rate: Decimal
    date: date_type
    source: Optional[str]

    class Config:
        from_attributes = True


@router.get("/accounts", response_model=list[AccountResponse])
async def list_networth_accounts(
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)
    balance_repo = BalanceRepository(session)

    accounts = []
    for account_type in [AccountType.ASSETS, AccountType.LIABILITIES]:
        accounts.extend(
            await account_repo.list_all(account_type=account_type, is_active=True)
        )

    balances = await balance_repo.get_latest_balances()
    balance_map = {
        (entry.account_id, entry.currency): entry.amount
        for entry in balances
    }

    response = []
    for account in accounts:
        account_dict = {
            "id": account.id,
            "name": account.name,
            "account_type": account.account_type.value,
            "currency": account.currency,
            "description": account.description,
            "open_date": account.open_date,
            "close_date": account.close_date,
            "is_active": account.is_active,
            "current_balance": balance_map.get((account.id, account.currency)),
        }
        response.append(AccountResponse(**account_dict))

    return response


@router.post("/accounts", response_model=AccountResponse)
async def create_networth_account(
    account_data: AccountCreate,
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)

    first_component = account_data.name.split(":")[0]
    if first_component not in ["Assets", "Liabilities"]:
        raise HTTPException(
            status_code=400,
            detail="Account name must start with 'Assets:' or 'Liabilities:'"
        )

    try:
        account = await account_repo.create(
            name=account_data.name,
            open_date=account_data.open_date,
            currency=account_data.currency,
            description=account_data.description,
        )
        await session.commit()

        return AccountResponse(
            id=account.id,
            name=account.name,
            account_type=account.account_type.value,
            currency=account.currency,
            description=account.description,
            open_date=account.open_date,
            close_date=account.close_date,
            is_active=account.is_active,
            current_balance=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/balances", response_model=BalanceResponse)
async def create_balance(
    balance_data: BalanceCreate,
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)
    balance_repo = BalanceRepository(session)

    account = await account_repo.get_by_id(balance_data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.account_type not in [AccountType.ASSETS, AccountType.LIABILITIES]:
        raise HTTPException(
            status_code=400,
            detail="Can only set balances for Assets or Liabilities accounts"
        )

    balance = await balance_repo.create_or_update(
        account_id=balance_data.account_id,
        date=balance_data.date,
        amount=balance_data.amount,
        currency=balance_data.currency,
    )
    await session.commit()

    return BalanceResponse(
        id=balance.id,
        account_id=account.id,
        account_name=account.name,
        account_type=account.account_type.value,
        amount=balance.amount,
        currency=balance.currency,
        date=balance.date,
    )


@router.get("/summary", response_model=NetWorthResponse)
async def get_networth_summary(
    as_of_date: Optional[date_type] = None,
    session: AsyncSession = Depends(get_session),
):
    if as_of_date is None:
        as_of_date = date_type.today()

    balance_repo = BalanceRepository(session)

    balances = await balance_repo.get_latest_balances(as_of_date=as_of_date)

    balance_responses = []
    for balance in balances:
        balance_responses.append(
            BalanceResponse(
                id=balance.id,
                account_id=balance.account.id,
                account_name=balance.account.name,
                account_type=balance.account.account_type.value,
                amount=balance.amount,
                currency=balance.currency,
                date=balance.date,
            )
        )

    summary_by_currency = {}
    for balance in balances:
        currency = balance.currency
        if currency not in summary_by_currency:
            summary_by_currency[currency] = {
                "total_assets": Decimal(0),
                "total_liabilities": Decimal(0),
            }

        if balance.account.account_type == AccountType.ASSETS:
            summary_by_currency[currency]["total_assets"] += balance.amount
        elif balance.account.account_type == AccountType.LIABILITIES:
            summary_by_currency[currency]["total_liabilities"] += balance.amount

    summaries = []
    for currency, totals in summary_by_currency.items():
        summaries.append(
            NetWorthSummary(
                currency=currency,
                total_assets=totals["total_assets"],
                total_liabilities=totals["total_liabilities"],
                net_worth=totals["total_assets"] - totals["total_liabilities"],
            )
        )

    summaries.sort(key=lambda x: x.currency)

    return NetWorthResponse(
        as_of_date=as_of_date,
        by_currency=summaries,
        entries=balance_responses,
    )


@router.delete("/balances/{balance_id}")
async def delete_balance(
    balance_id: str,
    session: AsyncSession = Depends(get_session),
):
    balance_repo = BalanceRepository(session)

    deleted = await balance_repo.delete(balance_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Balance entry not found")

    await session.commit()
    return {"message": "Balance entry deleted successfully"}


@router.post("/exchange-rates", response_model=ExchangeRateResponse)
async def create_exchange_rate(
    rate_data: ExchangeRateCreate,
    session: AsyncSession = Depends(get_session),
):
    rate_repo = ExchangeRateRepository(session)

    rate = await rate_repo.create_or_update(
        date=rate_data.date,
        from_currency=rate_data.from_currency,
        to_currency=rate_data.to_currency,
        rate=rate_data.rate,
        source=rate_data.source,
    )
    await session.commit()

    return ExchangeRateResponse(
        id=rate.id,
        from_currency=rate.from_currency,
        to_currency=rate.to_currency,
        rate=rate.rate,
        date=rate.date,
        source=rate.source,
    )


@router.get("/exchange-rates", response_model=list[ExchangeRateResponse])
async def list_exchange_rates(
    from_currency: Optional[str] = None,
    to_currency: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    rate_repo = ExchangeRateRepository(session)

    rates = await rate_repo.list_all(
        from_currency=from_currency,
        to_currency=to_currency,
    )

    return [
        ExchangeRateResponse(
            id=rate.id,
            from_currency=rate.from_currency,
            to_currency=rate.to_currency,
            rate=rate.rate,
            date=rate.date,
            source=rate.source,
        )
        for rate in rates
    ]


@router.get("/exchange-rates/{from_currency}/{to_currency}")
async def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    as_of_date: Optional[date_type] = None,
    session: AsyncSession = Depends(get_session),
):
    rate_repo = ExchangeRateRepository(session)

    rate = await rate_repo.get_rate(
        from_currency=from_currency,
        to_currency=to_currency,
        as_of_date=as_of_date,
    )

    if rate is None:
        raise HTTPException(
            status_code=404,
            detail=f"No exchange rate found for {from_currency}/{to_currency}"
        )

    return {"from_currency": from_currency, "to_currency": to_currency, "rate": rate}


@router.delete("/exchange-rates/{rate_id}")
async def delete_exchange_rate(
    rate_id: str,
    session: AsyncSession = Depends(get_session),
):
    rate_repo = ExchangeRateRepository(session)

    deleted = await rate_repo.delete(rate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Exchange rate not found")

    await session.commit()
    return {"message": "Exchange rate deleted successfully"}
