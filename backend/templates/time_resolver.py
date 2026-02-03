from datetime import datetime, timedelta, timezone
import calendar
from templates.time_range import TimeRange, DatePart

def month_start(year: int, month: int):
    return datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)

def month_end(year: int, month: int):
    last_day = calendar.monthrange(year, month)[1]
    return datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

def shift_month(year, month, offset):
    """Shifts year and month by an offset (e.g., -1 for previous month)"""
    total_months = year * 12 + (month - 1) + offset
    new_year = total_months // 12
    new_month = (total_months % 12) + 1
    return new_year, new_month

from datetime import datetime
from dateutil.relativedelta import relativedelta


def resolve_relative(part: DatePart, base: datetime, is_start: bool):
    rel = part.relative
    unit = rel.unit
    offset = rel.offset

    if unit == "day":
        dt = base + relativedelta(days=offset)

    elif unit == "month":
        dt = base + relativedelta(months=offset)

        # Month boundary normalization
        if is_start:
            dt = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            dt = (
                dt.replace(day=1)
                + relativedelta(months=1)
                - relativedelta(microseconds=1)
            )

    elif unit == "year":
        dt = base + relativedelta(years=offset)

        if is_start:
            dt = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            dt = (
                dt.replace(month=1, day=1)
                + relativedelta(years=1)
                - relativedelta(microseconds=1)
            )

    else:
        raise ValueError(f"Unsupported relative unit: {unit}")

    return dt

def resolve_absolute(part: DatePart, is_start: bool):
    if not part:
        return None

    year = part.year
    month = part.month or (1 if is_start else 12)
    day = part.day or (
        1 if is_start else calendar.monthrange(year, month)[1]
    )

    hour = 0 if is_start else 23
    minute = 0 if is_start else 59
    second = 0 if is_start else 59

    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

def resolve_time_range(tr: TimeRange):
    if not isinstance(tr, TimeRange):
        raise TypeError("resolve_time_range expects TimeRange object")

    now = datetime.now(timezone.utc)

    # 1. Handle NONE
    if tr.type == "NONE":
        return None

    # 2. Handle RELATIVE (Hybrid Month: e.g., "Last November")
    if (tr.type == "RELATIVE" and tr.from_ and tr.from_.relative and tr.from_.month):
        if tr.from_.relative.unit == "year":
            year = now.year + tr.from_.relative.offset
        elif tr.from_.relative.unit == "month":
            year, _ = shift_month(now.year, now.month, tr.from_.relative.offset)
        else:
            raise ValueError("Unsupported relative unit for hybrid month")

        month = tr.from_.month
        return {"$gte": month_start(year, month), "$lte": month_end(year, month)}

    # 3. Handle RELATIVE (Standard Ranges: e.g., "Last 3 months")
    if tr.type == "RELATIVE" and tr.from_ and tr.from_.relative:
        if tr.from_.relative.unit == "month":
            offset = tr.from_.relative.offset
            start_year, start_month = shift_month(now.year, now.month, offset)
            start = month_start(start_year, start_month)
            
            # If offset is -3, we want from 3 months ago until last month
            end_offset = -1 if offset < -1 else offset
            end_year, end_month = shift_month(now.year, now.month, end_offset)
            end = month_end(end_year, end_month)
            return {"$gte": start, "$lte": end}

    # 4. Handle RELATIVE (Pure Day/Year)
    if tr.type == "RELATIVE":
        start = resolve_relative(tr.from_, now, is_start=True)
        end = resolve_relative(tr.to, now, is_start=False)
        return {"$gte": start, "$lte": end}

    # 5. Handle ABSOLUTE (The Logic Fix)
    if tr.type == "ABSOLUTE" and tr.from_:
        # Check if this is a single point (no 'to' or 'to' is same as 'from')
        is_single_point = tr.to is None or (
            tr.to.year == tr.from_.year and 
            tr.to.month == tr.from_.month and 
            tr.to.day == tr.from_.day
        )

        if is_single_point:
            y, m, d = tr.from_.year, tr.from_.month, tr.from_.day
            
            if tr.granularity == "day" and d:
                # Specific Day: 00:00:00 to 23:59:59
                start = datetime(y, m, d, 0, 0, 0, tzinfo=timezone.utc)
                end = datetime(y, m, d, 23, 59, 59, tzinfo=timezone.utc)
            elif tr.granularity == "month" and m:
                # Full Month: 1st to Last Day
                start = month_start(y, m)
                end = month_end(y, m)
            elif tr.granularity == "year":
                # Full Year: Jan 1st to Dec 31st
                start = datetime(y, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
                end = datetime(y, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            else:
                # Fallback to resolver helper
                start = resolve_absolute(tr.from_, is_start=True)
                end = resolve_absolute(tr.from_, is_start=False)
            return {"$gte": start, "$lte": end}

        # Handle Explicit Range (e.g., "Jan 2024 to March 2024")
        start = resolve_absolute(tr.from_, is_start=True)
        end = resolve_absolute(tr.to, is_start=False)
        return {"$gte": start, "$lte": end}

    raise ValueError(f"Unsupported TimeRange type: {tr.type}")