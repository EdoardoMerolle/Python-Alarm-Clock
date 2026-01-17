from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional

from .storage import AlarmStore


# Weekdays: Python datetime.weekday(): Mon=0 ... Sun=6
def weekdays_to_mask(weekdays: Iterable[int]) -> int:
    mask = 0
    for d in weekdays:
        if d < 0 or d > 6:
            raise ValueError("weekday must be 0..6 (Mon..Sun)")
        mask |= 1 << d
    return mask


def mask_has_day(mask: int, weekday: int) -> bool:
    return (mask & (1 << weekday)) != 0


def parse_hhmm(hhmm: str) -> tuple[int, int]:
    parts = hhmm.strip().split(":")
    if len(parts) != 2:
        raise ValueError("time must be HH:MM")
    h = int(parts[0])
    m = int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("hour/minute out of range")
    return h, m


@dataclass(frozen=True)
class Alarm:
    id: int
    label: str
    hour: int
    minute: int
    weekdays_mask: int
    enabled: bool
    one_shot_date: Optional[str]  # YYYY-MM-DD or None

    def is_one_shot(self) -> bool:
        return self.one_shot_date is not None

    def one_shot_as_date(self) -> Optional[date]:
        if self.one_shot_date is None:
            return None
        return date.fromisoformat(self.one_shot_date)


@dataclass(frozen=True)
class NextAlarm:
    alarm: Alarm
    trigger_at: datetime


class AlarmManager:
    """
    Pure scheduling logic + storage. No UI code.
    """

    def __init__(self, store: AlarmStore) -> None:
        self.store = store

    def list_alarms(self) -> list[Alarm]:
        rows = self.store.list_rows()
        return [
            Alarm(
                id=int(r["id"]),
                label=str(r["label"]),
                hour=int(r["hour"]),
                minute=int(r["minute"]),
                weekdays_mask=int(r["weekdays_mask"]),
                enabled=bool(r["enabled"]),
                one_shot_date=(str(r["one_shot_date"]) if r["one_shot_date"] is not None else None),
            )
            for r in rows
        ]

    def add_weekly_alarm(
        self,
        label: str,
        hhmm: str,
        weekdays: Iterable[int],
        enabled: bool = True,
    ) -> int:
        h, m = parse_hhmm(hhmm)
        mask = weekdays_to_mask(weekdays)
        return self.store.insert(label=label, hour=h, minute=m, weekdays_mask=mask, enabled=enabled, one_shot_date=None)

    def add_one_shot_alarm(
        self,
        label: str,
        hhmm: str,
        on_date: date,
        enabled: bool = True,
    ) -> int:
        h, m = parse_hhmm(hhmm)
        # weekdays_mask ignored for one-shot, keep 0
        return self.store.insert(label=label, hour=h, minute=m, weekdays_mask=0, enabled=enabled, one_shot_date=on_date.isoformat())

    def set_enabled(self, alarm_id: int, enabled: bool) -> None:
        self.store.update_enabled(alarm_id, enabled)

    def delete(self, alarm_id: int) -> None:
        self.store.delete(alarm_id)

    def compute_next(self, now: Optional[datetime] = None) -> Optional[NextAlarm]:
        """
        Returns the next upcoming enabled alarm (weekly or one-shot) after 'now'.
        """
        now = now or datetime.now()
        candidates: list[NextAlarm] = []

        for a in self.list_alarms():
            if not a.enabled:
                continue

            nxt = self._next_trigger_for_alarm(a, now)
            if nxt is not None:
                candidates.append(NextAlarm(alarm=a, trigger_at=nxt))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x.trigger_at)
        return candidates[0]

    def mark_fired_if_one_shot(self, alarm: Alarm, fired_at: datetime) -> None:
        """
        If a one-shot alarm fired, disable it (or clear date). Here we disable it.
        """
        if alarm.is_one_shot():
            self.set_enabled(alarm.id, False)

    def _next_trigger_for_alarm(self, alarm: Alarm, now: datetime) -> Optional[datetime]:
        # One-shot: if date in the past -> no trigger
        if alarm.is_one_shot():
            d = alarm.one_shot_as_date()
            if d is None:
                return None
            trigger = datetime.combine(d, time(alarm.hour, alarm.minute))
            if trigger > now:
                return trigger
            return None

        # Weekly repeating
        if alarm.weekdays_mask == 0:
            return None  # no days selected

        # Search up to 7 days ahead for next selected weekday/time
        for day_offset in range(0, 8):
            day = (now.date() + timedelta(days=day_offset))
            weekday = datetime.combine(day, time(0, 0)).weekday()
            if not mask_has_day(alarm.weekdays_mask, weekday):
                continue

            candidate = datetime.combine(day, time(alarm.hour, alarm.minute))
            if candidate > now:
                return candidate

        return None
