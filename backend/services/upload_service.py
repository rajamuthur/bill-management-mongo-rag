import uuid
from utils.file_utils import save_file
from utils.ocr_utils import extract_text, normalize_for_mongo
from chains.bill_extract_chain import extract_bill_structured
from services.bill_service import insert_bill
from services.vector_service import insert_bill_vector


async def handle_bill_upload(
    file,
    user_id: str,
    category: str,
    amount: float,
    db
):
    bill_id = str(uuid.uuid4())

    # 1️⃣ Save file
    file_path = save_file(file, user_id, bill_id)

    # 2️⃣ OCR / text extraction
    raw_text = extract_text(file_path)

    # 3️⃣ LLM bill extraction
    extracted = extract_bill_structured(raw_text)

    # 4️⃣ Override user provided fields
    if category:
        extracted["category"] = category
    if amount:
        extracted["total_amount"] = amount

    # 🔴 CHECK MISSING FIELDS
    missing_fields = []
    # Major details: vendor, date (maybe?), category, total_amount, payment_method
    # The prompt specifically mentioned: vendor name, type (category), total amount, mode of payment
    required_fields = ["vendor", "category", "total_amount", "payment_method"]
    
    for field in required_fields:
        if not extracted.get(field):
            missing_fields.append(field)

    # If missing fields, return for confirmation (do not save yet)
    if missing_fields:
        return {
            "status": "requires_confirmation",
            "bill_id": bill_id,
            "file_path": file_path,
            "extracted": extracted,
            "raw_text": raw_text,
            "missing_fields": missing_fields
        }

    # 5️⃣ & 6️⃣ Proceed to Save
    return await save_confirmed_bill(
        bill_id=bill_id,
        user_id=user_id,
        extracted=extracted,
        raw_text=raw_text,
        file_path=file_path,
        db=db
    )


async def save_confirmed_bill(
    bill_id: str,
    user_id: str,
    extracted: dict,
    raw_text: str,
    file_path: str,
    db
):
    # 5️⃣ Mongo insert
    normalized = normalize_for_mongo(extracted)
    insert_bill(
        bill_id=bill_id,
        user_id=user_id,
        extracted=normalized,
        raw_text=raw_text,
        file_path=file_path,
        db=db
    )

    # 6️⃣ Vector insert
    insert_bill_vector(
        bill_id=bill_id,
        user_id=user_id,
        text=raw_text
    )

    return {"status": "ok", "bill_id": bill_id}
