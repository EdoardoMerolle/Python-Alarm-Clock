from __future__ import annotations

import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import simpleaudio as sa


def ensure_default_alarm_wav(path: Path) -> None:
    """
    Creates a simple beep WAV if no alarm sound exists.
    """
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    duration_s = 0.6
    freq = 880.0

    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    tone = 0.35 * np.sin(2 * np.pi * freq * t)  # -1..1 float
    # fade out to reduce clicks
    fade = np.linspace(1.0, 0.0, len(tone))
    tone = tone * fade

    audio = np.int16(tone * 32767)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())


@dataclass
class AudioStatus:
    is_playing: bool
    volume: float


class AudioEngine:
    """
    WAV playback with looping + software volume ramp (cross-platform).
    """

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._status = AudioStatus(is_playing=False, volume=0.0)

    def status(self) -> AudioStatus:
        with self._lock:
            return AudioStatus(is_playing=self._status.is_playing, volume=self._status.volume)

    def stop(self) -> None:
        self._stop_event.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=2.0)
        with self._lock:
            self._status = AudioStatus(is_playing=False, volume=0.0)

    def play_loop_with_ramp(
        self,
        wav_path: Path,
        ramp_seconds: int = 30,
        start_volume: float = 0.15,
        max_volume: float = 1.0,
        loop_pause_ms: int = 50,
    ) -> None:
        """
        Starts a background thread that loops the wav and ramps volume up over ramp_seconds.
        Calling stop() will stop it.
        """
        self.stop()
        self._stop_event.clear()

        ensure_default_alarm_wav(wav_path)

        thread = threading.Thread(
            target=self._run_loop,
            args=(wav_path, ramp_seconds, start_volume, max_volume, loop_pause_ms),
            daemon=True,
        )
        self._thread = thread
        thread.start()

    def _run_loop(
        self,
        wav_path: Path,
        ramp_seconds: int,
        start_volume: float,
        max_volume: float,
        loop_pause_ms: int,
    ) -> None:
        # Load wav frames
        with wave.open(str(wav_path), "rb") as wf:
            nch = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            fr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        if sampwidth != 2:
            raise ValueError("Only 16-bit PCM WAV is supported (sampwidth=2).")

        data = np.frombuffer(frames, dtype=np.int16)

        with self._lock:
            self._status = AudioStatus(is_playing=True, volume=start_volume)

        started = time.time()
        while not self._stop_event.is_set():
            elapsed = time.time() - started
            if ramp_seconds <= 0:
                vol = max_volume
            else:
                prog = min(1.0, max(0.0, elapsed / float(ramp_seconds)))
                vol = start_volume + (max_volume - start_volume) * prog

            vol = float(min(max(vol, 0.0), 1.0))
            with self._lock:
                self._status = AudioStatus(is_playing=True, volume=vol)

            # scale samples (software volume)
            scaled = np.clip(data.astype(np.float32) * vol, -32768, 32767).astype(np.int16)

            play_obj = sa.play_buffer(scaled.tobytes(), num_channels=nch, bytes_per_sample=2, sample_rate=fr)
            # Wait for the loop chunk to finish or stop early
            while play_obj.is_playing():
                if self._stop_event.is_set():
                    play_obj.stop()
                    break
                time.sleep(0.02)

            # tiny pause between loops
            if loop_pause_ms > 0:
                for _ in range(int(loop_pause_ms / 10)):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.01)

        with self._lock:
            self._status = AudioStatus(is_playing=False, volume=0.0)
