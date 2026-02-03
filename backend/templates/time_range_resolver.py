from datetime import datetime, timedelta, timezone
import calendar

from templates.time_range import TimeRange, DatePart

def resolve_time_range(tr: TimeRange):
    now = datetime.now(timezone.utc)

    def resolve_part(part: DatePart, is_start: bool):
        if part.relative:
            if part.relative.unit == "month":
                base = now.replace(day=1)
                month = base.month + part.relative.offset
                year = base.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                day = 1 if is_start else calendar.monthrange(year, month)[1]
                return datetime(year, month, day, tzinfo=timezone.utc)

            if part.relative.unit == "year":
                year = now.year + part.relative.offset
                return datetime(year, 1, 1 if is_start else 12, tzinfo=timezone.utc)

            if part.relative.unit == "day":
                return now + timedelta(days=part.relative.offset)

        # Absolute
        year = part.year
        month = part.month or (1 if is_start else 12)
        day = part.day or (
            1 if is_start else calendar.monthrange(year, month)[1]
        )

        return datetime(year, month, day, tzinfo=timezone.utc)

    start = resolve_part(tr.from_, True) if tr.from_ else None
    end = resolve_part(tr.to, False) if tr.to else None

    if start and end:
        end = end.replace(hour=23, minute=59, second=59)

    return {"$gte": start, "$lte": end}
