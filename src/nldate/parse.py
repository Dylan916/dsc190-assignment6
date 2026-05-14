import calendar
import re
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

_WEEKDAYS: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_MONTHS: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

# Word → integer for "two weeks from now" style
_WORD_NUMBERS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "a": 1,
    "an": 1,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_int(s: str) -> int | None:
    """Convert digit string or word number to int, or None if unrecognised."""
    s = s.strip()
    if s.isdigit():
        return int(s)
    return _WORD_NUMBERS.get(s.lower())


def _add_months(d: date, n: int) -> date:
    """Add n months to date d, clamping to the last day of the target month."""
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(d: date, n: int) -> date:
    """Add n years to date d, handling leap-day edge cases."""
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        # Feb 29 → Feb 28 in non-leap year
        return d.replace(year=d.year + n, day=28)


def _parse_named_month_date(text: str) -> date | None:
    """Parse absolute dates written with a month name.

    Accepts all of:
      - 'December 1st, 2025'   (Month Day, Year)
      - 'December 1, 2025'     (Month Day, Year  – no ordinal)
      - 'December 1 2025'      (Month Day Year   – no comma)
      - '1st December 2025'    (Day Month Year   – European)
      - '1 December 2025'      (Day Month Year)
      - 'Dec 1, 2025'          (abbreviated month)
    """
    ordinal = r"(?:st|nd|rd|th)?"
    sep = r"[,\s]+"

    # Month-first: "December 1st, 2025"
    m = re.fullmatch(
        rf"([a-z]+)\s+(\d{{1,2}}){ordinal}{sep}(\d{{4}})", text, re.IGNORECASE
    )
    if m:
        month = _MONTHS.get(m.group(1).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(2)))

    # Day-first: "1st December 2025"
    m = re.fullmatch(
        rf"(\d{{1,2}}){ordinal}\s+([a-z]+)\s+(\d{{4}})", text, re.IGNORECASE
    )
    if m:
        month = _MONTHS.get(m.group(2).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(1)))

    return None


def _resolve_relative(text: str, today: date) -> date | None:
    """Resolve a relative anchor word (today/tomorrow/yesterday) or return None."""
    if text == "today":
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)
    if text == "yesterday":
        return today - timedelta(days=1)
    return None


def _parse_anchor(text: str, today: date) -> date | None:
    """Parse any date expression that can serve as an anchor."""
    rel = _resolve_relative(text, today)
    if rel is not None:
        return rel
    # ISO / slash formats
    result = _try_absolute(text, today)
    return result


def _try_absolute(text: str, today: date) -> date | None:  # noqa: ARG001
    """Attempt to parse text as a bare absolute date; return None if unknown."""
    # ISO 8601
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", text):
        return date.fromisoformat(text)
    # YYYY/MM/DD
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # MM/DD/YYYY
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    # Named month
    return _parse_named_month_date(text)


