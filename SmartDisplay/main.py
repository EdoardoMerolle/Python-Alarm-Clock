import sys
import os
import random
import threading
import requests
import json
import asyncio
import time
from datetime import datetime, timedelta, date
from pathlib import Path

from icalendar import Calendar
from kasa import Discover

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
    weatherChanged = Signal()
    lightStateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_time = ""
        self._is_night_mode = False
        self._calendar_events = [] 
        self._is_fetching_calendar = False 
        
        # --- 1. LOAD SECRETS ---
        self.secrets = self._load_secrets()

        # --- 2. CONFIGURATION ---
        self.LATITUDE = self.secrets.get("latitude", 51.5074)
        self.LONGITUDE = self.secrets.get("longitude", -0.1278)
        self.TAPO_IP = self.secrets.get("tapo_ip", "")
        self.TAPO_EMAIL = self.secrets.get("tapo_email", "")
        self.TAPO_PASSWORD = self.secrets.get("tapo_password", "")
        
        self._weather_temp = "--"
        self._weather_icon = "" 
        self._weather_desc = "Loading..."
        self._light_is_on = False
        
        # --- ASYNC SETUP (Fix for Event Loop Error) ---
        self._bulb_device = None
        self.tapo_loop = asyncio.new_event_loop()
        self.tapo_thread = threading.Thread(target=self._run_tapo_loop, daemon=True)
        self.tapo_thread.start()
        
        database.init_db()

        # Paths
        base_path = Path(__file__).resolve().parent
        self.cal_path = base_path / "assets" / "calendars"
        self.cal_path.mkdir(parents=True, exist_ok=True)
        self.cal_links_file = base_path / "assets" / "calendar_links.txt"
        self.weather_asset_path = base_path / "assets" / "weather"
        self.weather_asset_path.mkdir(parents=True, exist_ok=True)

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
        
        # --- 3. INITIAL LOADS ---
        if "latitude" not in self.secrets:
            self._detect_location()
        else:
            self._fetch_weather()
            
        self._refresh_calendar()
        self._tick()

    def _load_secrets(self):
        secrets_path = Path(__file__).resolve().parent / "secrets.json"
        try:
            if secrets_path.exists():
                with open(secrets_path, "r") as f:
                    return json.load(f)
            return {}
        except: return {}

    # --- TAPO LIGHT LOGIC (FIXED) ---
    def _run_tapo_loop(self):
        """Runs a permanent event loop in a background thread."""
        asyncio.set_event_loop(self.tapo_loop)
        self.tapo_loop.run_forever()

    @Property(bool, notify=lightStateChanged)
    def lightIsOn(self): return self._light_is_on

    @Slot()
    def toggleLight(self):
        # Optimistic UI update
        self._light_is_on = not self._light_is_on
        self.lightStateChanged.emit()
        # Schedule the toggle on the persistent loop
        asyncio.run_coroutine_threadsafe(self._async_tapo_toggle(), self.tapo_loop)

    def _check_light_status(self):
        # Schedule status check
        asyncio.run_coroutine_threadsafe(self._async_tapo_status(), self.tapo_loop)

    async def _get_bulb(self):
        """Gets the bulb device, reusing the connection if possible."""
        if self._bulb_device:
            return self._bulb_device
        
        if not self.TAPO_IP: return None

        try:
            # Discover and connect
            dev = await Discover.discover_single(
                self.TAPO_IP, 
                username=self.TAPO_EMAIL, 
                password=self.TAPO_PASSWORD
            )
            await dev.update()
            self._bulb_device = dev
            return dev
        except Exception as e:
            print(f"Tapo Connect Error: {e}")
            return None

    async def _async_tapo_toggle(self):
        bulb = await self._get_bulb()
        if not bulb: return

        try:
            if bulb.is_on:
                await bulb.turn_off()
                self._light_is_on = False
            else:
                await bulb.turn_on()
                self._light_is_on = True
            self.lightStateChanged.emit()
        except Exception as e:
            print(f"Tapo Toggle Error: {e}")
            self._bulb_device = None # Force reconnect next time

    async def _async_tapo_status(self):
        bulb = await self._get_bulb()
        if not bulb: return

        try:
            # We must explicitly update state from the device
            await bulb.update()
            real_state = bulb.is_on
            
            # Only emit signal if state actually changed
            if self._light_is_on != real_state:
                self._light_is_on = real_state
                self.lightStateChanged.emit()
        except Exception as e:
            print(f"Tapo Status Error: {e}")
            self._bulb_device = None # Force reconnect next time

    # --- LOCATION DETECTION ---
    def _detect_location(self):
        threading.Thread(target=self._worker_location, daemon=True).start()

    def _worker_location(self):
        try:
            response = requests.get("http://ip-api.com/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.LATITUDE = data.get("lat")
                    self.LONGITUDE = data.get("lon")
                    self._fetch_weather()
        except: pass

    # --- WEATHER LOGIC ---
    def _fetch_weather(self):
        threading.Thread(target=self._worker_weather, daemon=True).start()

    def _worker_weather(self):
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.LATITUDE}&longitude={self.LONGITUDE}&current_weather=true"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json().get("current_weather", {})
                temp = data.get("temperature")
                code = data.get("weathercode")
                
                self._weather_temp = f"{temp}°C"
                self._weather_icon = self._get_icon_for_code(code)
                self._weather_desc = self._get_desc_for_code(code)
                self.weatherChanged.emit()
        except: pass

    def _get_icon_for_code(self, code):
        filename = "cloudy.png"
        if code == 0: 
            filename = "moon.png" if self._is_night_mode else "sun.png"
        elif code in [1, 2, 3]: filename = "cloudy.png"
        elif code in [45, 48]: filename = "fog.png"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: filename = "rain.png"
        elif code in [71, 73, 75, 77, 85, 86]: filename = "snow.png"
        elif code in [95, 96, 99]: filename = "storm.png"
        
        full_path = self.weather_asset_path / filename
        if full_path.exists():
            return QUrl.fromLocalFile(str(full_path)).toString()
        return ""

    def _get_desc_for_code(self, code):
        if code == 0: return "Clear Sky"
        if code in [1, 2, 3]: return "Cloudy"
        if code in [45, 48]: return "Foggy"
        if code in [51, 53, 55, 61, 63, 65]: return "Rain"
        if code in [71, 73, 75, 77]: return "Snow"
        if code >= 95: return "Storm"
        return "Unknown"

    @Property(str, notify=weatherChanged)
    def weatherTemp(self): return self._weather_temp

    @Property(str, notify=weatherChanged)
    def weatherIcon(self): return self._weather_icon

    @Property(str, notify=weatherChanged)
    def weatherDesc(self): return self._weather_desc

    # --- CALENDAR LOGIC ---
    def _refresh_calendar(self):
        if self._is_fetching_calendar: return
        self._is_fetching_calendar = True
        threading.Thread(target=self._worker_fetch_calendars, daemon=True).start()

    def _worker_fetch_calendars(self):
        try:
            events = []
            now = datetime.now().astimezone()
            if self.cal_path.exists():
                for file in os.listdir(self.cal_path):
                    if file.lower().endswith(".ics"):
                        try:
                            with open(self.cal_path / file, 'rb') as f:
                                self._parse_ical_data(f.read(), events, now)
                        except: pass
            if self.cal_links_file.exists():
                try:
                    with open(self.cal_links_file, 'r') as f:
                        urls = [line.strip() for line in f if line.strip()]
                    for url in urls:
                        try:
                            r = requests.get(url, timeout=5)
                            if r.status_code == 200:
                                self._parse_ical_data(r.content, events, now)
                        except: pass
                except: pass
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
                    summary = str(component.get('summary', 'No Title'))
                    location = str(component.get('location', '')) if component.get('location') else ""
                    description = str(component.get('description', '')) if component.get('description') else ""
                    if component.get('dtstart'):
                        dtstart = component.get('dtstart').dt
                        if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                            dtstart = datetime.combine(dtstart, datetime.min.time()).astimezone()
                        if dtstart.tzinfo is None:
                            dtstart = dtstart.astimezone()
                        if dtstart >= now - timedelta(days=60):
                            if dtstart.date() == now.date(): date_str = f"Today, {dtstart.strftime('%H:%M')}"
                            elif dtstart.date() == (now + timedelta(days=1)).date(): date_str = f"Tomorrow, {dtstart.strftime('%H:%M')}"
                            else: date_str = dtstart.strftime("%a %d %b, %H:%M")
                            events_list.append({"title": summary, "date": date_str, "date_iso": dtstart.isoformat(), "sort_date": dtstart, "location": location, "description": description})
        except: pass

    @Property(list, notify=calendarChanged)
    def calendarEvents(self): return self._calendar_events

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
        
        # 1. Update Time
        if time_str != self._current_time:
            self._current_time = time_str
            self.timeChanged.emit()
            if now.second == 0:
                self._check_alarms(now)
                self._refresh_calendar()
                if now.minute % 15 == 0:
                    self._fetch_weather()

        # 2. Update Night Mode
        is_night = (now.hour >= 22 or now.hour < 5)
        if is_night != self._is_night_mode:
            self._is_night_mode = is_night
            self.nightModeChanged.emit()
            self._fetch_weather()
            
        # 3. Poll Tapo Light (Every 2 seconds)
        # We use a simple counter or just modulus on seconds if the timer is 1000ms
        if self.TAPO_IP and now.second % 2 == 0:
            self._check_light_status()

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
    def closeApp(self): sys.exit()
    @Slot()
    def snoozeAlarm(self):
        self.player.stop()
        new_time_str = (datetime.now() + timedelta(minutes=9)).strftime("%H:%M")
        database.add_alarm(new_time_str, str(datetime.now().weekday()))
        self.alarmsChanged.emit()
    @Slot(int)
    def deleteAlarm(self, id):
        conn = database.get_connection()
        conn.execute("DELETE FROM alarms WHERE id = ?", (id,))
        conn.commit(); conn.close()
        self.alarmsChanged.emit()
    @Slot(str, str)
    def createAlarm(self, t, d): database.add_alarm(t, d); self.alarmsChanged.emit()
    @Slot(int, str, str)
    def updateAlarm(self, id, t, d): database.update_alarm(id, t, d); self.alarmsChanged.emit()
    @Slot(int, bool)
    def toggleAlarm(self, id, active): database.toggle_alarm(id, active); self.alarmsChanged.emit()

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    backend = SmartClockBackend(app)
    engine.backend_reference = backend 
    engine.rootContext().setContextProperty("backend", backend)
    engine.load("main.qml")
    if not engine.rootObjects(): sys.exit(-1)
    sys.exit(app.exec())