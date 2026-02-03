from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator


class Relative(BaseModel):
    unit: Literal["day", "month", "year"]
    offset: int


class DatePart(BaseModel):
    # Absolute
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None

    # Relative
    relative: Optional[Relative] = None

    @model_validator(mode="after")
    def validate_date_part(self):
        # Case 1: Pure relative → valid
        if self.relative and not any([self.year, self.month, self.day]):
            return self

        # Case 2: Hybrid (relative + month/day) → valid
        if self.relative:
            return self

        # Case 3: Pure absolute → must have year
        if self.year is None:
            raise ValueError("Absolute date must include at least year")

        return self



class TimeRange(BaseModel):
    type: Literal["ABSOLUTE", "RELATIVE", "NONE"]
    from_: Optional[DatePart] = Field(None, alias="from")
    to: Optional[DatePart] = None
    granularity: Literal["day", "month", "year"]

    model_config = {
        "populate_by_name": True
    }
