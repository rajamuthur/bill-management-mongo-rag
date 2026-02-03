from datetime import datetime


def insert_bill(
    bill_id: str,
    user_id: str,
    extracted: dict,
    raw_text: str,
    file_path: str,
    db
):
    doc = {
        "_id": bill_id,
        "user_id": user_id,
        **extracted,
        "raw_text": raw_text,
        "file_path": file_path,
        "source": "upload",
        "created_at": datetime.utcnow()
    }

    db.bills.insert_one(doc)
