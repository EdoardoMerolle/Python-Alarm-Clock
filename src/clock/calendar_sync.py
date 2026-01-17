"""Calendar sync utilities for integrating external calendars with alarms."""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from typing import Optional
import json

try:
    from icalendar import Calendar
except ImportError:
    Calendar = None

try:
    import requests
except ImportError:
    requests = None


class IcsSync:
    """Sync alarms from .ics calendar files."""

    @staticmethod
    def parse_ics_file(ics_path: Path) -> list[dict]:
        """
        Parse .ics file and extract events.
        Returns list of dicts with keys: label, datetime (datetime object)
        """
        if Calendar is None:
            raise ImportError("icalendar package required for .ics support. Install with: pip install icalendar")

        events = []
        try:
            with open(ics_path, "rb") as f:
                cal = Calendar.from_ical(f.read())

            for component in cal.walk():
                if component.name == "VEVENT":
                    summary = str(component.get("summary", "Event")).strip()
                    
                    # Get start time (dtstart)
                    dtstart = component.get("dtstart")
                    if dtstart is None:
                        continue
                    
                    # Decode the datetime
                    dt_value = dtstart.dt
                    
                    # Handle both date-only and datetime values
                    if isinstance(dt_value, date) and not isinstance(dt_value, datetime):
                        # Date-only event; treat as 09:00 on that date
                        dt = datetime.combine(dt_value, datetime.min.time().replace(hour=9))
                    else:
                        # Already a datetime
                        dt = dt_value if isinstance(dt_value, datetime) else datetime.combine(dt_value, datetime.min.time())
                    
                    # Strip timezone info for comparison (convert to naive UTC)
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    
                    events.append({
                        "label": summary,
                        "datetime": dt,
                    })
        except Exception as e:
            print(f"Error parsing {ics_path}: {e}")
        
        return events

    @staticmethod
    def sync_from_directory(alarm_manager, calendar_dir: Path, dry_run: bool = False) -> dict:
        """
        Scan calendar_dir for .ics files and create one-shot alarms.
        
        Returns dict with keys:
        - 'created': list of alarm labels created
        - 'skipped': list of events skipped (e.g., in the past)
        - 'errors': list of error messages
        """
        created = []
        skipped = []
        errors = []

        if not calendar_dir.exists():
            errors.append(f"Calendar directory not found: {calendar_dir}")
            return {"created": created, "skipped": skipped, "errors": errors}

        now = datetime.now()
        ics_files = list(calendar_dir.glob("*.ics"))

        for ics_file in ics_files:
            try:
                events = IcsSync.parse_ics_file(ics_file)
                for event in events:
                    event_dt = event["datetime"]
                    label = event["label"]

                    # Skip past events
                    if event_dt < now:
                        skipped.append(f"{label} ({event_dt.strftime('%Y-%m-%d %H:%M')})")
                        continue

                    # Create alarm
                    if not dry_run:
                        hhmm = f"{event_dt.hour:02d}:{event_dt.minute:02d}"
                        alarm_manager.add_one_shot_alarm(
                            label,
                            hhmm,
                            event_dt.date(),
                            enabled=True,
                        )
                    created.append(f"{label} ({event_dt.strftime('%Y-%m-%d %H:%M')})")
            except Exception as e:
                errors.append(f"{ics_file.name}: {e}")

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }

    @staticmethod
    def fetch_ics_from_url(url: str) -> bytes:
        """Download .ics file from URL."""
        if requests is None:
            raise ImportError("requests package required for URL calendars. Install with: pip install requests")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"Failed to download calendar from {url}: {e}")

    @staticmethod
    def parse_ics_data(data: bytes) -> list[dict]:
        """Parse .ics data (bytes) and extract events."""
        if Calendar is None:
            raise ImportError("icalendar package required for .ics support. Install with: pip install icalendar")

        events = []
        try:
            cal = Calendar.from_ical(data)

            for component in cal.walk():
                if component.name == "VEVENT":
                    summary = str(component.get("summary", "Event")).strip()
                    
                    # Get start time (dtstart)
                    dtstart = component.get("dtstart")
                    if dtstart is None:
                        continue
                    
                    # Decode the datetime
                    dt_value = dtstart.dt
                    
                    # Handle both date-only and datetime values
                    if isinstance(dt_value, date) and not isinstance(dt_value, datetime):
                        # Date-only event; treat as 09:00 on that date
                        dt = datetime.combine(dt_value, datetime.min.time().replace(hour=9))
                    else:
                        # Already a datetime
                        dt = dt_value if isinstance(dt_value, datetime) else datetime.combine(dt_value, datetime.min.time())
                    
                    # Strip timezone info for comparison (convert to naive UTC)
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    
                    events.append({
                        "label": summary,
                        "datetime": dt,
                    })
        except Exception as e:
            print(f"Error parsing calendar data: {e}")
        
        return events

    @staticmethod
    def sync_from_url(alarm_manager, url: str, dry_run: bool = False) -> dict:
        """
        Fetch and sync calendar from URL.
        
        Returns dict with keys:
        - 'created': list of alarm labels created
        - 'skipped': list of events skipped
        - 'errors': list of error messages
        """
        created = []
        skipped = []
        errors = []

        try:
            ics_data = IcsSync.fetch_ics_from_url(url)
            events = IcsSync.parse_ics_data(ics_data)
            
            now = datetime.now()
            for event in events:
                event_dt = event["datetime"]
                label = event["label"]

                # Skip past events
                if event_dt < now:
                    skipped.append(f"{label} ({event_dt.strftime('%Y-%m-%d %H:%M')})")
                    continue

                # Create alarm
                if not dry_run:
                    hhmm = f"{event_dt.hour:02d}:{event_dt.minute:02d}"
                    alarm_manager.add_one_shot_alarm(
                        label,
                        hhmm,
                        event_dt.date(),
                        enabled=True,
                    )
                created.append(f"{label} ({event_dt.strftime('%Y-%m-%d %H:%M')})")
        except Exception as e:
            errors.append(f"URL: {e}")

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }


class CalendarConfig:
    """Manage calendar URLs config."""

    CONFIG_PATH = Path("assets/calendar_urls.json")

    @classmethod
    def load_urls(cls) -> dict[str, str]:
        """Load calendar URLs from config file."""
        if not cls.CONFIG_PATH.exists():
            return {}
        
        try:
            with open(cls.CONFIG_PATH) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading calendar config: {e}")
            return {}

    @classmethod
    def save_urls(cls, urls: dict[str, str]) -> None:
        """Save calendar URLs to config file."""
        try:
            cls.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(cls.CONFIG_PATH, "w") as f:
                json.dump(urls, f, indent=2)
        except Exception as e:
            print(f"Error saving calendar config: {e}")

    @classmethod
    def add_url(cls, name: str, url: str) -> None:
        """Add a calendar URL."""
        urls = cls.load_urls()
        urls[name] = url
        cls.save_urls(urls)

    @classmethod
    def remove_url(cls, name: str) -> None:
        """Remove a calendar URL."""
        urls = cls.load_urls()
        urls.pop(name, None)
        cls.save_urls(urls)
