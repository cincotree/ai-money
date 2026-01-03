from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from accounting.store import load, persist, first_link
from accounting import store
from accounting.catagory import CATEGORIES
from accounting.cc import convert_fidelity_cc_to_beancount
from accounting.accounts import account_directives
from accounting.transactions import build_transaction_dicts
from datetime import datetime
import pandas as pd
from fastapi import UploadFile
import os
import traceback

router = APIRouter()

class Transaction(BaseModel):
    id: str
    date: str
    description: str
    postings: List[Dict]
    from_account: str  # Credit account
    to_account: str  # Debit account
    links: List[str]

@router.post("/upload")
async def upload_file(file: UploadFile):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("/tmp", exist_ok=True)

        # Determine file type from extension
        file_extension = os.path.splitext(file.filename)[1].lower()

        # Save the uploaded file
        if file_extension == '.pdf':
            filename = f"/tmp/upload_{timestamp}.pdf"
        else:
            filename = f"/tmp/upload_{timestamp}.csv"

        content = await file.read()
        with open(filename, "wb") as f:
            f.write(content)

        # Process based on file type
        currency = "USD"
        if file_extension == '.pdf':
            raise HTTPException(status_code=400, detail="PDF upload not currently supported")
        else:
            sample_txns = pd.read_csv(filename)

        # Convert to beancount format
        beancount_txns = convert_fidelity_cc_to_beancount(sample_txns)
        all_entries = account_directives + beancount_txns
        beancount_filepath = f"/tmp/transactions_{timestamp}.beancount"
        store.persist(all_entries, beancount_filepath)
        transactions = load(beancount_filepath)

        return {
            "beancount_filepath": beancount_filepath,
            'categories': CATEGORIES,
            'transactions': build_transaction_dicts(transactions),
            "message": f"File uploaded successfully as {filename}",
            "file_type": "PDF" if file_extension == '.pdf' else "CSV",
            "currency": currency
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def healthcheck():
    return {"status": "ok"}

