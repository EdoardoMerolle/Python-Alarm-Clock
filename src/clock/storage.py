from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS alarms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT NOT NULL,
  hour INTEGER NOT NULL,
  minute INTEGER NOT NULL,
  weekdays_mask INTEGER NOT NULL, -- bitmask Mon..Sun (Mon=1<<0 ... Sun=1<<6)
  enabled INTEGER NOT NULL,
  one_shot_date TEXT -- YYYY-MM-DD or NULL
);

CREATE INDEX IF NOT EXISTS idx_alarms_enabled ON alarms(enabled);

-- single-row state table for snooze / active alarm
CREATE TABLE IF NOT EXISTS alarm_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  snooze_until TEXT,       -- ISO datetime string or NULL
  snooze_alarm_id INTEGER  -- which alarm was snoozed (optional, can be NULL)
);

INSERT OR IGNORE INTO alarm_state(id, snooze_until, snooze_alarm_id)
VALUES (1, NULL, NULL);
"""


class AlarmStore:
    def __init__(self, db_path: str | Path = "alarms.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.executescript(SCHEMA)

    def list_rows(self) -> list[sqlite3.Row]:
        with self._connect() as con:
            cur = con.execute("SELECT * FROM alarms ORDER BY hour, minute, id")
            return cur.fetchall()

    def insert(
        self,
        label: str,
        hour: int,
        minute: int,
        weekdays_mask: int,
        enabled: bool = True,
        one_shot_date: Optional[str] = None,
    ) -> int:
        with self._connect() as con:
            cur = con.execute(
                """
                INSERT INTO alarms(label, hour, minute, weekdays_mask, enabled, one_shot_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (label, hour, minute, weekdays_mask, 1 if enabled else 0, one_shot_date),
            )
            return int(cur.lastrowid)

    def update_enabled(self, alarm_id: int, enabled: bool) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE alarms SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, alarm_id),
            )

    def delete(self, alarm_id: int) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))

    def update_one_shot_date(self, alarm_id: int, one_shot_date: Optional[str]) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE alarms SET one_shot_date = ? WHERE id = ?",
                (one_shot_date, alarm_id),
            )
        # ---- Snooze state helpers ----

    def get_snooze(self) -> tuple[Optional[str], Optional[int]]:
        with self._connect() as con:
            row = con.execute(
                "SELECT snooze_until, snooze_alarm_id FROM alarm_state WHERE id = 1"
            ).fetchone()
            if row is None:
                return None, None
            return (
                (str(row["snooze_until"]) if row["snooze_until"] is not None else None),
                (int(row["snooze_alarm_id"]) if row["snooze_alarm_id"] is not None else None),
            )

    def set_snooze(self, snooze_until: Optional[str], snooze_alarm_id: Optional[int]) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE alarm_state SET snooze_until = ?, snooze_alarm_id = ? WHERE id = 1",
                (snooze_until, snooze_alarm_id),
            )

    def clear_snooze(self) -> None:
        self.set_snooze(None, None)
