import sys
import os
import random
import threading
import requests
from datetime import datetime, timedelta, date
from pathlib import Path

from icalendar import Calendar

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import database

class SmartClockBackend(QObject):
    timeChanged = Signal()
    alarmTriggered = Signal(str)
    alarmsChanged = Signal()
    nightModeChanged = Signal()
    calendarChanged = Signal() 

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_time = ""
        self._is_night_mode = False
        self._calendar_events = [] 
        self._is_fetching_calendar = False 
        
        database.init_db()

        # Paths
        base_path = Path(__file__).resolve().parent
        self.cal_path = base_path / "assets" / "calendars"
        self.cal_path.mkdir(parents=True, exist_ok=True)
        self.cal_links_file = base_path / "assets" / "calendar_links.txt"

        # Audio Setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        sound_path = base_path / "assets" / "sounds" / "alarm.mp3"
        self.player.setSource(QUrl.fromLocalFile(str(sound_path)))
        self.audio_output.setVolume(1.0)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        
        self._refresh_calendar()
        self._tick()

    def _refresh_calendar(self):
        if self._is_fetching_calendar: return
        self._is_fetching_calendar = True
        thread = threading.Thread(target=self._worker_fetch_calendars, daemon=True)
        thread.start()

    def _worker_fetch_calendars(self):
        try:
            events = []
            now = datetime.now().astimezone()

            # 1. Local Files
            if self.cal_path.exists():
                for file in os.listdir(self.cal_path):
                    if file.lower().endswith(".ics"):
                        try:
                            with open(self.cal_path / file, 'rb') as f:
                                self._parse_ical_data(f.read(), events, now)
                        except Exception as e:
                            print(f"Error parsing local file {file}: {e}")

            # 2. Remote URLs
            if self.cal_links_file.exists():
                try:
                    with open(self.cal_links_file, 'r') as f:
                        urls = [line.strip() for line in f if line.strip()]
                    for url in urls:
                        try:
                            response = requests.get(url, timeout=5)
                            if response.status_code == 200:
                                self._parse_ical_data(response.content, events, now)
                        except Exception as e:
                            print(f"Error fetching {url}: {e}")
                except Exception: pass

            # Sort by the datetime object (sort_date)
            events.sort(key=lambda x: x['sort_date'])
            self._calendar_events = events 
            self.calendarChanged.emit()
        finally:
            self._is_fetching_calendar = False

    def _parse_ical_data(self, content, events_list, now):
        try:
            gcal = Calendar.from_ical(content)
            for component in gcal.walk():
                if component.name == "VEVENT":
                    # Extract Basic Info
                    summary = str(component.get('summary', 'No Title'))
                    
                    # Extract Location & Description (Handle None safely)
                    location = component.get('location')
                    location = str(location) if location else ""
                    
                    description = component.get('description')
                    description = str(description) if description else ""

                    if component.get('dtstart'):
                        dtstart = component.get('dtstart').dt
                        
                        # Fix Date vs Datetime types
                        if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                            dtstart = datetime.combine(dtstart, datetime.min.time()).astimezone()
                        
                        if dtstart.tzinfo is None:
                            dtstart = dtstart.astimezone()

                        # Filter old events (keep recent past for context)
                        if dtstart >= now - timedelta(days=1):
                            # Pretty Date String
                            if dtstart.date() == now.date():
                                date_str = f"Today, {dtstart.strftime('%H:%M')}"
                            elif dtstart.date() == (now + timedelta(days=1)).date():
                                date_str = f"Tomorrow, {dtstart.strftime('%H:%M')}"
                            else:
                                date_str = dtstart.strftime("%a %d %b, %H:%M")

                            events_list.append({
                                "title": summary,
                                "date": date_str,          
                                "date_iso": dtstart.isoformat(), 
                                "sort_date": dtstart,
                                "location": location,       # <--- NEW
                                "description": description  # <--- NEW
                            })
        except Exception as e:
            print(f"ICS Parse Error: {e}")

    @Property(list, notify=calendarChanged)
    def calendarEvents(self):
        return self._calendar_events

    @Property(list, constant=True)
    def imageList(self):
        image_urls = []
        base_path = Path(__file__).resolve().parent
        folder_path = base_path / "assets" / "images"
        if folder_path.exists():
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    full_path = folder_path / file
                    image_urls.append(QUrl.fromLocalFile(str(full_path)).toString())
        random.shuffle(image_urls)
        return image_urls

    def _tick(self):
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        if time_str != self._current_time:
            self._current_time = time_str
            self.timeChanged.emit()
            if now.second == 0:
                self._check_alarms(now)
                self._refresh_calendar()

        is_night = (now.hour >= 22 or now.hour < 5)
        if is_night != self._is_night_mode:
            self._is_night_mode = is_night
            self.nightModeChanged.emit()

    def _check_alarms(self, now_dt):
        current_time_str = now_dt.strftime("%H:%M")
        current_weekday = str(now_dt.weekday()) 
        active_alarms = database.get_active_alarms()
        for alarm in active_alarms:
            if alarm['time'] == current_time_str:
                days = alarm['days'] 
                if days == "Daily" or current_weekday in days.split(","):
                    if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                        self.player.play()
                    self.alarmTriggered.emit("Wake Up!")

    @Property(str, notify=timeChanged)
    def currentTime(self): return self._current_time
    
    @Property(bool, notify=nightModeChanged)
    def isNightMode(self): return self._is_night_mode

    @Property(list, notify=alarmsChanged)
    def alarmList(self): return database.get_all_alarms()

    @Slot()
    def stopAlarm(self): self.player.stop()

    @Slot()
    def snoozeAlarm(self):
        self.player.stop()
        snooze_time = datetime.now() + timedelta(minutes=9)
        new_time_str = snooze_time.strftime("%H:%M")
        day_str = str(datetime.now().weekday())
        database.add_alarm(new_time_str, day_str)
        self.alarmsChanged.emit()

    @Slot(int)
    def deleteAlarm(self, alarm_id):
        conn = database.get_connection()
        conn.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
        conn.commit()
        conn.close()
        self.alarmsChanged.emit()

    @Slot(str, str)
    def createAlarm(self, time_str, days_str):
        database.add_alarm(time_str, days_str)
        self.alarmsChanged.emit()

    @Slot(int, str, str)
    def updateAlarm(self, alarm_id, time_str, days_str):
        database.update_alarm(alarm_id, time_str, days_str)
        self.alarmsChanged.emit()

    @Slot(int, bool)
    def toggleAlarm(self, alarm_id, is_active):
        database.toggle_alarm(alarm_id, is_active)
        self.alarmsChanged.emit()

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    backend = SmartClockBackend(app)
    engine.backend_reference = backend 
    engine.rootContext().setContextProperty("backend", backend)
    engine.load("main.qml")
    if not engine.rootObjects(): sys.exit(-1)
    sys.exit(app.exec())