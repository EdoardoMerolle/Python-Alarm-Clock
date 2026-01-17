# Calendar Integration Guide

The Python Alarm Clock supports syncing events from both local `.ics` files and calendar URLs. This allows you to automatically create alarms from calendar events.

## Quick Start: Add Your University Calendar

If you have a calendar URL (like from your uni):

1. Open the app and go to **Calendar** panel
2. Paste the URL into the "Paste calendar URL..." field
3. Tap **Add**
4. Tap **Sync All URLs**
5. Events appear in the Alarms panel

## How to Get Calendar URLs

### Outlook / Office 365 (including many universities)

**Web:**
1. Go to [outlook.office365.com](https://outlook.office365.com)
2. Right-click the calendar you want → **Sharing** → **Get sharing link**
3. Click the **ICS** icon to get the `.ics` link
4. Copy that link and paste it in the app

**Alternative:**
1. Settings → Calendar → **Publish**
2. Copy the **ICS URL**

### Google Calendar

1. Go to [calendar.google.com](https://calendar.google.com)
2. Right-click the calendar → **Settings**
3. Scroll to "Integrate calendar"
4. Copy the **Calendar ID** (looks like `abc123...@group.calendar.google.com`)
5. Use this URL:
   ```
   https://calendar.google.com/calendar/ical/{CALENDAR_ID}/public/basic.ics
   ```

### Apple Calendar (iCloud)

1. Right-click calendar → **Share Calendar**
2. Copy the public link
3. If it's a `.ics` link, use it directly
4. If it's a web link, change `/webcal://` to `https://`

### Other Calendar Apps

- Look for **Export**, **Share**, **ICS**, or **Subscribe** options
- Most apps provide a `.ics` download or public link
- Paste the URL into the app

## Methods

### Local .ics Files

Place `.ics` files directly in the `assets/calendar/` folder:

```
Python-Alarm-Clock/
  assets/
    calendar/
      myevents.ics           ← Drop files here
      university.ics
      work.ics
```

Then tap **"Sync .ics Files"** in the Calendar panel.

### Calendar URLs (Recommended)

1. Go to Calendar panel
2. Paste the URL
3. Tap **Add**
4. Saved URLs appear in the list
5. Tap **"Sync All URLs"** to fetch latest events

**Advantages:**
- URLs stay synchronized automatically
- No manual file management
- One-click sync for all calendars

## Example: University Calendar Setup

**Step 1:** Get your university calendar URL
- Check your uni email system (Outlook, Google, etc.)
- Right-click calendar → Get sharing link → ICS URL
- Example: `https://outlook.office365.com/owa/calendar/...`

**Step 2:** Add to the app
1. Open Calendar panel
2. Paste the URL
3. Tap **Add**

**Step 3:** Sync
1. Tap **Sync All URLs**
2. All class times + events become alarms
3. Alarms appear in your Alarms panel

## Features

✓ **Local .ics files** – Drop files in `assets/calendar/`  
✓ **URL-based calendars** – Paste links, auto-fetch events  
✓ **Timezone-aware** – Handles UTC and local times  
✓ **Date-only events** – Converts to 9:00 AM  
✓ **Past filtering** – Old events are skipped  
✓ **Multi-calendar** – Combine unlimited calendars  
✓ **Persistent URLs** – Saved in `assets/calendar_urls.json`  

## Troubleshooting

**URL not working?**
- Make sure it's a `.ics` or iCalendar URL (not a web calendar link)
- Check the URL starts with `http://` or `https://`
- Some calendars require authentication (not supported yet)

**No events created?**
- Events must be in the future (relative to device time)
- Check the URL is correct (try pasting in browser)
- Check app console for error messages

**Time zones wrong?**
- App uses device local time (no timezone conversion yet)
- Adjust event times in your calendar if needed

**"Network error" when syncing URLs?**
- Check internet connection
- Some URLs might be blocked or require authentication
- Try the URL in your browser first to verify it works

## Configuration Files

Settings are stored in:
- **`assets/calendar_urls.json`** – Saved calendar URLs
- **`assets/calendar/`** – Local .ics files

You can edit `calendar_urls.json` manually:
```json
{
  "University Calendar": "https://outlook.office365.com/owa/calendar/.../calendar.ics",
  "Work Calendar": "https://calendar.google.com/calendar/ical/.../public/basic.ics"
}
```

## Future Enhancements

- [ ] Direct Google Calendar API (no URL needed)
- [ ] Automatic periodic sync (every hour)
- [ ] Timezone conversion
- [ ] Recurring event support (RRULE)
- [ ] Calendar color coding
- [ ] Home Assistant calendar integration

