from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional, List, Dict, Any
class BillItem(BaseModel):
    # Accept both "description" and "name"
    description: str = Field(..., alias="name")

    amount: Optional[float] = None
    quantity: Optional[float] = None
    rate: Optional[float] = None
    gst: Optional[float] = None

    # Store anything unexpected
    extra_data: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "populate_by_name": True,
        "extra": "allow"
    }

    @field_validator("gst", mode="before")
    @classmethod
    def parse_gst(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return float(v.replace("%", "").strip())
        return v

class BillExtract(BaseModel):
    vendor: Optional[str] = None
    bill_date: Optional[date] = None
    category: Optional[str] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    currency: Optional[str] = "INR"
    items: Optional[list[BillItem]] = None

    extra_data: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "extra": "allow"
    }
