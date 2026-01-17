#!/usr/bin/env python3
"""Quick test of calendar sync functionality."""

from pathlib import Path
from datetime import datetime
import sys

# Add src to path (run from project root)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from clock.storage import AlarmStore
from clock.alarms import AlarmManager
from clock.calendar import IcsSync

def test_calendar_sync():
    print("Testing .ics calendar sync...")
    print()
    
    # Setup
    db_path = Path("test_alarms.db")
    if db_path.exists():
        db_path.unlink()
    
    store = AlarmStore(db_path)
    mgr = AlarmManager(store)
    calendar_dir = Path("assets/calendar")
    
    # Test sync
    result = IcsSync.sync_from_directory(mgr, calendar_dir)
    
    print(f"Created: {len(result['created'])}")
    for item in result['created']:
        print(f"  ✓ {item}")
    
    if result['skipped']:
        print(f"\nSkipped: {len(result['skipped'])}")
        for item in result['skipped']:
            print(f"  ⊘ {item}")
    
    if result['errors']:
        print(f"\nErrors: {len(result['errors'])}")
        for item in result['errors']:
            print(f"  ✗ {item}")
    
    print()
    print("Alarms in database:")
    for alarm in mgr.list_alarms():
        print(f"  {alarm.label} @ {alarm.hour:02d}:{alarm.minute:02d} "
              f"(one-shot: {alarm.one_shot_date})")
    
    # Cleanup
    del store
    del mgr
    import gc
    gc.collect()
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception as e:
            print(f"\nWarning: Could not delete test DB: {e}")
    print("\nTest complete!")

if __name__ == "__main__":
    test_calendar_sync()
