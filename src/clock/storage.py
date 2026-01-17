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
