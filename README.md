# Python Alarm Clock

A smart, feature-rich alarm clock application built with Python, Kivy, and pygame. Supports multiple weekly alarms, one-shot alarms, snoozing, smooth volume ramping, and photo slideshow backgrounds.

## Features

- **Weekly Alarms**: Set alarms for any combination of days (Mon–Sun)
- **One-Shot Alarms**: Schedule a single alarm for a specific date
- **Snooze**: Snooze active alarms for 9 minutes (customizable)
- **Volume Ramp**: Audio starts soft and gradually increases over 30 seconds for a gentler wake-up
- **Photo Slideshow**: Display background photos with configurable interval
- **Persistent Storage**: SQLite-backed alarm scheduling and state
- **Time Adjustment**: Intuitive +/– buttons for fine-tuning alarm times
- **Cross-Platform**: Runs on Linux, macOS, Windows, and Raspberry Pi

## Installation

### Prerequisites

- Python 3.9+
- pip

### Setup

1. **Clone the repository** (or extract the archive):

   ```bash
   git clone https://github.com/yourusername/Python-Alarm-Clock.git
   cd Python-Alarm-Clock
   ```

2. **Create a virtual environment** (optional but recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Alarm Clock

### Main GUI Application

```bash
python -m clock.app
```

This launches the Kivy UI with the home panel (showing photos), alarms, calendar (placeholder), and settings.

### CLI Scheduler Demo

For testing the scheduling logic without the UI:

```bash
python scripts/schedule_demo.py
```

## Configuration

### Photos Directory

By default, the application looks for photos in `assets/photos/`. You can override this:

**Option 1: Environment variable**

```bash
export ALARM_CLOCK_PHOTOS=/path/to/your/photos
python -m clock.app
```

**Option 2: Edit `src/clock/app.py`**
Change the `PHOTOS_DIR` line to point to your desired directory.

### Customizable Parameters

In `src/clock/app.py`:

- `SNOOZE_MINUTES`: Duration of snooze (default: 9)
- `RAMP_SECONDS`: Volume ramp duration (default: 30)
- `PHOTO_INTERVAL_SECONDS`: Time between photo transitions (default: 12)
- `ALARM_WAV`: Path to alarm sound file (default: `assets/sounds/alarm.wav`)

## Usage

### Creating an Alarm

1. Open the **Alarms** panel (swipe right)
2. Tap **Add Alarm**
3. Set the time using the +/– buttons
4. Choose **Weekly** (select days) or **One-Shot** (pick a date)
5. Optional: Change the alarm label (e.g., "Wake up", "Workout")
6. Tap **Save**

### Editing an Alarm

1. In the **Alarms** panel, tap **Edit** on an alarm
2. Adjust time, weekdays, or label as needed
3. Tap **Save**

### Dismissing an Alarm

When an alarm rings:

- Tap **Dismiss** to stop immediately
- Tap **Snooze** to repeat in 9 minutes

## Raspberry Pi Setup

The app runs well on a Raspberry Pi (tested on Pi 4+). Additional considerations:

### Audio Device

If the app doesn't detect audio on boot, specify the device explicitly:

```bash
export SDL_AUDIODRIVER=alsa
python -m clock.app
```

Or check available devices:

```bash
aplay -l
```

Then in `src/clock/audio.py`, update the mixer initialization if needed.

### Fullscreen Mode

Edit `src/clock/app.py` and add after `Window` imports:

```python
from kivy.core.window import Window
Window.fullscreen = True
# Or for borderless:
# Window.borderless = True
```

### Auto-Start on Boot

Create a systemd service file at `/etc/systemd/system/alarm-clock.service`:

```ini
[Unit]
Description=Python Alarm Clock
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Python-Alarm-Clock
ExecStart=/usr/bin/python3 -m clock.app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable alarm-clock
sudo systemctl start alarm-clock
```

## Architecture

### Core Modules

- **`clock/app.py`**: Kivy UI (HomePanel, AlarmsPanel, etc.)
- **`clock/alarms.py`**: Pure scheduling logic (AlarmManager)
- **`clock/storage.py`**: SQLite persistence layer
- **`clock/audio.py`**: Pygame mixer + volume ramping
- **`clock/platform/`**: Platform-specific extensions (desktop, Raspberry Pi)

### Data Model

Alarms are stored with:

- `hour`, `minute`: 24-hour time
- `weekdays_mask`: Bitmask for selected days (bit 0 = Monday, ..., bit 6 = Sunday)
- `enabled`: Whether the alarm is active
- `one_shot_date`: Date for one-shot alarms (NULL for weekly)

### Key Features

- **Separation of concerns**: AlarmManager is UI-agnostic; easy to add Home Assistant, REST API, etc.
- **Snooze state**: Single `alarm_state` table with `snooze_until` timestamp
- **Volume ramp**: Background thread in AudioEngine smoothly adjusts mixer volume

## Troubleshooting

### No photos appear

- Check that photos exist in `assets/photos/` (or your configured path)
- Ensure filenames are `.jpg`, `.png`, etc.
- Verify PHOTOS_DIR path is correct: `python -c "from pathlib import Path; import os; print(Path(os.getenv('ALARM_CLOCK_PHOTOS', 'assets/photos')))`

### Audio doesn't play

- On Linux: Try `SDL_AUDIODRIVER=alsa python -m clock.app`
- Check that `assets/sounds/alarm.wav` exists
- Verify system volume is not muted

### Weekday editing broken

- Make sure your app.py is up to date; an older version had a bug decoding `weekdays_mask`

### Minute adjustment doesn't carry hours

- Make sure your app.py is up to date; an older version had a bug in `_adjust_time()`

## Development & Testing

Run the CLI demo to test scheduling without UI:

```bash
python scripts/schedule_demo.py
```

Database is stored in `alarms.db` (auto-created). Clear it to reset:

```bash
rm alarms.db
```

## Contributing

Feel free to fork, modify, and submit issues or PRs. Areas for future work:

- Calendar integration
- Home Assistant/MQTT support
- Custom alarm sounds
- Sunrise alarm simulation
- Sleep timer

## License

MIT (or your chosen license)

## Credits

Built with:

- [Kivy](https://kivy.org/) – Modern Python UI framework
- [Pygame](https://www.pygame.org/) – Audio playback
- [SQLite](https://www.sqlite.org/) – Persistent storage
