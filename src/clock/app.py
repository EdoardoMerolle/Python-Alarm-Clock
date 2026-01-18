from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
import random
from typing import Iterable, Optional

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
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.animation import Animation

from clock.alarms import AlarmManager
from clock.storage import AlarmStore
from clock.audio import AudioEngine


# ---- Config ----
SNOOZE_MINUTES = 9
DB_PATH = Path("alarms.db")

ALARM_WAV = Path("assets/sounds/alarm.wav")
RAMP_SECONDS = 30

PHOTOS_DIR = Path("/home/edoardo/Pictures/camera pics")
PHOTO_INTERVAL_SECONDS = 12
PHOTO_PLACEHOLDER = Path("assets/placeholder.jpg")  # optional fallback


# ---- Helpers ----
def debounce(widget, seconds: float = 0.35):
    """Disable a widget briefly after it fires to prevent double-presses."""
    widget.disabled = True
    def _reenable(_dt):
        widget.disabled = False
    KivyClock.schedule_once(_reenable, seconds)
    
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


def _weekdays_from_alarm_obj(alarm) -> Optional[list[bool]]:
    """
    Best-effort decoding of weekdays from whatever the alarm object exposes.
    Supports:
      - alarm.weekdays as list[bool] length 7
      - alarm.weekdays_mask or alarm.weekdays as int bitmask (bit0..bit6)
    Returns None if unknown / not present.
    """
    # list[bool]
    w = getattr(alarm, "weekdays", None)
    if isinstance(w, (list, tuple)) and len(w) == 7 and all(isinstance(x, bool) for x in w):
        return list(w)

    # int mask (try weekdays_mask first, then weekdays if it's int)
    mask = getattr(alarm, "weekdays_mask", None)
    if isinstance(mask, int):
        return [((mask >> i) & 1) == 1 for i in range(7)]

    if isinstance(w, int):
        return [((w >> i) & 1) == 1 for i in range(7)]

    return None


