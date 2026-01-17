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
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle

from clock.alarms import AlarmManager, NextAlarm
from clock.storage import AlarmStore
from clock.audio import AudioEngine


SNOOZE_MINUTES = 9
DB_PATH = Path("alarms.db")
ALARM_WAV = Path("assets/sounds/alarm.wav")
RAMP_SECONDS = 30


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


class Card(BoxLayout):
    """A rounded rectangle background container."""
    def __init__(self, radius=20, bg=(0.12, 0.12, 0.14, 1), **kwargs):
        super().__init__(**kwargs)
        self._radius = radius
        self._bg = bg
        with self.canvas.before:
            Color(*self._bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class PillButton(Button):
    """Big rounded button."""
    def __init__(self, **kwargs):
        # Remove custom kwargs BEFORE Kivy sees them
        fill = kwargs.pop("fill", (0.20, 0.52, 0.95, 1))
        fill_down = kwargs.pop("fill_down", (0.16, 0.45, 0.85, 1))
        radius = kwargs.pop("radius", dp(22))

        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)  # draw our own
        self.color = (1, 1, 1, 1)
        self.bold = True

        self._radius = radius
        self._fill = fill
        self._fill_down = fill_down

        with self.canvas.before:
            Color(*self._fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])

        self.bind(pos=self._update, size=self._update, state=self._state_update)

    def _update(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _state_update(self, *_):
        # simple press effect
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*(self._fill_down if self.state == "down" else self._fill))
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])



class AlarmClockUI(BoxLayout):
    def __init__(self, mgr: AlarmManager, **kwargs):
        super().__init__(orientation="vertical", padding=dp(18), spacing=dp(14), **kwargs)
        self.mgr = mgr
        self.audio = AudioEngine()

        self.ringing_alarm_id: int | None = None
        self._ringing_label: str | None = None

        # Top: Time card
        self.time_card = Card(orientation="vertical", padding=dp(18), spacing=dp(6), size_hint=(1, 0.55))
        self.time_label = Label(text="--:--", font_size=110, bold=True, color=(1, 1, 1, 1))
        self.date_label = Label(text="---", font_size=24, color=(0.80, 0.80, 0.86, 1))
        self.time_card.add_widget(self._center(self.time_label))
        self.time_card.add_widget(self._center(self.date_label))

        # Middle: Next alarm card
        self.next_card = Card(orientation="vertical", padding=dp(18), spacing=dp(10), size_hint=(1, 0.22))
        self.next_title = Label(text="NEXT ALARM", font_size=18, bold=True, color=(0.70, 0.72, 0.78, 1),
                                size_hint=(1, None), height=dp(22), halign="left", valign="middle")
        self.next_title.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        self.next_main = Label(text="(no alarms set)", font_size=30, bold=True, color=(1, 1, 1, 1),
                               halign="left", valign="middle")
        self.next_main.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        self.next_sub = Label(text="", font_size=20, color=(0.80, 0.80, 0.86, 1),
                              halign="left", valign="middle")
        self.next_sub.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        self.next_card.add_widget(self.next_title)
        self.next_card.add_widget(self.next_main)
        self.next_card.add_widget(self.next_sub)

        # Bottom: Buttons card
        self.btn_card = Card(orientation="horizontal", padding=dp(14), spacing=dp(14), size_hint=(1, 0.23))

        self.snooze_btn = PillButton(
            text=f"Snooze {SNOOZE_MINUTES} min",
            fill=(0.20, 0.52, 0.95, 1),
            fill_down=(0.16, 0.45, 0.85, 1),
            font_size=28,
        )
        self.stop_btn = PillButton(
            text="Stop",
            fill=(0.92, 0.28, 0.28, 1),
            fill_down=(0.82, 0.22, 0.22, 1),
            font_size=28,
        )

        self.snooze_btn.bind(on_release=self.on_snooze)
        self.stop_btn.bind(on_release=self.on_stop)

        self.btn_card.add_widget(self.snooze_btn)
        self.btn_card.add_widget(self.stop_btn)

        self.add_widget(self.time_card)
        self.add_widget(self.next_card)
        self.add_widget(self.btn_card)

        # Update UI 5x/sec
        KivyClock.schedule_interval(self.tick, 0.2)

    def _center(self, widget: Widget) -> BoxLayout:
        box = BoxLayout(size_hint=(1, None), height=widget.font_size + dp(10))
        box.add_widget(widget)
        return box

    def tick(self, _dt):
        now = datetime.now()

        # Time / date
        self.time_label.text = now.strftime("%H:%M")
        self.date_label.text = now.strftime("%A, %d %B %Y")

        nxt = self.mgr.compute_next(now)
        self._render_next(nxt, now)

        # Fire
        if nxt is not None:
            seconds = int((nxt.trigger_at - now).total_seconds())
            if seconds <= 0 and self.ringing_alarm_id is None:
                self.ringing_alarm_id = (nxt.alarm.id if nxt.alarm.id != -1 else None)
                self._ringing_label = nxt.alarm.label
                self.mgr.mark_fired(nxt.alarm, now)
                self.audio.play_loop_with_ramp(
                    ALARM_WAV,
                    ramp_seconds=RAMP_SECONDS,
                    start_volume=0.15,
                    max_volume=1.0,
                )

    def _render_next(self, nxt: NextAlarm | None, now: datetime) -> None:
        if self.ringing_alarm_id is not None:
            self.next_main.text = f"RINGING: {self._ringing_label or 'Alarm'}"
            self.next_sub.text = "Tap Snooze or Stop"
            return

        if nxt is None:
            self.next_main.text = "(no alarms set)"
            self.next_sub.text = "Create an alarm to get started"
            return

        seconds = int((nxt.trigger_at - now).total_seconds())
        self.next_main.text = f"{nxt.alarm.label} • {nxt.trigger_at.strftime('%H:%M')}"
        self.next_sub.text = f"In {format_countdown(seconds)}"

    def on_snooze(self, *_args):
        # If ringing: snooze that alarm
        if self.ringing_alarm_id is not None:
            self.mgr.snooze(SNOOZE_MINUTES, alarm_id=self.ringing_alarm_id)
            self.audio.stop()
            self.ringing_alarm_id = None
            self._ringing_label = None
            return

        # Otherwise: snooze the next alarm (handy shortcut)
        nxt = self.mgr.compute_next(datetime.now())
        alarm_id = nxt.alarm.id if (nxt and nxt.alarm.id != -1) else None
        self.mgr.snooze(SNOOZE_MINUTES, alarm_id=alarm_id)

    def on_stop(self, *_args):
        self.mgr.stop()
        self.audio.stop()
        self.ringing_alarm_id = None
        self._ringing_label = None


class AlarmClockApp(App):
    def build(self):
        # Desktop testing size (Pi touchscreen is often 800x480 too)
        Window.size = (800, 480)

        store = AlarmStore(DB_PATH)
        mgr = AlarmManager(store)
        return AlarmClockUI(mgr)


if __name__ == "__main__":
    AlarmClockApp().run()
