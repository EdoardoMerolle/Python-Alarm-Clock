"""Calendar view utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, date
from calendar import monthcalendar, month_name


class CalendarView:
    """Generate calendar grid data for display."""

    @staticmethod
    def get_month_grid(year: int, month: int) -> list[list[tuple[int, bool]]]:
        """
        Get calendar grid for month.
        
        Returns list of weeks, each week is list of (day, is_current_month) tuples.
        Days outside month have day=0.
        """
        grid = monthcalendar(year, month)
        result = []
        for week in grid:
            week_data = []
            for day in week:
                is_current = day != 0
                week_data.append((day, is_current))
            result.append(week_data)
        return result

    @staticmethod
    def get_events_for_date(alarms: list, target_date: date) -> list[str]:
        """Get alarm labels for a specific date."""
        events = []
        for alarm in alarms:
            if alarm.is_one_shot():
                alarm_date = alarm.one_shot_as_date()
                if alarm_date == target_date:
                    events.append(f"{alarm.label} @ {alarm.hour:02d}:{alarm.minute:02d}")
        return events

    @staticmethod
    def get_dates_with_events(alarms: list, year: int, month: int) -> set[int]:
        """Get set of day numbers that have events in given month."""
        dates_with_events = set()
        for alarm in alarms:
            if alarm.is_one_shot():
                alarm_date = alarm.one_shot_as_date()
                if alarm_date and alarm_date.year == year and alarm_date.month == month:
                    dates_with_events.add(alarm_date.day)
        return dates_with_events

    @staticmethod
    def format_month(year: int, month: int) -> str:
        """Format month name."""
        return f"{month_name[month]} {year}"
