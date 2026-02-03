from pydantic import BaseModel
from app import query_router
from fastapi import FastAPI, UploadFile, File, Form
from services.ingest_service import handle_bill_ingestion
from services.upload_service import handle_bill_upload, save_confirmed_bill
from db.mongodb import get_db
from schemas.ingest import IngestRequest

app = FastAPI()


class QueryRequest(BaseModel):
    user_id: str
    query: str

@app.post("/query")
def query_handler(req: QueryRequest):
    result = query_router(req.query, req.user_id)
    return {"result": result}

@app.post("/ingest")
def ingest_handler(req: IngestRequest):
    result = handle_bill_ingestion(
        user_id=req.user_id,
        file_path=req.file_path,
        manual_bill=req.bill,
        metadata=req.metadata
    )

    return result

class ConfirmRequest(BaseModel):
    bill_id: str
    user_id: str
    extracted: dict
    raw_text: str
    file_path: str

@app.post("/ingest_")
async def ingest_handler_(
    file: UploadFile = File(...),
    category: str = Form(None),
    amount: float = Form(None),
    user_id: str = Form("u1")  # temp
):
    db = get_db()

    result = await handle_bill_upload(
        file=file,
        user_id=user_id,
        category=category,
        amount=amount,
        db=db
    )
    
    # Can allow "status": "requires_confirmation" to pass through
    return result

@app.post("/ingest/confirm")
async def confirm_handler(req: ConfirmRequest):
    db = get_db()
    return await save_confirmed_bill(
        bill_id=req.bill_id,
        user_id=req.user_id,
        extracted=req.extracted,
        raw_text=req.raw_text,
        file_path=req.file_path,
        db=db
    )

from fastapi import Query
from typing import Optional
import re

@app.get("/bills")
def get_bills(
    user_id: str = Query("u1"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = Query("bill_date"),
    sort_order: str = Query("desc"),
    search: Optional[str] = None
):
    db = get_db()
    query = {"user_id": user_id}

    if search:
        # Simple regex search on vendor or item descriptions
        # Note: This might be slow on large datasets without indexes
        query["$or"] = [
            {"vendor": {"$regex": re.escape(search), "$options": "i"}},
            {"items.description": {"$regex": re.escape(search), "$options": "i"}},
            {"category": {"$regex": re.escape(search), "$options": "i"}}
        ]

    # Sort direction
    mongo_sort_order = -1 if sort_order.lower() == "desc" else 1
    
    # Calculate skip
    skip = (page - 1) * page_size

    total_count = db.bills.count_documents(query)
    cursor = db.bills.find(query).sort(sort_by, mongo_sort_order).skip(skip).limit(page_size)
    
    bills = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        bills.append(doc)

    return {
        "data": bills,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    }
