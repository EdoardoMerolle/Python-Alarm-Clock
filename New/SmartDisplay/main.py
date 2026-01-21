import sys
import os
import random  # <--- NEW IMPORT
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import database

class SmartClockBackend(QObject):
    timeChanged = Signal()
    alarmTriggered = Signal(str)
    alarmsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_time = ""
        
        database.init_db()

        # Audio Setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        base_path = Path(__file__).resolve().parent
        sound_path = base_path / "assets" / "sounds" / "alarm.mp3"
        
        self.player.setSource(QUrl.fromLocalFile(str(sound_path)))
        self.audio_output.setVolume(1.0)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    @Property(list, constant=True)
    def imageList(self):
        """Returns a list of absolute file URLs for images"""
        image_urls = []
        base_path = Path(__file__).resolve().parent
        folder_path = base_path / "assets" / "images"
        
        if folder_path.exists():
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    full_path = folder_path / file
                    image_urls.append(QUrl.fromLocalFile(str(full_path)).toString())
        
        # FIX: Randomize the list instead of sorting it
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

    def _check_alarms(self, now_dt):
        current_time_str = now_dt.strftime("%H:%M")
        current_weekday = str(now_dt.weekday()) 
        
        active_alarms = database.get_active_alarms()
        
        for alarm in active_alarms:
            if alarm['time'] == current_time_str:
                days = alarm['days'] 
                if days == "Daily" or current_weekday in days.split(","):
                    print(f"ALARM TRIGGERED: {alarm['id']}")
                    if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                        self.player.play()
                    self.alarmTriggered.emit("Wake Up!")

    # --- Properties ---
    @Property(str, notify=timeChanged)
    def currentTime(self):
        return self._current_time

    @Property(list, notify=alarmsChanged)
    def alarmList(self):
        return database.get_all_alarms()

    # --- Slots ---
    @Slot()
    def stopAlarm(self):
        self.player.stop()

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

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())