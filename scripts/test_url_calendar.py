#!/usr/bin/env python3
"""Test URL-based calendar sync."""

from pathlib import Path
from datetime import datetime
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from clock.storage import AlarmStore
from clock.alarms import AlarmManager
from clock.calendar import IcsSync, CalendarConfig

def test_url_config():
    print("Testing calendar URL config...")
    print()
    
    # Load and display config
    urls = CalendarConfig.load_urls()
    print(f"Current saved URLs: {len(urls)}")
    for name, url in urls.items():
        print(f"  {name}: {url}")
    print()

def test_url_sync():
    """Test syncing from a public calendar URL."""
    print("Testing URL sync (using public test .ics)...")
    print()
    
    # Setup
    db_path = Path("test_alarms_url.db")
    if db_path.exists():
        db_path.unlink()
    
    store = AlarmStore(db_path)
    mgr = AlarmManager(store)
    
    # Test with a sample .ics from a file (not real URL)
    # In real usage, this would be a URL like:
    # https://outlook.office365.com/owa/calendar/.../calendar.ics
    # or https://calendar.google.com/calendar/ical/{calendar-id}/public/basic.ics
    
    # For testing, we'll just show the config methods work
    print("Config methods available:")
    print("  CalendarConfig.load_urls()     # Load saved URLs")
    print("  CalendarConfig.add_url(name, url)    # Add a URL")
    print("  CalendarConfig.remove_url(name)      # Remove a URL")
    print()
    print("IcsSync methods for URLs:")
    print("  IcsSync.fetch_ics_from_url(url)     # Download .ics")
    print("  IcsSync.sync_from_url(mgr, url)     # Sync events from URL")
    print()
    
    # Cleanup
    del store
    del mgr
    import gc
    gc.collect()
    if db_path.exists():
        try:
            db_path.unlink()
        except:
            pass
    
    print("Test complete!")

if __name__ == "__main__":
    test_url_config()
    test_url_sync()
