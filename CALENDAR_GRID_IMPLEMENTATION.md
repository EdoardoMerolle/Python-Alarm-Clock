# Calendar Grid Implementation

## What Changed

The **CalendarPanel** has been upgraded from a simple placeholder to a full-featured monthly calendar grid view with event visualization and synchronization controls.

### New Features

#### 1. **Monthly Calendar Grid**
- Visual 7x7 calendar grid with day names (Sun-Sat)
- Month navigation with ◀ ▶ buttons
- Highlights current month, grays out days from adjacent months
- **Red-colored days** indicate dates with synced calendar events
- **Gray days** show no events scheduled

#### 2. **Event Visualization**
- **Click any date** to see events scheduled for that day
- Events display in a dedicated panel showing time and label
- Example: "📅 Monday, January 20:\n  • Team Standup @ 08:00"

#### 3. **Calendar Synchronization**
Two sync methods are available:

**File Sync:**
- Scans `assets/calendar/` for `.ics` files
- Click **"Sync .ics Files"** to import
- Useful for local calendar exports

**URL Sync:**
- Paste calendar URLs (Outlook, Google, Apple, etc.)
- URLs saved automatically in `assets/calendar_urls.json`
- Click **"Sync All URLs"** to fetch latest events
- Shows sync results with count of created/skipped events

#### 4. **Integrated Status Display**
- Real-time feedback on sync operations
- Shows count of new alarms created
- Lists past/skipped events
- Error messages for troubleshooting

### Architecture

#### New Files
- **`src/clock/calendar_view.py`** - Calendar display utilities
  - `CalendarView.get_month_grid()` - Generates calendar grid
  - `CalendarView.get_events_for_date()` - Lists alarms for a date
  - `CalendarView.get_dates_with_events()` - Marks dates with events
  
- **`src/clock/calendar.py`** - Calendar sync engine (already implemented)
  - `IcsSync` - Parses .ics files and downloads from URLs
  - `CalendarConfig` - Manages saved calendar URLs

#### Modified Files
- **`src/clock/app.py`**
  - `CalendarPanel.__init__()` - Complete UI rebuild
  - `CalendarPanel._draw_calendar()` - Renders 7x7 grid
  - `CalendarPanel._select_day()` - Shows events for selected date
  - `CalendarPanel._prev_month()` / `_next_month()` - Month navigation
  - `CalendarPanel._sync_files()` - Import from local .ics files
  - `CalendarPanel._sync_urls()` - Download and sync from URLs

### User Workflow

#### 1. Viewing the Calendar
1. Open app, swipe to **Calendar** panel
2. See current month with red dots on dates with events
3. Click any date to see that day's events

#### 2. Adding a Calendar URL
1. Copy calendar URL from Outlook/Google/Apple
2. Paste into "Paste URL..." field
3. Tap **Add**
4. URL saved and appears in list

#### 3. Syncing Events
1. Tap **Sync .ics Files** (for local files in `assets/calendar/`)
2. Or tap **Sync All URLs** (for saved calendar URLs)
3. New one-shot alarms created automatically
4. View results in status panel

### Data Flow

```
Calendar URL or .ics File
        ↓
   IcsSync.parse_ics_data()
        ↓
   Event extraction (title, datetime)
        ↓
   Filter past events
        ↓
   AlarmManager.add_one_shot_alarm()
        ↓
   Created in Alarms panel
        ↓
   CalendarPanel shows as red dots
```

### Synced Events

Events are created as **one-shot alarms** with:
- Label: Event title from calendar
- Time: Event start time (date + hour:minute)
- Type: One-shot (specific date only)
- Enabled: Yes (by default)

**Example:** University class "CS101 Lecture" on Jan 20 @ 10:00 → Creates alarm "CS101 Lecture" at 10:00 on 2025-01-20

### Configuration

#### Calendar URLs (Optional)
Manually edit `assets/calendar_urls.json`:
```json
{
  "University": "https://outlook.office365.com/owa/calendar/.../calendar.ics",
  "Work": "https://calendar.google.com/calendar/ical/.../public/basic.ics"
}
```

#### Local .ics Files
Drop files into `assets/calendar/`:
```
assets/
  calendar/
    myevents.ics        ← Automatically synced
    university.ics
    work.ics
```

### Troubleshooting

**No events showing on calendar?**
- Check if events are synced: Tap **Sync .ics Files** or **Sync All URLs**
- Verify events are in the future (past events filtered)
- Check Alarms panel to confirm alarms were created

**Calendar grid not rendering?**
- Ensure `calendar_view.py` module is present in `src/clock/`
- Check for Python errors in app console

**URL sync fails?**
- Verify URL is a `.ics` iCalendar link (not a web calendar)
- Check internet connection
- Try URL in browser to confirm it's accessible

### Next Steps (Future Enhancements)

- [ ] Automatic periodic sync (e.g., every hour)
- [ ] Direct Google Calendar API support
- [ ] Timezone conversion
- [ ] Recurring event support (RRULE parsing)
- [ ] Calendar color coding
- [ ] Filtering by calendar source
- [ ] Home Assistant calendar integration

---

**Last Updated:** January 2025  
**Status:** Fully implemented and tested