def _safe_fit_cover(img: Image) -> None:
    # Kivy versions differ; try the modern property but don’t crash.
    try:
        img.fit_mode = "cover"
    except Exception:
        pass


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
        self.always_release = True

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.bold = True
        self.halign = "center"
        self.valign = "middle"

        self._radius = radius
        self._fill = fill
        self._fill_down = fill_down

        with self.canvas.before:
            Color(*self._fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])

        self.bind(pos=self._update, size=self._on_size_change, state=self._state_update)

    def _update(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _on_size_change(self, *_):
        self._update()
        self.text_size = self.size

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

        # Ringing state (separate latch so we don’t retrigger on “id=-1” alarms)
        self._is_ringing: bool = False
        self._ringing_alarm_id: Optional[int] = None
        self._ringing_label: Optional[str] = None

        # Layered root so widgets can overlap
        self.root = FloatLayout()
        self.add_widget(self.root)

        # Two photo layers for cross-fade
        self.photo_a = Image(size_hint=(1, 1), pos_hint={"x": 0, "y": 0}, opacity=1)
        self.photo_b = Image(size_hint=(1, 1), pos_hint={"x": 0, "y": 0}, opacity=0)
        _safe_fit_cover(self.photo_a)
        _safe_fit_cover(self.photo_b)

        self.root.add_widget(self.photo_a)
        self.root.add_widget(self.photo_b)

        self._photo_front = self.photo_a
        self._photo_back = self.photo_b

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
            size_hint=(1, None),
            height=dp(50),
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
        if self._photos:
            self._photo_front.source = str(self._photos[0])
            self._photo_front.opacity = 1
            self._photo_back.opacity = 0
            return

        if PHOTO_PLACEHOLDER.exists():
            self._photo_front.source = str(PHOTO_PLACEHOLDER)
            self._photo_front.opacity = 1
            self._photo_back.opacity = 0

    def _next_photo(self, _dt) -> None:
        if not self._photos:
            return

        self._photo_index = (self._photo_index + 1) % len(self._photos)
        next_path = str(self._photos[self._photo_index])

        back = self._photo_back
        front = self._photo_front

        back.source = next_path
        back.opacity = 0
        back.reload()

        def start_fade(_):
            Animation(opacity=1, duration=1.2).start(back)
            Animation(opacity=0, duration=1.2).start(front)
            self._photo_front, self._photo_back = back, front

        KivyClock.schedule_once(start_fade, 0)

    def _tick(self, _dt) -> None:
        import traceback
        try:
            now = datetime.now()
            self.time_label.text = now.strftime("%H:%M")
            self.date_label.text = now.strftime("%A, %d %B %Y")
            self._set_alarm_controls_visible(self._is_ringing)

            nxt = self.mgr.compute_next(now)

            if self._is_ringing:
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

            if seconds <= 0 and not self._is_ringing:
                # Latch ringing state immediately so we don’t retrigger
                self._is_ringing = True
                self._ringing_alarm_id = getattr(nxt.alarm, "id", None)
                self._ringing_label = getattr(nxt.alarm, "label", "Alarm")

                self.mgr.mark_fired(nxt.alarm, now)
                self.audio.play_loop_with_ramp(
                    ALARM_WAV,
                    ramp_seconds=RAMP_SECONDS,
                    start_volume=0.15,
                    max_volume=1.0,
                )
                self._set_alarm_controls_visible(True)

        except Exception as e:
            print("ERROR in HomePanel._tick:\n", "".join(traceback.format_exception(type(e), e, e.__traceback__)))
            self.next_label.text = "UI error (see console)"

    def _clear_ringing(self) -> None:
        self.audio.stop()
        self._is_ringing = False
        self._ringing_alarm_id = None
        self._ringing_label = None
        self._set_alarm_controls_visible(False)

    def on_snooze(self, *_):
        if self._is_ringing:
            # snooze specific ringing alarm if possible
            self.mgr.snooze(SNOOZE_MINUTES, alarm_id=self._ringing_alarm_id)
            self._clear_ringing()
            return

        # Optional shortcut: snooze the next alarm even if nothing is ringing
        nxt = self.mgr.compute_next(datetime.now())
        alarm_id = getattr(nxt.alarm, "id", None) if nxt else None
        self.mgr.snooze(SNOOZE_MINUTES, alarm_id=alarm_id)

    def on_stop(self, *_):
        self.mgr.stop()
        self._clear_ringing()


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
        self.editor_open = False

        # Header (title + add/close button)
        header = BoxLayout(size_hint=(1, None), height=dp(64), spacing=dp(16))

        title = Label(
            text="Alarms",
            font_size=48,
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp(64),
        )
        title.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.add_btn = PillButton(
            text="  Add  ",
            fill=(0.25, 0.70, 0.35, 1),
            fill_down=(0.20, 0.62, 0.30, 1),
            font_size=22,
            size_hint=(None, None),
            width=dp(220),
            height=dp(60),
        )
        self.add_btn.bind(on_release=self.toggle_editor)

        header.add_widget(title)
        header.add_widget(self.add_btn)
        self.add_widget(header)

        # Editor card (initially hidden)
        self.editor_card = Card(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10),
            size_hint=(1, None),
            height=0,
            opacity=0,
        )
        self.editor_card.disabled = True
        self.add_widget(self.editor_card)

        # Editor state
        self.new_label = "Alarm"
        self.new_hour = 7
        self.new_minute = 0
        self.weekdays = [True, True, True, True, True, False, False]  # Mon..Sun
        self.one_shot_today = False

        self.editing_alarm_id: Optional[int] = None
        self.editing_alarm_was_enabled: bool = True
        self.editing_alarm_is_oneshot: bool = False

        self._build_editor_ui()

        # Scrollable list
        self.scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        self.list_box = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=dp(10))
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        self.add_widget(self.scroll)

        # Refresh less aggressively
        KivyClock.schedule_interval(self.refresh, 2.0)
        self.refresh(0)

    def _build_editor_ui(self):
        self.editor_card.clear_widgets()

        # Time display at top
        self.time_display = Label(
            text=self._time_text(),
            font_size=36,
            bold=True,
            size_hint=(1, None),
            height=dp(50),
        )
        self.editor_card.add_widget(self.time_display)

        # Label selector
        row1 = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        self.label_display = Label(
            text=f"Label: {self.new_label}",
            font_size=18,
            size_hint=(0.6, 1),
            halign="left",
            valign="middle",
        )
        self.label_display.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        label_btn = PillButton(
            text="Change",
            font_size=16,
            size_hint=(0.4, 1),
            fill=(0.35, 0.35, 0.40, 1),
            fill_down=(0.30, 0.30, 0.34, 1),
        )
        label_btn.bind(on_release=self._cycle_label)
        row1.add_widget(self.label_display)
        row1.add_widget(label_btn)
        self.editor_card.add_widget(row1)

        # Time controls
        row2 = BoxLayout(size_hint=(1, None), height=dp(60), spacing=dp(8))

        h_minus = PillButton(text="H-", font_size=16, size_hint=(0.18, 1),
                             fill=(0.35, 0.35, 0.40, 1), fill_down=(0.30, 0.30, 0.34, 1))
        h_plus = PillButton(text="H+", font_size=16, size_hint=(0.18, 1),
                            fill=(0.35, 0.35, 0.40, 1), fill_down=(0.30, 0.30, 0.34, 1))
        m_minus = PillButton(text="M-", font_size=16, size_hint=(0.18, 1),
                             fill=(0.35, 0.35, 0.40, 1), fill_down=(0.30, 0.30, 0.34, 1))
        m_plus = PillButton(text="M+", font_size=16, size_hint=(0.18, 1),
                            fill=(0.35, 0.35, 0.40, 1), fill_down=(0.30, 0.30, 0.34, 1))
        m_plus_30 = PillButton(text="+30m", font_size=14, size_hint=(0.28, 1),
                               fill=(0.25, 0.70, 0.35, 1), fill_down=(0.20, 0.62, 0.30, 1))

        h_minus.bind(on_release=lambda *_: self._adjust_time("h", -1))
        h_plus.bind(on_release=lambda *_: self._adjust_time("h", +1))
        m_minus.bind(on_release=lambda *_: self._adjust_time("m", -1))
        m_plus.bind(on_release=lambda *_: self._adjust_time("m", +1))
        m_plus_30.bind(on_release=lambda *_: self._adjust_time("m", +30))

        row2.add_widget(h_minus)
        row2.add_widget(h_plus)
        row2.add_widget(m_minus)
        row2.add_widget(m_plus)
        row2.add_widget(m_plus_30)
        self.editor_card.add_widget(row2)

        # Weekday toggles (Mon..Sun)
        row3 = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(6))
        days = ["M", "T", "W", "Th", "F", "Sa", "Su"]
        self.day_btns = []
        for i, d in enumerate(days):
            on = self.weekdays[i]
            btn = PillButton(
                text=d,
                font_size=14,
                size_hint=(1, 1),
                fill=(0.20, 0.52, 0.95, 1) if on else (0.35, 0.35, 0.40, 1),
                fill_down=(0.16, 0.45, 0.85, 1) if on else (0.30, 0.30, 0.34, 1),
            )
            btn.bind(on_release=lambda _b, idx=i: self._toggle_day(idx))
            self.day_btns.append(btn)
            row3.add_widget(btn)
        self.editor_card.add_widget(row3)

        # One-shot toggle
        row4 = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        self.oneshot_btn = PillButton(
            text="One-shot: ON" if self.one_shot_today else "One-shot: OFF",
            font_size=16,
            size_hint=(0.6, 1),
            fill=(0.20, 0.52, 0.95, 1) if self.one_shot_today else (0.35, 0.35, 0.40, 1),
            fill_down=(0.16, 0.45, 0.85, 1) if self.one_shot_today else (0.30, 0.30, 0.34, 1),
        )
        self.oneshot_btn.bind(on_release=self._toggle_oneshot)
        row4.add_widget(self.oneshot_btn)
        self.editor_card.add_widget(row4)

        # Buttons: Save/Cancel
        row5 = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        save_btn = PillButton(
            text="Save",
            font_size=18,
            fill=(0.25, 0.70, 0.35, 1),
            fill_down=(0.20, 0.62, 0.30, 1),
        )
        cancel_btn = PillButton(
            text="Cancel",
            font_size=18,
            fill=(0.60, 0.60, 0.65, 1),
            fill_down=(0.50, 0.50, 0.55, 1),
        )
        save_btn.bind(on_release=self._save_alarm)
        cancel_btn.bind(on_release=lambda *_: self.toggle_editor(force_close=True))
        row5.add_widget(save_btn)
        row5.add_widget(cancel_btn)
        self.editor_card.add_widget(row5)

    def toggle_editor(self, *_args, force_close: bool = False):
        if force_close:
            self.editor_open = False
            self.editing_alarm_id = None
        else:
            self.editor_open = not self.editor_open

        if self.editor_open:
            self.editor_card.height = dp(310)
            self.editor_card.opacity = 1
            self.editor_card.disabled = False
            self.add_btn.text = "Close"
        else:
            self.editor_card.height = 0
            self.editor_card.opacity = 0
            self.editor_card.disabled = True
            self.add_btn.text = "  Add  "
            self.editing_alarm_id = None

    def _time_text(self) -> str:
        return f"{self.new_hour:02d}:{self.new_minute:02d}"

    def _adjust_time(self, which: str, delta: int):
        if which == "h":
            self.new_hour = (self.new_hour + delta) % 24
        else:
            # carry minutes into hours properly
            total = (self.new_hour * 60 + self.new_minute + delta) % (24 * 60)
            self.new_hour = total // 60
            self.new_minute = total % 60
        self.time_display.text = self._time_text()

    def _toggle_day(self, idx: int):
        self.weekdays[idx] = not self.weekdays[idx]
        btn = self.day_btns[idx]
        on = self.weekdays[idx]
        btn._fill = (0.20, 0.52, 0.95, 1) if on else (0.35, 0.35, 0.40, 1)
        btn._fill_down = (0.16, 0.45, 0.85, 1) if on else (0.30, 0.30, 0.34, 1)
        btn._state_update()

    def _toggle_oneshot(self, *_):
        self.one_shot_today = not self.one_shot_today
        self._build_editor_ui()

    def _cycle_label(self, *_):
        presets = ["Alarm", "Wake up", "Workout", "School", "Meeting", "Medicine"]
        try:
            i = presets.index(self.new_label)
        except ValueError:
            i = 0
        self.new_label = presets[(i + 1) % len(presets)]
        self.label_display.text = f"Label: {self.new_label}"

    def _save_alarm(self, *_):
        hhmm = f"{self.new_hour:02d}:{self.new_minute:02d}"

        # Preserve enabled state if editing (best-effort)
        enabled = True
        if self.editing_alarm_id is not None:
            enabled = self.editing_alarm_was_enabled
            self.mgr.delete(self.editing_alarm_id)

        if self.one_shot_today:
            self.mgr.add_one_shot_alarm(self.new_label, hhmm, date.today(), enabled=enabled)
        else:
            days = [i for i, on in enumerate(self.weekdays) if on]
            if not days:
                days = list(range(7))
            self.mgr.add_weekly_alarm(self.new_label, hhmm, days, enabled=enabled)

        self.toggle_editor(force_close=True)
        self.refresh(0)

    def refresh(self, _dt):
        self.list_box.clear_widgets()
        alarms = self.mgr.list_alarms()

        if not alarms:
            self.list_box.add_widget(Label(
                text="No alarms yet.",
                font_size=22,
                color=(0.85, 0.85, 0.90, 1),
                size_hint_y=None,
                height=dp(50),
            ))
            return

        for a in alarms:
            row = Card(
                orientation="horizontal",
                padding=dp(12),
                spacing=dp(10),
                size_hint_y=None,
                height=dp(70),
                bg=(0.16, 0.16, 0.18, 1),
            )

            label = f"{a.label} • {a.hour:02d}:{a.minute:02d}"
            if getattr(a, "one_shot_date", None):
                label += f" • {a.one_shot_date}"

            lbl_widget = Label(text=label, font_size=18, size_hint=(0.40, 1), halign="left", valign="middle")
            lbl_widget.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            row.add_widget(lbl_widget)

            edit_btn = PillButton(
                text="Edit",
                fill=(0.40, 0.60, 0.95, 1),
                fill_down=(0.35, 0.55, 0.85, 1),
                font_size=16,
                size_hint=(0.20, 1),
            )
            edit_btn.bind(on_release=lambda _btn, alarm_id=a.id: self._load_alarm_for_edit(alarm_id))
            row.add_widget(edit_btn)

            toggle = PillButton(
                text="ON" if a.enabled else "OFF",
                fill=(0.25, 0.70, 0.35, 1) if a.enabled else (0.50, 0.50, 0.55, 1),
                fill_down=(0.20, 0.62, 0.30, 1) if a.enabled else (0.45, 0.45, 0.50, 1),
                font_size=16,
                size_hint=(0.20, 1),
            )
            toggle.bind(on_release=lambda _btn, alarm_id=a.id, enabled=a.enabled: self._toggle(alarm_id, enabled))
            row.add_widget(toggle)

            del_btn = PillButton(
                text="Del",
                fill=(0.92, 0.28, 0.28, 1),
                fill_down=(0.82, 0.22, 0.22, 1),
                font_size=16,
                size_hint=(0.20, 1),
            )
            del_btn.bind(on_release=lambda _btn, alarm_id=a.id: self._delete(alarm_id))
            row.add_widget(del_btn)

            self.list_box.add_widget(row)

    def _toggle(self, alarm_id: int, enabled: bool):
        self.mgr.set_enabled(alarm_id, not enabled)
        self.refresh(0)

    def _delete(self, alarm_id: int):
        self.mgr.delete(alarm_id)
        self.refresh(0)

    def _load_alarm_for_edit(self, alarm_id: int):
        alarms = self.mgr.list_alarms()
        alarm = next((a for a in alarms if a.id == alarm_id), None)
        if not alarm:
            return

        self.editing_alarm_id = alarm_id
        self.editing_alarm_was_enabled = bool(getattr(alarm, "enabled", True))

        self.new_label = alarm.label
        self.new_hour = alarm.hour
        self.new_minute = alarm.minute

        self.editing_alarm_is_oneshot = getattr(alarm, "one_shot_date", None) is not None
        self.one_shot_today = self.editing_alarm_is_oneshot

        if not self.editing_alarm_is_oneshot:
            decoded = _weekdays_from_alarm_obj(alarm)
            if decoded is not None:
                self.weekdays = decoded
            # else: keep current selection as a fallback

        self._build_editor_ui()

        if not self.editor_open:
            self.toggle_editor()


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


