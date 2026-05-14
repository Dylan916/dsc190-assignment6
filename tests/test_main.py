from nldate import parse
from datetime import date

def test_relative_offset_before_specific_date():
    assert parse("5 days before December 1st, 2025") == date(2025, 11, 26)

def test_relative_offset_after_specific_date():
    assert parse("3 weeks after January 10th, 2026") == date(2026, 1, 31)

def test_next_weekday():
    assert parse("next Tuesday", today=date(2025, 5, 12)) == date(2025, 5, 13)

def test_next_weekday_when_today_is_that_day():
    assert parse("next Monday", today=date(2025, 5, 12)) == date(2025, 5, 19)

def test_last_weekday():
    assert parse("last Friday", today=date(2025, 5, 14)) == date(2025, 5, 9)

def test_today():
    assert parse("today", today=date(2025, 6, 1)) == date(2025, 6, 1)

def test_tomorrow_across_year_boundary():
    assert parse("tomorrow", today=date(2025, 12, 31)) == date(2026, 1, 1)

def test_yesterday_across_year_boundary():
    assert parse("yesterday", today=date(2026, 1, 1)) == date(2025, 12, 31)

def test_days_from_now_across_month_boundary():
    assert parse("10 days from now", today=date(2025, 3, 25)) == date(2025, 4, 4)

def test_end_of_month_february_non_leap_year():
    assert parse("end of month", today=date(2025, 2, 10)) == date(2025, 2, 28)

def test_case_and_whitespace_insensitivity():
    assert parse("  NEXT tuesday ", today=date(2025, 5, 12)) == date(2025, 5, 13)