from datetime import datetime, timedelta, timezone
import calendar
def resolve_time_range_to_mongo(tr: dict):
    """
    Converts semantic time range → Mongo filter
    """
    now = datetime.now(timezone.utc)

    def resolve(part, is_start):
        if "relative" in part:
            unit = part["relative"]["unit"]
            offset = part["relative"]["offset"]

            if unit == "month":
                base = now.replace(day=1)
                month = base.month + offset
                year = base.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                day = 1 if is_start else calendar.monthrange(year, month)[1]
                return datetime(year, month, day, tzinfo=timezone.utc)

            if unit == "day":
                return now + timedelta(days=offset)

        # absolute
        year = part["year"]
        month = part.get("month", 1 if is_start else 12)
        day = part.get("day", 1 if is_start else calendar.monthrange(year, month)[1])

        return datetime(year, month, day, tzinfo=timezone.utc)

    start = resolve(tr["from"], True)
    end = resolve(tr["to"], False)

    return {
        "$gte": start,
        "$lte": end.replace(hour=23, minute=59, second=59)
    }