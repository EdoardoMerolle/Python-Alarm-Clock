from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random

from kivy.app import App
from kivy.clock import Clock as KivyClock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.carousel import Carousel
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, RoundedRectangle

from clock.alarms import AlarmManager, NextAlarm
from clock.storage import AlarmStore
from clock.audio import AudioEngine


# ---- Config ----
SNOOZE_MINUTES = 9
DB_PATH = Path("alarms.db")

ALARM_WAV = Path("assets/sounds/alarm.wav")
RAMP_SECONDS = 30

PHOTOS_DIR = Path("assets/photos")
PHOTO_INTERVAL_SECONDS = 12


# ---- Helpers ----
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


# ---- UI building blocks ----
class Card(BoxLayout):
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
    def __init__(self, **kwargs):
        fill = kwargs.pop("fill", (0.20, 0.52, 0.95, 1))
        fill_down = kwargs.pop("fill_down", (0.16, 0.45, 0.85, 1))
        radius = kwargs.pop("radius", dp(22))
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
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
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*(self._fill_down if self.state == "down" else self._fill))
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])


class HomePanel(BoxLayout):
    def __init__(self, mgr: AlarmManager, audio: AudioEngine, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.mgr = mgr
        self.audio = audio

        self.ringing_alarm_id: int | None = None
        self._ringing_label: str | None = None

        # Layered root so widgets can overlap
        self.root = FloatLayout()
        self.add_widget(self.root)

        # Background photo fills the whole panel
        self.photo = Image(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        try:
            self.photo.fit_mode = "cover"  # newer Kivy
        except Exception:
            pass
        self.root.add_widget(self.photo)

        # Overlay box anchored to bottom
        self.overlay = BoxLayout(
            orientation="vertical",
            padding=dp(24),
            spacing=dp(10),
            size_hint=(1, None),
            height=dp(220),
            pos_hint={"x": 0, "y": 0},
        )
        with self.overlay.canvas.before:
            Color(0, 0, 0, 0.55)
            self._overlay_rect = RoundedRectangle(pos=self.overlay.pos, size=self.overlay.size, radius=[0])
        self.overlay.bind(pos=self._update_overlay, size=self._update_overlay)

        # Overlay content
        self.time_label = Label(
            text="--:--",
            font_size=96,
            bold=True,
            halign="left",
            valign="middle",
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=dp(110),
        )
        self.time_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.date_label = Label(
            text="---",
            font_size=22,
            color=(0.85, 0.85, 0.90, 1),
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp(28),
        )
        self.date_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.next_label = Label(
            text="Next: (no alarms)",
            font_size=24,
            bold=True,
            color=(1, 1, 1, 1),
            halign="left",
            valign="middle",
        )
        self.next_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.overlay.add_widget(self.time_label)
        self.overlay.add_widget(self.date_label)
        self.overlay.add_widget(self.next_label)
        self.root.add_widget(self.overlay)

        # Buttons bar (overlaid at bottom)
        self.btn_card = Card(
            orientation="horizontal",
            padding=dp(14),
            spacing=dp(14),
            size_hint=(1, None),
            height=dp(96),
            pos_hint={"x": 0, "y": 0},
            bg=(0.10, 0.10, 0.12, 0.95),
        )

        self.snooze_btn = PillButton(
            text=f"Snooze {SNOOZE_MINUTES} min",
            fill=(0.20, 0.52, 0.95, 1),
            fill_down=(0.16, 0.45, 0.85, 1),
            font_size=26,
        )
        self.stop_btn = PillButton(
            text="Stop",
            fill=(0.92, 0.28, 0.28, 1),
            fill_down=(0.82, 0.22, 0.22, 1),
            font_size=26,
        )
        self.snooze_btn.bind(on_release=self.on_snooze)
        self.stop_btn.bind(on_release=self.on_stop)
        self.btn_card.add_widget(self.snooze_btn)
        self.btn_card.add_widget(self.stop_btn)

        self.root.add_widget(self.btn_card)
        self._set_alarm_controls_visible(False)

        # Photos
        self._photos = self._load_photos()
        self._photo_index = 0
        self._set_photo_initial()

        KivyClock.schedule_interval(self._tick, 0.2)
        KivyClock.schedule_interval(self._next_photo, PHOTO_INTERVAL_SECONDS)

    def _update_overlay(self, *_):
        self._overlay_rect.pos = self.overlay.pos
        self._overlay_rect.size = self.overlay.size

    def _set_alarm_controls_visible(self, visible: bool) -> None:
        if visible:
            self.btn_card.opacity = 1
            self.btn_card.disabled = False
            self.btn_card.height = dp(96)
        else:
            self.btn_card.opacity = 0
            self.btn_card.disabled = True
            self.btn_card.height = 0

    def _load_photos(self) -> list[Path]:
        if not PHOTOS_DIR.exists():
            return []
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        photos = [p for p in PHOTOS_DIR.iterdir() if p.suffix.lower() in exts and p.is_file()]
        random.shuffle(photos)
        return photos

    def _set_photo_initial(self) -> None:
        if not self._photos:
            self.photo.source = ""
            return
        self.photo.source = str(self._photos[0])
        self.photo.reload()

    def _next_photo(self, _dt) -> None:
        if not self._photos:
            return
        self._photo_index = (self._photo_index + 1) % len(self._photos)
        self.photo.source = str(self._photos[self._photo_index])
        self.photo.reload()

    def _tick(self, _dt) -> None:
        now = datetime.now()
        self.time_label.text = now.strftime("%H:%M")
        self.date_label.text = now.strftime("%A, %d %B %Y")
        self._set_alarm_controls_visible(self.ringing_alarm_id is not None)

        nxt = self.mgr.compute_next(now)

        if self.ringing_alarm_id is not None:
            self.next_label.text = f"RINGING: {self._ringing_label or 'Alarm'}"
            return

        if nxt is None:
            self.next_label.text = "Next: (no alarms set)"
            return

        seconds = int((nxt.trigger_at - now).total_seconds())
        self.next_label.text = (
            f"Next: {nxt.alarm.label} • {nxt.trigger_at.strftime('%H:%M')} "
            f"(in {format_countdown(seconds)})"
        )

        if seconds <= 0 and self.ringing_alarm_id is None:
            import traceback

            try:
                self.ringing_alarm_id = (nxt.alarm.id if nxt.alarm.id != -1 else None)
                self._ringing_label = nxt.alarm.label
                self.mgr.mark_fired(nxt.alarm, now)

                # Start audio (this is the most common crash point)
                self.audio.play_loop_with_ramp(
                    ALARM_WAV,
                    ramp_seconds=RAMP_SECONDS,
                    start_volume=0.15,
                    max_volume=1.0,
                )

                self._set_alarm_controls_visible(True)

            except Exception as e:
                # Keep app alive and show error on screen
                self.ringing_alarm_id = None
                self._ringing_label = None
                self._set_alarm_controls_visible(False)

                err = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                print("ERROR while firing alarm:\n", err)

                # Also show a short message in the UI
                self.next_label.text = "Alarm error (see console)."


    def on_snooze(self, *_):
        if self.ringing_alarm_id is not None:
            self.mgr.snooze(SNOOZE_MINUTES, alarm_id=self.ringing_alarm_id)
            self.audio.stop()
            self.ringing_alarm_id = None
            self._ringing_label = None
            self._set_alarm_controls_visible(False)
            return

        # Optional shortcut: snooze the next alarm even if nothing is ringing
        nxt = self.mgr.compute_next(datetime.now())
        alarm_id = nxt.alarm.id if (nxt and nxt.alarm.id != -1) else None
        self.mgr.snooze(SNOOZE_MINUTES, alarm_id=alarm_id)

    def on_stop(self, *_):
        self.mgr.stop()
        self.audio.stop()
        self.ringing_alarm_id = None
        self._ringing_label = None
        self._set_alarm_controls_visible(False)


class CalendarPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(18), spacing=dp(14), **kwargs)
        self.add_widget(Label(text="Calendar", font_size=52, bold=True, size_hint=(1, None), height=dp(70)))
        card = Card(orientation="vertical", padding=dp(18), spacing=dp(10))
        card.add_widget(Label(
            text="Placeholder for calendar.\n\nNext step options:\n• local .ics file\n• Google Calendar\n• Home Assistant calendar entities (later)",
            font_size=24,
            color=(0.85, 0.85, 0.90, 1),
        ))
        self.add_widget(card)


class AlarmsPanel(BoxLayout):
    def __init__(self, mgr: AlarmManager, **kwargs):
        super().__init__(orientation="vertical", padding=dp(18), spacing=dp(14), **kwargs)
        self.mgr = mgr

        header = BoxLayout(size_hint=(1, None), height=dp(70))
        header.add_widget(Label(text="Alarms", font_size=52, bold=True))

        self.add_btn = PillButton(
            text="Add one-shot +1 min (test)",
            fill=(0.25, 0.70, 0.35, 1),
            fill_down=(0.20, 0.62, 0.30, 1),
            font_size=22,
            size_hint=(None, 1),
            width=dp(300),
        )
        self.add_btn.bind(on_release=self.add_test_alarm)
        header.add_widget(self.add_btn)

        self.add_widget(header)

        self.list_card = Card(orientation="vertical", padding=dp(10), spacing=dp(8))
        self.scroll = ScrollView()
        self.list_box = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        self.list_card.add_widget(self.scroll)
        self.add_widget(self.list_card)

        KivyClock.schedule_interval(self.refresh, 1.0)
        self.refresh(0)

    def add_test_alarm(self, *_):
        from datetime import timedelta, date
        t = datetime.now() + timedelta(minutes=1)
        self.mgr.add_one_shot_alarm("Test alarm", t.strftime("%H:%M"), date.today(), True)
        self.refresh(0)

    def refresh(self, _dt):
        self.list_box.clear_widgets()
        alarms = self.mgr.list_alarms()

        if not alarms:
            self.list_box.add_widget(Label(text="No alarms yet.", font_size=24, color=(0.85, 0.85, 0.90, 1),
                                           size_hint_y=None, height=dp(40)))
            return

        for a in alarms:
            row = Card(orientation="horizontal", padding=dp(12), spacing=dp(12), size_hint_y=None, height=dp(72),
                       bg=(0.16, 0.16, 0.18, 1))

            label = f"{a.label} • {a.hour:02d}:{a.minute:02d}"
            if a.one_shot_date:
                label += f" • {a.one_shot_date}"

            row.add_widget(Label(text=label, font_size=22, halign="left", valign="middle"))
            toggle = PillButton(
                text="On" if a.enabled else "Off",
                fill=(0.20, 0.52, 0.95, 1) if a.enabled else (0.35, 0.35, 0.40, 1),
                fill_down=(0.16, 0.45, 0.85, 1) if a.enabled else (0.30, 0.30, 0.34, 1),
                font_size=22,
                size_hint=(None, 1),
                width=dp(110),
            )
            toggle.bind(on_release=lambda _btn, alarm_id=a.id, enabled=a.enabled: self._toggle(alarm_id, enabled))
            row.add_widget(toggle)

            self.list_box.add_widget(row)

    def _toggle(self, alarm_id: int, enabled: bool):
        self.mgr.set_enabled(alarm_id, not enabled)
        self.refresh(0)


class AppSettingsPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(18), spacing=dp(14), **kwargs)
        self.add_widget(Label(text="Settings", font_size=52, bold=True, size_hint=(1, None), height=dp(70)))
        card = Card(orientation="vertical", padding=dp(18), spacing=dp(10))
        card.add_widget(Label(
            text="Placeholder.\n\nLater:\n• photo interval\n• brightness/night mode\n• alarm sound + ramp duration\n• Wi-Fi status, etc.",
            font_size=24,
            color=(0.85, 0.85, 0.90, 1),
        ))
        self.add_widget(card)


# ---- Root app ----
class SmartDisplayRoot(BoxLayout):
    def __init__(self, mgr: AlarmManager, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.audio = AudioEngine()

        self.carousel = Carousel(direction="right", loop=False)
        self.carousel.add_widget(HomePanel(mgr, self.audio))
        self.carousel.add_widget(CalendarPanel())
        self.carousel.add_widget(AlarmsPanel(mgr))
        self.carousel.add_widget(AppSettingsPanel())

        self.add_widget(self.carousel)


class SmartDisplayApp(App):
    def build(self):
        Window.size = (800, 480)  # nice for Pi touchscreens too
        # Window.fullscreen = True  # enable later when you're ready

        store = AlarmStore(DB_PATH)
        mgr = AlarmManager(store)
        return SmartDisplayRoot(mgr)


if __name__ == "__main__":
    SmartDisplayApp().run()
