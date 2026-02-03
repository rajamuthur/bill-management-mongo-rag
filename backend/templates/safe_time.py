from datetime import datetime, timedelta, timezone
import calendar
import re

from templates.time_range import TimeRange, DatePart
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from helper import groqllm

# -------------------------------
# Parser
# -------------------------------
parser = PydanticOutputParser(pydantic_object=TimeRange)

time_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You extract time ranges from user queries.

STRICT RULES:
- Output VALID JSON only
- No explanations
- No comments
- No markdown
- No extra text
- If unknown, return type NONE
- Do NOT calculate real dates
- Words like "recent", "latest", "earlier", "long ago" are ambiguous.
If no explicit duration is given, return type NONE.
For phrases like "last N months":
- Include N completed months
- Exclude the current month
- For a specific single date (e.g., "Jan 19 2026"), set 'from' to that date and 'to' to null.
- Do not assume a range starting from the 1st of the month unless specified (e.g., "since", "from").
- If a specific day is mentioned without a starting point (e.g., 'on Jan 19' or 'in Jan 19'), set 'from' to that date and 'to' to null. Do not assume the range starts at the beginning of the month.
"""),

    # -------- FEW SHOT --------
    ("human", "Total bill for last month"),
    ("assistant", """
{{
  "type": "RELATIVE",
  "from": {{ "relative": {{ "unit": "month", "offset": -1 }} }},
  "to": {{ "relative": {{ "unit": "day", "offset": 0 }} }},
  "granularity": "month"
}}
"""),
    ("human", "Total bill for last 3 month"),
    ("assistant", """
{{
  "type": "RELATIVE",
  "from": {{ "relative": {{ "unit": "month", "offset": -3 }} }},
  "to": {{ "relative": {{ "unit": "month", "offset": -1 }} }},
  "granularity": "month"
}}
"""),

("human", "Total bill for last november"),
("assistant", """
{{
  "type": "RELATIVE",
  "from": {{ "relative": {{ "unit": "year", "offset": -1 }}, "month": 11 }},
  "to": {{ "relative": {{ "unit": "year", "offset": -1 }}, "month": 11 }},
  "granularity": "month"
}}
"""),

    ("human", "Bills between sept 2024 and nov 2024"),
    ("assistant", """
{{
  "type": "ABSOLUTE",
  "from": {{ "year": 2024, "month": 9 }},
  "to": {{ "year": 2024, "month": 11 }},
  "granularity": "month"
}}
"""),

    ("human", "from 9th sept 2024 to 10 oct 2025"),
    ("assistant", """
{{
  "type": "ABSOLUTE",
  "from": {{ "year": 2024, "month": 9, "day": 9 }},
  "to": {{ "year": 2025, "month": 10, "day": 10 }},
  "granularity": "day"
}}
"""),

    ("human", "all time"),
    ("assistant", """
{{
  "type": "NONE",
  "from": null,
  "to": null,
  "granularity": "year"
}}
"""),

    # -------- USER --------
    ("human", "{query}")
]).partial(format_instructions=parser.get_format_instructions())


# -------------------------------
# Chain
# -------------------------------
time_range_chain = time_prompt | groqllm | parser

# -------------------------------
# Resolver
# -------------------------------

def resolve_relative_simple(part: DatePart, is_start: bool):
    now = datetime.now(timezone.utc)

    if part.relative.unit == "day":
        return now + timedelta(days=part.relative.offset)

    if part.relative.unit == "year":
        year = now.year + part.relative.offset
        if is_start:
            return datetime(year, 1, 1, tzinfo=timezone.utc)
        return datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    raise ValueError("Unsupported relative unit")

def resolve_relative_month(tr: TimeRange):
    now = datetime.now(timezone.utc)
    base_year, base_month = now.year, now.month

    offset = tr.from_.relative.offset

    start_year, start_month = month_shift(base_year, base_month, offset)
    start, _ = month_bounds(start_year, start_month)

    # last month → end of same month
    # last N months → end of previous month
    if offset < -1:
        end_year, end_month = month_shift(base_year, base_month, -1)
    else:
        end_year, end_month = start_year, start_month

    _, end = month_bounds(end_year, end_month)

    return {"$gte": start, "$lte": end}

def resolve_absolute(part: DatePart, is_start: bool):
    year = part.year
    month = part.month or (1 if is_start else 12)
    day = part.day or (
        1 if is_start else calendar.monthrange(year, month)[1]
    )

    hour = 0 if is_start else 23
    minute = 0 if is_start else 59
    second = 0 if is_start else 59

    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

def month_shift(year: int, month: int, offset: int):
    new_month = month + offset
    new_year = year + (new_month - 1) // 12
    new_month = (new_month - 1) % 12 + 1
    return new_year, new_month


def month_bounds(year: int, month: int):
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end

def resolve_time_range(tr: TimeRange):
    if tr.type == "NONE":
        return None

    # ✅ RELATIVE MONTH (last month, last N months)
    if tr.type == "RELATIVE" and tr.from_ and tr.from_.relative:
        if tr.from_.relative.unit == "month":
            return resolve_relative_month(tr)

    # ✅ GENERIC RELATIVE (day, year)
    if tr.type == "RELATIVE":
        start = resolve_relative_simple(tr.from_, True) if tr.from_ else None
        end = resolve_relative_simple(tr.to, False) if tr.to else None
        return {"$gte": start, "$lte": end}

    # -------------------------
    # ✅ ENHANCED ABSOLUTE FIX
    # -------------------------
    if tr.type == "ABSOLUTE" and tr.from_ and tr.from_.day:
        # Check if it's a single day: 'to' is None OR 'to' is identical to 'from'
        is_single_day = (
            tr.to is None or 
            (tr.to.year == tr.from_.year and 
            tr.to.month == tr.from_.month and 
            tr.to.day == tr.from_.day)
        )

        if is_single_day:
            start = datetime(tr.from_.year, tr.from_.month, tr.from_.day, 0, 0, 0, tzinfo=timezone.utc)
            end = datetime(tr.from_.year, tr.from_.month, tr.from_.day, 23, 59, 59, tzinfo=timezone.utc)
            return {"$gte": start, "$lte": end}
        
        # Otherwise, resolve as a range
        start = resolve_absolute(tr.from_, True)
        end = resolve_absolute(tr.to, False)
        return {"$gte": start, "$lte": end}

    raise ValueError(f"Unsupported TimeRange type: {tr.type}")


# -------------------------------
# SAFE ENTRY
# -------------------------------
def extract_time_range_semantic(query: str) -> TimeRange | None:
    try:
        tr = time_range_chain.invoke({"query": query})
        if tr.type == "NONE":
            return None
        return tr
    except Exception as e:
        print("[TIME PARSE FAILED]", e)
        fallback = fallback_time_range(query)
        return TimeRange(**fallback) if fallback else None


import re

def fallback_time_range(query: str):
    q = query.lower()

    if "last month" in q:
        return {
            "type": "RELATIVE",
            "from": {"relative": {"unit": "month", "offset": -1}},
            "to": {"relative": {"unit": "month", "offset": -1}},
            "granularity": "month"
        }

    if m := re.search(r"last (\d+) months", q):
        n = int(m.group(1))
        return {
            "type": "RELATIVE",
            "from": {"relative": {"unit": "month", "offset": -n}},
            "to": {"relative": {"unit": "month", "offset": -1}},
            "granularity": "month"
        }

    return None

def safe_time_range(query: str):
    try:
        tr = extract_time_range_semantic(query)
        if tr is None:
            return fallback_time_parser(query)

        return resolve_time_range(tr)

    except Exception as e:
        print("[TIME RANGE FAILED]", e)
        return fallback_time_parser(query)


# -------------------------------
# FALLBACK (Deterministic)
# -------------------------------
def fallback_time_parser(query: str):
    q = query.lower()
    now = datetime.now(timezone.utc)

    if "last month" in q:
        start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = now.replace(day=1) - timedelta(seconds=1)
        return {"$gte": start, "$lte": end}

    if "last year" in q:
        y = now.year - 1
        return {
            "$gte": datetime(y, 1, 1, tzinfo=timezone.utc),
            "$lte": datetime(y, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        }

    return None
