from __future__ import annotations

import time
from datetime import datetime, timedelta, date

from clock.storage import AlarmStore
from clock.alarms import AlarmManager, weekdays_to_mask


def main() -> None:
    store = AlarmStore("alarms.db")
    mgr = AlarmManager(store)

    # If DB has no alarms, create a demo alarm ~1 minute from now (one-shot)
    alarms = mgr.list_alarms()
    if not alarms:
        t = datetime.now() + timedelta(minutes=1)
        mgr.add_one_shot_alarm(
            label="Demo alarm (one-shot)",
            hhmm=t.strftime("%H:%M"),
            on_date=date.today(),
            enabled=True,
        )
        print("Created a demo one-shot alarm for ~1 minute from now.")

    print("\nCurrent alarms:")
    for a in mgr.list_alarms():
        print(f"- id={a.id} enabled={a.enabled} {a.label} {a.hour:02d}:{a.minute:02d} one_shot={a.one_shot_date} mask={a.weekdays_mask}")

    print("\nWatching for next alarm (Ctrl+C to stop)...")
    last_print = 0.0
    while True:
        now = datetime.now()
        nxt = mgr.compute_next(now)

        if nxt is None:
            if time.time() - last_print > 5:
                print("No upcoming alarms.")
                last_print = time.time()
            time.sleep(1)
            continue

        seconds = int((nxt.trigger_at - now).total_seconds())

        if time.time() - last_print > 1:
            print(f"Next: {nxt.alarm.label} at {nxt.trigger_at} (in {seconds}s)")
            last_print = time.time()

        if seconds <= 0:
            print("\n*** ALARM FIRED ***", nxt.alarm.label, "at", now)
            mgr.mark_fired_if_one_shot(nxt.alarm, now)
            # in the real app, you'd trigger audio + UI here
            time.sleep(2)

        time.sleep(0.2)


if __name__ == "__main__":
    main()
