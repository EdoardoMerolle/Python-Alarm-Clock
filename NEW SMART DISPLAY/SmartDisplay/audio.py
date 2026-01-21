# audio.py
import pygame
import os

class AudioManager:
    def __init__(self):
        # Initialize the mixer specifically for 44.1kHz (standard quality)
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            print("Audio initialized successfully.")
        except Exception as e:
            print(f"Audio init failed: {e}")

        self._sound = None
        self._load_sound()

    def _load_sound(self):
        # Path to your sound file
        sound_path = os.path.join("assets", "sounds", "alarm.mp3")
        
        if os.path.exists(sound_path):
            try:
                self._sound = pygame.mixer.Sound(sound_path)
            except Exception as e:
                print(f"Error loading sound file: {e}")
        else:
            print(f"WARNING: Sound file not found at {sound_path}")

    def play_alarm(self):
        """Plays the alarm sound in a loop."""
        if self._sound:
            # loops=-1 means loop forever until stopped
            self._sound.play(loops=-1)

    def stop_alarm(self):
        """Stops the alarm sound."""
        if self._sound:
            self._sound.stop()