"""Offline regressions for calendar updates and Python/QML list conversion."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from datetime import datetime, timedelta
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QObject, Property, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from main import SmartClockBackend


class CalendarBackend(SmartClockBackend):
    def __init__(self):
        QObject.__init__(self)
        self._calendar_events = []
        self._is_fetching_calendar = False
        self._calendarLoaded.connect(self._apply_calendar_events, Qt.QueuedConnection)
        self.reads = 0
        self._current_time = "12:00"
        self._current_date = "Test date"
        self._is_night_mode = False
        self._night_mode_setting = "auto"
        self._weather_temp = "--"
        self._weather_icon = self._weather_desc = ""
        self._light_is_on = False
        self._snooze_until = None
        self._image_urls = []

    @Property(list, notify=SmartClockBackend.calendarChanged)
    def calendarEvents(self):
        self.reads += 1
        return self._calendar_events


def events():
    today = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
    return [dict(title="Test event", date="Test date", date_iso=(today + timedelta(days=i)).isoformat(),
                 sort_date=today + timedelta(days=i), location="", description="") for i in range(12)]


class CalendarUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def test_worker_delivery_and_unchanged_data(self):
        backend = CalendarBackend()
        changes = []
        backend.calendarChanged.connect(lambda: changes.append(threading.get_ident()))
        backend._is_fetching_calendar = True
        worker = threading.Thread(target=lambda: backend._calendarLoaded.emit(events()))
        worker.start()
        worker.join()
        self.assertEqual(backend._calendar_events, [])
        QTest.qWait(30)
        self.assertEqual(len(backend._calendar_events), 12)
        self.assertFalse(backend._is_fetching_calendar)
        self.assertEqual(changes, [threading.get_ident()])
        backend._apply_calendar_events(list(backend._calendar_events))
        self.assertEqual(len(changes), 1)

    def test_qml_reads_event_list_once_per_update(self):
        backend = CalendarBackend()
        backend._calendar_events = events()
        engine = QQmlApplicationEngine()
        with patch("database.get_all_alarms", return_value=[]):
            engine.rootContext().setContextProperty("backend", backend)
            engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "main.qml")))
            self.assertTrue(engine.rootObjects())
            QTest.qWait(30)
            self.assertLessEqual(backend.reads, 2)
            before = backend.reads
            backend._apply_calendar_events(backend._calendar_events + [dict(backend._calendar_events[0], title="Changed")])
            QTest.qWait(30)
            self.assertLessEqual(backend.reads - before, 2)
            for root in engine.rootObjects():
                root.close()
            engine.deleteLater()
            QTest.qWait(20)


if __name__ == "__main__":
    unittest.main()
