from pydantic import BaseModel
from typing import Any, Optional, Dict

class IngestRequest(BaseModel):
    user_id: str
    # Optional file ingestion
    file_path: Optional[str] = None

    # Manual bill data (optional)
    bill: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Optional[float | str]]
