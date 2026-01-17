from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock as KivyClock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from clock.alarms import AlarmManager, NextAlarm
from clock.storage import AlarmStore
from clock.audio import AudioEngine
from pathlib import Path




ALARM_WAV = Path("assets/sounds/alarm.wav")
RAMP_SECONDS = 30
SNOOZE_MINUTES = 9
DB_PATH = Path("alarms.db")


def format_countdown(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"


class AlarmClockUI(BoxLayout):
    def __init__(self, mgr: AlarmManager, **kwargs):
        super().__init__(orientation="vertical", padding=dp(24), spacing=dp(18), **kwargs)
        self.mgr = mgr
        self.audio = AudioEngine()


        self.time_label = Label(text="--:--:--", font_size=96, size_hint=(1, 0.55))
        self.next_label = Label(text="Next: --", font_size=28, size_hint=(1, 0.20))

        btn_row = BoxLayout(orientation="horizontal", spacing=dp(18), size_hint=(1, 0.25))

        self.snooze_btn = Button(text=f"Snooze {SNOOZE_MINUTES} min", font_size=28)
        self.stop_btn = Button(text="Stop", font_size=28)

        self.snooze_btn.bind(on_release=self.on_snooze)
        self.stop_btn.bind(on_release=self.on_stop)

        btn_row.add_widget(self.snooze_btn)
        btn_row.add_widget(self.stop_btn)

        self.add_widget(self.time_label)
        self.add_widget(self.next_label)
        self.add_widget(btn_row)

        # Track whether we're currently "ringing" (demo state for now)
        self.ringing_alarm_id: int | None = None

        # Update UI 5x/sec for smooth countdown
        KivyClock.schedule_interval(self.tick, 0.2)

    def tick(self, _dt):
        now = datetime.now()
        self.time_label.text = now.strftime("%H:%M:%S")

        nxt = self.mgr.compute_next(now)
        self.next_label.text = self._format_next(nxt, now)

        # Auto-fire behavior (for now): when next alarm time hits, mark fired.
        # In the next step we’ll trigger audio here.
        if nxt is not None:
            seconds = int((nxt.trigger_at - now).total_seconds())
            if seconds <= 0 and self.ringing_alarm_id is None:
                self.ringing_alarm_id = (nxt.alarm.id if nxt.alarm.id != -1 else None)
                self.mgr.mark_fired(nxt.alarm, now)
                self.audio.play_loop_with_ramp(ALARM_WAV, ramp_seconds=RAMP_SECONDS, start_volume=0.15, max_volume=1.0)
                self.next_label.text = f"RINGING: {nxt.alarm.label}"


    def _format_next(self, nxt: NextAlarm | None, now: datetime) -> str:
        if nxt is None:
            return "Next: (no alarms set)"
        seconds = int((nxt.trigger_at - now).total_seconds())
        return f"Next: {nxt.alarm.label} at {nxt.trigger_at.strftime('%H:%M')} (in {format_countdown(seconds)})"

    def on_snooze(self, *_args):
        # If we're currently ringing, snooze that alarm and stop sound
        if self.ringing_alarm_id is not None:
            self.mgr.snooze(SNOOZE_MINUTES, alarm_id=self.ringing_alarm_id)
            self.audio.stop()
            self.ringing_alarm_id = None
            return

        # Not ringing: allow snooze to act like "snooze the next scheduled alarm"
        nxt = self.mgr.compute_next(datetime.now())
        alarm_id = nxt.alarm.id if (nxt and nxt.alarm.id != -1) else None
        self.mgr.snooze(SNOOZE_MINUTES, alarm_id=alarm_id)

    def on_stop(self, *_args):
        # Stop = clear snooze + clear ringing state
        self.mgr.stop()
        self.audio.stop()
        self.ringing_alarm_id = None



class AlarmClockApp(App):
    def build(self):
        # Optional: set a reasonable window size for desktop testing
        Window.size = (800, 480)

        store = AlarmStore(DB_PATH)
        mgr = AlarmManager(store)
        return AlarmClockUI(mgr)


if __name__ == "__main__":
    AlarmClockApp().run()
