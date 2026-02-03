class BillExtract(BaseModel):
    vendor: str
    bill_date: date
    category: str
    total_amount: float
    tax_amount: float | None
    currency: str
    items: list[str] | None
