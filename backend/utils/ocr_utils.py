import pytesseract
import shutil
import os
from pdf2image import convert_from_path

# 1. Try to find tesseract in PATH
tesseract_cmd = shutil.which("tesseract")

# 2. If not found, try common Windows paths
if not tesseract_cmd:
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            tesseract_cmd = p
            break

if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    print(f"[OCR CONFIG] Tesseract found at: {tesseract_cmd}")
else:
    print("[OCR ERROR] Tesseract not found in PATH or common locations.")

# POPPLER CONFIG
# Try to find valid poppler path or use hardcoded as fallback
POPPLER_PATH = r"C:\tools\poppler-24.08.0\Library\bin"

def extract_text(file_path: str) -> str:
    print(f"[EXTRACT TEXT] Processing: {file_path}")
    
    text = ""
    try:
        if file_path.lower().endswith(".pdf"):
            # Check poppler
            if not os.path.exists(POPPLER_PATH) and not shutil.which("pdftoppm"):
                 print(f"[OCR WARNING] Poppler not found at {POPPLER_PATH}")

            pages = convert_from_path(
                file_path,
                dpi=300,
                poppler_path=POPPLER_PATH if os.path.exists(POPPLER_PATH) else None
            )
            text = "\n".join(
                pytesseract.image_to_string(p, lang="eng")
                for p in pages
            )
        else:
            text = pytesseract.image_to_string(file_path, lang="eng")
    except Exception as e:
        print(f"[OCR FAILED] Error extracting text: {e}")
        return ""
        
    print(f"[EXTRACT TEXT] Result Length: {len(text)} characters")
    return text

from datetime import datetime, date, time, timezone

def normalize_for_mongo_dynamic(data: dict) -> dict:
    for k, v in data.items():
        if isinstance(v, date) and not isinstance(v, datetime):
            # Convert date → datetime at midnight
            data[k] = datetime.combine(v, time.min)

        elif isinstance(v, list):
            data[k] = [normalize_for_mongo_dynamic(i) if isinstance(i, dict) else i for i in v]

        elif isinstance(v, dict):
            data[k] = normalize_for_mongo_dynamic(v)

    return data


from datetime import datetime
from typing import Dict, Any

def parse_date(value):
    if value is None:
        return None

    # Already datetime → force UTC
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)

    # date → convert to datetime
    if isinstance(value, date):
        return datetime(
            value.year,
            value.month,
            value.day,
            0, 0, 0,
            tzinfo=timezone.utc
        )

    # string → parse
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return None


def parse_float(value):
    try:
        return float(value)
    except Exception:
        return None


def normalize_items(items):
    normalized = []

    for item in items or []:
        normalized.append({
            "description": item.get("description") or item.get("name"),
            "quantity": parse_float(item.get("quantity")),
            "rate": parse_float(item.get("rate")),
            "amount": parse_float(item.get("amount")),
            "gst": item.get("gst"),
            "tax": parse_float(item.get("tax")),
            "extra_data": item.get("extra_data", {})
        })

    return normalized

def sanitize_raw(bill: dict) -> dict:
    clean = {}
    for k, v in bill.items():
        if isinstance(v, date) and not isinstance(v, datetime):
            clean[k] = parse_date(v)
        else:
            clean[k] = v
    return clean

def normalize_for_mongo(bill: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts LLM/manual bill output into canonical Mongo format
    """
    print("[RAW BILL]", bill)
    normalized = {
        # ---------- Core ----------
        "vendor": bill.get("vendor"),
        "bill_no": bill.get("bill_no"),
        "bill_date": parse_date(bill.get("bill_date")),
        "bill_time": bill.get("bill_time"),
        "category": bill.get("category"),
        "customer": bill.get("customer"),

        # ---------- Contact ----------
        "address": bill.get("address"),
        "phone": bill.get("phone"),
        "gst": bill.get("gst"),

        # ---------- Money ----------
        "currency": bill.get("currency", "INR"),
        "subtotal": parse_float(bill.get("subtotal")),
        "tax_amount": parse_float(
            bill.get("tax_amount") or bill.get("total_tax")
        ),
        "total_amount": parse_float(bill.get("total_amount")),

        # ---------- Payment ----------
        "payment_method": bill.get("payment_method"),

        # ---------- Items ----------
        "items": normalize_items(
            bill.get("items") or bill.get("line_items")
        ),

        # ---------- OCR leftovers ----------
        "extra_data": bill.get("extra_data", {}),

        # ---------- Raw ----------
        "raw": sanitize_raw(bill),  # raw bill
    }

    print("[NORMALIZED BILL]", normalized)
    print("[ORIGINAL BILL]", bill)

    return normalized

