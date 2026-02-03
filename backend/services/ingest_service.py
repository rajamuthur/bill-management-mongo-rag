# from services.file_loader import extract_text
# from services.bill_llm import extract_bill_structured
from utils.ocr_utils import extract_text, normalize_for_mongo
from chains.bill_extract_chain import extract_bill_structured
from services.vector_service import insert_bill_vector
# from services.vector_store import upsert_bill_vector
from db.mongodb import get_db

def handle_bill_ingestion(user_id: str,
    file_path: str | None,
    manual_bill: dict | None,
    metadata: dict):
    text = None
    print("[INGEST BILL]", user_id, file_path, manual_bill is not None, metadata)
     # ---------- CASE 1: File-based ingestion ----------
    # ---------- CASE 1: File-based ingestion ----------
    if file_path:
        text = extract_text(file_path)
        bill = extract_bill_structured(text=text)

    # ---------- CASE 2: Manual bill entry ----------
    elif manual_bill:
        bill = manual_bill
        text = f"{bill.get('vendor', '')} {bill.get('category', '')} {bill.get('total_amount', '')}"
    else:
        raise ValueError("Either file_path or manual_bill must be provided")

    bill = normalize_for_mongo(bill)

    # 🔴 CHECK MISSING FIELDS
    # If it's a manual bill, we trust the user input? Usually manual entry form enforces required fields.
    # But for file upload, we need to check.
    if file_path:
        # If OCR completely failed (empty text) or Extraction skipped (empty dict)
        if not text or not text.strip() or not bill:
             return {
                "status": "extraction_failed",
                "message": "Could not extract any text from the document. The image might be too blurry or contain no readable text.",
                "file_path": file_path
            }
            
        missing_fields = [] 
        required_fields = ["vendor", "category", "total_amount", "payment_method"]
        for field in required_fields:
            if not bill.get(field):
                missing_fields.append(field)

        if missing_fields:
            return {
                "status": "requires_confirmation",
                "extracted": bill,
                "raw_text": text,
                "file_path": file_path,
                "missing_fields": missing_fields
            }

    bill_doc = {
        **bill,
        "user_id": user_id,
        "source_file": file_path
    }

    db = get_db()
    bills_col = db.bills

    result = bills_col.insert_one(bill_doc)

    insert_bill_vector(
        text=text,
        user_id=user_id,
        bill_id=str(result.inserted_id),
    )

    return {"status": "ok", "bill_id": str(result.inserted_id)}