class SmartCarousel(Carousel):
    def on_touch_down(self, touch):
        if Carousel.on_touch_down(self, touch):
            return True
        return Widget.on_touch_down(self, touch)


class SmartDisplayRoot(BoxLayout):
    def __init__(self, mgr: AlarmManager, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.audio = AudioEngine()

        self.carousel = SmartCarousel(direction="right", loop=False)
        self.carousel.scroll_distance = dp(120)
        self.carousel.scroll_timeout = 300

        # Pages
        self.carousel.add_widget(HomePanel(mgr, self.audio))
        self.carousel.add_widget(AlarmsPanel(mgr))
        self.carousel.add_widget(CalendarPanel())
        # self.carousel.add_widget(AppSettingsPanel())  # enable when ready

        self.carousel.bind(index=self._on_carousel_index_change)
        self.add_widget(self.carousel)

        # Page indicator dots (dynamic)
        self.indicator_box = BoxLayout(
            size_hint=(1, None),
            height=dp(30),
            spacing=dp(12),
            padding=dp(12),
        )
        with self.indicator_box.canvas.before:
            Color(0.10, 0.10, 0.12, 1)
            self._indicator_bg = RoundedRectangle(pos=self.indicator_box.pos, size=self.indicator_box.size, radius=[0])
        self.indicator_box.bind(pos=self._update_indicator_bg, size=self._update_indicator_bg)

        self.indicator_dots: list[Widget] = []
        self._build_dots()

        self.add_widget(self.indicator_box)

    def _build_dots(self):
        self.indicator_box.clear_widgets()
        self.indicator_dots.clear()

        num_pages = len(self.carousel.slides)
        for i in range(num_pages):
            dot = Widget(size_hint=(None, 1), width=dp(14))
            color = (0.20, 0.52, 0.95, 1) if i == self.carousel.index else (0.40, 0.40, 0.45, 1)
            with dot.canvas:
                Color(*color)
                dot._circle = RoundedRectangle(pos=dot.pos, size=dot.size, radius=[dp(7)])
            dot._color = color
            dot.bind(pos=self._update_dot, size=self._update_dot)
            self.indicator_dots.append(dot)
            self.indicator_box.add_widget(dot)

    def _update_indicator_bg(self, *_):
        self._indicator_bg.pos = self.indicator_box.pos
        self._indicator_bg.size = self.indicator_box.size

    def _update_dot(self, dot, *_):
        dot._circle.pos = dot.pos
        dot._circle.size = dot.size

    def _on_carousel_index_change(self, _carousel, index: int):
        # If slides ever change, rebuild
        if len(self.indicator_dots) != len(self.carousel.slides):
            self._build_dots()

        for i, dot in enumerate(self.indicator_dots):
            new_color = (0.20, 0.52, 0.95, 1) if i == index else (0.40, 0.40, 0.45, 1)
            dot.canvas.clear()
            with dot.canvas:
                Color(*new_color)
                dot._circle = RoundedRectangle(pos=dot.pos, size=dot.size, radius=[dp(7)])


class SmartDisplayApp(App):
    def build(self):
        Window.size = (1024, 600)  # nice for Pi touchscreens too
        # Window.fullscreen = True  # enable later when you're ready

        store = AlarmStore(DB_PATH)
        mgr = AlarmManager(store)
        return SmartDisplayRoot(mgr)


if __name__ == "__main__":
    SmartDisplayApp().run()
