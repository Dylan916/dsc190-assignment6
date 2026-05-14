from datetime import date, timedelta
import calendar
import re

# Mapping weekday names to weekday() integers (Monday=0 ... Sunday=6)
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Mapping month names to month numbers
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _parse_specific_date(text: str) -> date | None:
    """Try to parse a specific date like 'December 1st, 2025' or 'January 10th, 2026'."""
    pattern = r"(\w+)\s+(\d+)(?:st|nd|rd|th)?,?\s+(\d{4})"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        month_name, day_str, year_str = m.group(1), m.group(2), m.group(3)
        month = _MONTHS.get(month_name.lower())
        if month:
            return date(int(year_str), month, int(day_str))
    return None


def parse(s: str, today: date | None = None) -> date:
    """Parse a natural language date string and return a datetime.date.

    Parameters
    ----------
    s:     Natural language date expression (case- and whitespace-insensitive).
    today: Reference date for relative expressions. Defaults to date.today().

    Supported expressions
    ---------------------
    - "today", "tomorrow", "yesterday"
    - "N days from now"
    - "next <weekday>", "last <weekday>"
    - "N days before <specific date>"
    - "N weeks before <specific date>"
    - "N days after <specific date>"
    - "N weeks after <specific date>"
    - "end of month"
    """
    if today is None:
        today = date.today()

    # Normalise: strip surrounding whitespace and collapse internal whitespace
    text = " ".join(s.strip().split()).lower()

    # ── ISO 8601 "YYYY-MM-DD" ─────────────────────────────────────────────────
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return date.fromisoformat(text)

    # ── "today" ──────────────────────────────────────────────────────────────
    if text == "today":
        return today

    # ── "tomorrow" ───────────────────────────────────────────────────────────
    if text == "tomorrow":
        return today + timedelta(days=1)

    # ── "yesterday" ──────────────────────────────────────────────────────────
    if text == "yesterday":
        return today - timedelta(days=1)

    # ── "end of month" ───────────────────────────────────────────────────────
    if text == "end of month":
        last_day = calendar.monthrange(today.year, today.month)[1]
        return date(today.year, today.month, last_day)

    # ── "N days from now" ────────────────────────────────────────────────────
    m = re.fullmatch(r"(\d+)\s+days?\s+from\s+now", text)
    if m:
        return today + timedelta(days=int(m.group(1)))

    # ── "next <weekday>" ─────────────────────────────────────────────────────
    m = re.fullmatch(r"next\s+(\w+)", text)
    if m:
        target = _WEEKDAYS.get(m.group(1))
        if target is not None:
            days_ahead = (target - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # "next Monday" when today IS Monday → next week
            return today + timedelta(days=days_ahead)

    # ── "last <weekday>" ─────────────────────────────────────────────────────
    m = re.fullmatch(r"last\s+(\w+)", text)
    if m:
        target = _WEEKDAYS.get(m.group(1))
        if target is not None:
            days_back = (today.weekday() - target) % 7
            if days_back == 0:
                days_back = 7  # "last Monday" when today IS Monday → last week
            return today - timedelta(days=days_back)

    # ── "N days/weeks before <specific date>" ────────────────────────────────
    m = re.fullmatch(r"(\d+)\s+(days?|weeks?)\s+before\s+(.+)", text)
    if m:
        amount, unit, date_str = int(m.group(1)), m.group(2), m.group(3)
        anchor = _parse_specific_date(date_str)
        if anchor:
            delta = (
                timedelta(days=amount)
                if unit.startswith("day")
                else timedelta(weeks=amount)
            )
            return anchor - delta

    # ── "N days/weeks after <specific date>" ─────────────────────────────────
    m = re.fullmatch(r"(\d+)\s+(days?|weeks?)\s+after\s+(.+)", text)
    if m:
        amount, unit, date_str = int(m.group(1)), m.group(2), m.group(3)
        anchor = _parse_specific_date(date_str)
        if anchor:
            delta = (
                timedelta(days=amount)
                if unit.startswith("day")
                else timedelta(weeks=amount)
            )
            return anchor + delta

    raise ValueError(f"Cannot parse date expression: {s!r}")