def _apply_delta(anchor: date, amount: int, unit: str, direction: int) -> date:
    """Apply amount * unit in direction (+1 or -1) to anchor."""
    u = unit.rstrip("s")  # normalise plural
    if u in ("day",):
        return anchor + timedelta(days=direction * amount)
    if u in ("week",):
        return anchor + timedelta(weeks=direction * amount)
    if u in ("month",):
        return _add_months(anchor, direction * amount)
    if u in ("year",):
        return _add_years(anchor, direction * amount)
    return anchor + timedelta(days=direction * amount)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(s: str, today: date | None = None) -> date:
    """Parse a natural language date string and return a datetime.date.

    Parameters
    ----------
    s:
        Natural language date expression (case- and whitespace-insensitive).
    today:
        Reference date for relative expressions.  Defaults to date.today().

    Supported expressions
    ---------------------
    Absolute dates
        '2025-12-04', '2025/12/04', '12/04/2025'
        'December 1, 2025', 'Dec 1st, 2025', '1 December 2025'
    Relative to today
        'today', 'tomorrow', 'yesterday'
        'in N days', 'N days from now', 'N weeks from now'
        'N days ago', 'N weeks ago', 'N months ago', 'N years ago'
    Weekday navigation
        'next Tuesday', 'last Friday'
    Month navigation
        'next month', 'last month'
    Boundaries
        'start of month', 'beginning of month', 'end of month'
        'start of year', 'end of year'
    Offsets from a specific or relative date
        'N days before December 1st, 2025'
        'N weeks after January 10th, 2026'
        '1 year and 2 months after yesterday'
        'two weeks from tomorrow'
    """
    if today is None:
        today = date.today()

    # Normalise: strip surrounding whitespace and collapse internal whitespace
    text = " ".join(s.strip().split()).lower()

    # ── Bare absolute date ────────────────────────────────────────────────────
    absolute = _try_absolute(text, today)
    if absolute is not None:
        return absolute

    # ── Simple relative anchors ───────────────────────────────────────────────
    if text == "today":
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)
    if text == "yesterday":
        return today - timedelta(days=1)

    # ── Month / year boundaries ───────────────────────────────────────────────
    if text in ("start of month", "beginning of month"):
        return date(today.year, today.month, 1)
    if text == "end of month":
        last_day = calendar.monthrange(today.year, today.month)[1]
        return date(today.year, today.month, last_day)
    if text in ("start of year", "beginning of year"):
        return date(today.year, 1, 1)
    if text == "end of year":
        return date(today.year, 12, 31)

    # ── "next month" / "last month" ───────────────────────────────────────────
    if text == "next month":
        return _add_months(today, 1)
    if text == "last month":
        return _add_months(today, -1)

    # ── "next <weekday>" ─────────────────────────────────────────────────────
    m = re.fullmatch(r"next\s+(\w+)", text)
    if m:
        target = _WEEKDAYS.get(m.group(1))
        if target is not None:
            days_ahead = (target - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # same weekday → next week
            return today + timedelta(days=days_ahead)

    # ── "last <weekday>" ─────────────────────────────────────────────────────
    m = re.fullmatch(r"last\s+(\w+)", text)
    if m:
        target = _WEEKDAYS.get(m.group(1))
        if target is not None:
            days_back = (today.weekday() - target) % 7
            if days_back == 0:
                days_back = 7
            return today - timedelta(days=days_back)

    # ── "in N days/weeks/months/years" ───────────────────────────────────────
    _num = r"(\d+|" + "|".join(_WORD_NUMBERS) + r")"
    m = re.fullmatch(rf"in\s+{_num}\s+(days?|weeks?|months?|years?)", text)
    if m:
        amount = _to_int(m.group(1))
        if amount is not None:
            return _apply_delta(today, amount, m.group(2), 1)

    # ── "N days/weeks/months/years from now" ─────────────────────────────────
    m = re.fullmatch(rf"{_num}\s+(days?|weeks?|months?|years?)\s+from\s+now", text)
    if m:
        amount = _to_int(m.group(1))
        if amount is not None:
            return _apply_delta(today, amount, m.group(2), 1)

    # ── "N days/weeks/months/years ago" ──────────────────────────────────────
    m = re.fullmatch(rf"{_num}\s+(days?|weeks?|months?|years?)\s+ago", text)
    if m:
        amount = _to_int(m.group(1))
        if amount is not None:
            return _apply_delta(today, amount, m.group(2), -1)

    # ── "N units from <anchor>" (e.g. "two weeks from tomorrow") ─────────────
    m = re.fullmatch(rf"{_num}\s+(days?|weeks?|months?|years?)\s+from\s+(.+)", text)
    if m:
        amount = _to_int(m.group(1))
        anchor = _parse_anchor(m.group(3), today)
        if amount is not None and anchor is not None:
            return _apply_delta(anchor, amount, m.group(2), 1)

    # ── Compound: "N units and M units before/after <anchor>" ────────────────
    # e.g. "1 year and 2 months after yesterday"
    _unit_pat = (
        r"(\d+|" + "|".join(_WORD_NUMBERS) + r")\s+(days?|weeks?|months?|years?)"
    )
    compound = re.fullmatch(
        rf"{_unit_pat}(?:\s+and\s+{_unit_pat})*\s+(before|after)\s+(.+)", text
    )
    if compound and compound.lastindex is not None:
        direction_word = compound.group(compound.lastindex - 1)
        anchor_str = compound.group(compound.lastindex)
        direction = 1 if direction_word == "after" else -1
        anchor = _parse_anchor(anchor_str, today)
        if anchor is not None:
            # Extract all "N unit" pairs
            pairs = re.findall(_unit_pat, text[: text.rfind(direction_word)])
            result = anchor
            for amt_str, unit in pairs:
                amt = _to_int(amt_str)
                if amt is not None:
                    result = _apply_delta(result, amt, unit, direction)
            return result

    # ── Simple "N units before/after <anchor>" ────────────────────────────────
    m = re.fullmatch(
        rf"{_num}\s+(days?|weeks?|months?|years?)\s+(before|after)\s+(.+)", text
    )
    if m:
        amount = _to_int(m.group(1))
        unit = m.group(2)
        direction = 1 if m.group(3) == "after" else -1
        anchor = _parse_anchor(m.group(4), today)
        if amount is not None and anchor is not None:
            return _apply_delta(anchor, amount, unit, direction)

    raise ValueError(f"Cannot parse date expression: {s!r}")
