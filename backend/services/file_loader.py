from pathlib import Path

def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(p.page_content for p in reader.pages)

    if ext in [".txt"]:
        return Path(file_path).read_text(encoding="utf-8")

    raise ValueError(f"Unsupported file type: {ext}")
