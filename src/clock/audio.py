from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygame


@dataclass
class AudioStatus:
    is_playing: bool
    volume: float


class AudioEngine:
    def __init__(self) -> None:
        self._init_done = False
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._status = AudioStatus(is_playing=False, volume=0.0)

    def _ensure_init(self) -> None:
        if self._init_done:
            return
        pygame.mixer.init()
        self._init_done = True

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._init_done:
            pygame.mixer.music.stop()
        self._status = AudioStatus(is_playing=False, volume=0.0)

    def play_loop_with_ramp(
        self,
        wav_path: Path,
        ramp_seconds: int = 30,
        start_volume: float = 0.15,
        max_volume: float = 1.0,
    ) -> None:
        self.stop()
        self._stop.clear()
        self._ensure_init()

        wav_path.parent.mkdir(parents=True, exist_ok=True)
        if not wav_path.exists():
            raise FileNotFoundError(f"Alarm sound not found: {wav_path}")

        pygame.mixer.music.load(str(wav_path))
        pygame.mixer.music.set_volume(start_volume)
        pygame.mixer.music.play(loops=-1)

        self._status = AudioStatus(is_playing=True, volume=start_volume)

        def ramp() -> None:
            start = time.time()
            while not self._stop.is_set():
                elapsed = time.time() - start
                if ramp_seconds <= 0:
                    vol = max_volume
                else:
                    prog = min(1.0, max(0.0, elapsed / float(ramp_seconds)))
                    vol = start_volume + (max_volume - start_volume) * prog
                vol = float(min(max(vol, 0.0), 1.0))
                pygame.mixer.music.set_volume(vol)
                self._status = AudioStatus(is_playing=True, volume=vol)
                time.sleep(0.2)

        self._thread = threading.Thread(target=ramp, daemon=True)
        self._thread.start()
