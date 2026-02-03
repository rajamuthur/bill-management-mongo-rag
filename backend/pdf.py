import os
import pytesseract
from pdf2image import convert_from_path
from dotenv import load_dotenv
load_dotenv()
import shutil
print(shutil.which("pdfinfo"))

# TESSERACT_CMD = os.getenv("TESSERACT_CMD")
# POPPLER_PATH = os.getenv("POPPLER_PATH")

# if TESSERACT_CMD:
#     pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Explicit paths (Windows-safe)
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

POPPLER_PATH = r"C:\tools\poppler-24.08.0\Library\bin"

def extract_text(file_path: str) -> str:
    print("[EXTRACT TEXT]", file_path)

    if file_path.lower().endswith(".pdf"):
        pages = convert_from_path(
            file_path,
            dpi=300,
            poppler_path=POPPLER_PATH
        )
        return "\n".join(
            pytesseract.image_to_string(p, lang="eng")
            for p in pages
        )

    return pytesseract.image_to_string(file_path, lang="eng")


pdf_path = r"D:\workout\langchain\learning\RAG\bill-management-rag-mongo\frontend\uploads\generated_pdf.pdf"
result = extract_text(pdf_path)
print(result)