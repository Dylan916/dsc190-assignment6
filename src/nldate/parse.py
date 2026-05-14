from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

WEEKDAYS: dict[str, int] = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

MONTHS: dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

WORD_NUMBERS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
}

_NUM = r"(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty)"
_UNIT = r"(days?|weeks?|months?|years?)"


def _parse_int(s: str) -> int:
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    if s in WORD_NUMBERS:
        return WORD_NUMBERS[s]
    raise ValueError(f"Cannot parse number: {s!r}")


def _add_months(d: date, n: int) -> date:
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _apply_delta(base: date, n: int, unit: str) -> date:
    unit = unit if unit.endswith("s") else unit + "s"
    if unit == "days":
        return base + timedelta(days=n)
    if unit == "weeks":
        return base + timedelta(weeks=n)
    if unit == "months":
        return _add_months(base, n)
    if unit == "years":
        return _add_months(base, n * 12)
    raise ValueError(f"Unknown unit: {unit!r}")


def _parse_absolute(s: str) -> date | None:
    s = s.strip()

    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))

    m = re.search(r"(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", s, re.IGNORECASE)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(2)))

    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(\w+),?\s+(\d{4})", s, re.IGNORECASE)
    if m:
        month = MONTHS.get(m.group(2).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(1)))

    return None


def _resolve_anchor(s: str, today: date) -> date:
    s = s.strip().lower()
    if s in ("today", "now"):
        return today
    if s == "tomorrow":
        return today + timedelta(days=1)
    if s == "yesterday":
        return today - timedelta(days=1)
    result = _parse_absolute(s)
    if result is not None:
        return result
    raise ValueError(f"Cannot parse anchor: {s!r}")


def _try_weekday(s: str, today: date) -> date | None:
    s = s.strip().lower()

    m = re.fullmatch(r"next\s+(\w+)", s)
    if m and m.group(1) in WEEKDAYS:
        target = WEEKDAYS[m.group(1)]
        return today + timedelta(days=(target - today.weekday()) % 7 or 7)

    m = re.fullmatch(r"(?:last|previous)\s+(\w+)", s)
    if m and m.group(1) in WEEKDAYS:
        target = WEEKDAYS[m.group(1)]
        return today - timedelta(days=(today.weekday() - target) % 7 or 7)

    m = re.fullmatch(r"this\s+(\w+)", s)
    if m and m.group(1) in WEEKDAYS:
        target = WEEKDAYS[m.group(1)]
        return today + timedelta(days=(target - today.weekday()) % 7)

    return None


def parse(s: str, today: date | None = None) -> date:
    if today is None:
        today = date.today()

    s = " ".join(s.strip().split())
    s_lower = s.lower()

    if s_lower in ("today", "now"):
        return today
    if s_lower == "tomorrow":
        return today + timedelta(days=1)
    if s_lower == "yesterday":
        return today - timedelta(days=1)
    if s_lower == "end of month":
        return date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

    weekday_result = _try_weekday(s_lower, today)
    if weekday_result is not None:
        return weekday_result

    m = re.fullmatch(rf"in\s+{_NUM}\s+{_UNIT}", s_lower)
    if m:
        return _apply_delta(today, _parse_int(m.group(1)), m.group(2))

    m = re.fullmatch(rf"{_NUM}\s+{_UNIT}\s+ago", s_lower)
    if m:
        return _apply_delta(today, -_parse_int(m.group(1)), m.group(2))

    m = re.fullmatch(rf"{_NUM}\s+{_UNIT}\s+from\s+(.+)", s_lower)
    if m:
        return _apply_delta(_resolve_anchor(m.group(3), today), _parse_int(m.group(1)), m.group(2))

    m = re.fullmatch(
        rf"{_NUM}\s+{_UNIT}\s+and\s+{_NUM}\s+{_UNIT}\s+(after|before)\s+(.+)",
        s_lower,
    )
    if m:
        n1, u1 = _parse_int(m.group(1)), m.group(2)
        n2, u2 = _parse_int(m.group(3)), m.group(4)
        direction = 1 if m.group(5) == "after" else -1
        anchor = _resolve_anchor(m.group(6), today)
        return _apply_delta(_apply_delta(anchor, direction * n1, u1), direction * n2, u2)

    m = re.fullmatch(rf"{_NUM}\s+{_UNIT}\s+(after|before)\s+(.+)", s_lower)
    if m:
        direction = 1 if m.group(3) == "after" else -1
        anchor = _resolve_anchor(m.group(4), today)
        return _apply_delta(anchor, direction * _parse_int(m.group(1)), m.group(2))

    absolute = _parse_absolute(s_lower)
    if absolute is not None:
        return absolute

    raise ValueError(f"Cannot parse date string: {s!r}")