import sys
import os
import random
import threading
import requests
import json
import asyncio
import subprocess 
import hashlib
import time
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, date
from pathlib import Path

from icalendar import Calendar
from kasa import Discover, DeviceType

from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot, QUrl, Qt, QSettings
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import database

class SmartClockBackend(QObject):
    timeChanged = Signal()
    dateChanged = Signal()
    alarmTriggered = Signal(str)
    alarmsChanged = Signal()
    nightModeChanged = Signal()
    nightModeSettingChanged = Signal()
    calendarChanged = Signal()
    weatherChanged = Signal()
    lightStateChanged = Signal()
    snoozeChanged = Signal()
    imagesChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_time = ""
        self._current_date = ""
        self._is_night_mode = False
        self._settings = QSettings("SmartDisplay", "SmartDisplay")
        self._night_mode_setting = self._load_night_mode_setting()
        self._calendar_events = [] 
        self._is_fetching_calendar = False 
        
        # --- 1. LOAD SECRETS ---
        self.secrets = self._load_secrets()

        # --- 2. CONFIGURATION ---
        self.LATITUDE = self.secrets.get("latitude", 53.2587)
        self.LONGITUDE = self.secrets.get("longitude", -2.1270)
        self.TAPO_EMAIL = self.secrets.get("tapo_email", "")
        self.TAPO_PASSWORD = self.secrets.get("tapo_password", "")
        
        self._weather_temp = "--"
        self._weather_icon = "" 
        self._weather_desc = "Loading..."
        self._light_is_on = False
        self._active_alarm_id = None
        self._snoozed_alarm_id = None
        self._snooze_until = None
        self._image_refresh_lock = threading.Lock()
        self._image_refresh_inflight = False
        self._last_image_refresh_at = 0.0
        self._image_refresh_interval_seconds = 300
        
        # --- ASYNC SETUP ---
        self._bulb_device = None
        self._bulb_mac = self._settings.value("tapoBulbMac", "", type=str)
        self._tapo_lock = asyncio.Lock()
        self._tapo_status_future = None
        self._tapo_toggle_future = None
        self._next_tapo_discovery = 0.0
        self.tapo_loop = asyncio.new_event_loop()
        self.tapo_thread = threading.Thread(target=self._run_tapo_loop, daemon=True)
        self.tapo_thread.start()
        
        database.init_db()

        # Paths
        base_path = Path(__file__).resolve().parent
        self.cal_path = base_path / "assets" / "calendars"
        self.cal_path.mkdir(parents=True, exist_ok=True)
        self.cal_links_file = base_path / "assets" / "calendar_links.json"
        self.cal_links_legacy_file = base_path / "assets" / "calendar_links.txt"
        self.weather_asset_path = base_path / "assets" / "weather"
        self.weather_asset_path.mkdir(parents=True, exist_ok=True)
        self.photo_links_file = base_path / "assets" / "photo_links.json"
        self.photo_links_legacy_file = base_path / "assets" / "photo_links.txt"
        self.photo_rejections_file = base_path / "assets" / "photo_rejections.json"
        self.image_cache_path = base_path / "assets" / "image_cache"
        self.image_cache_path.mkdir(parents=True, exist_ok=True)
        self.image_source_path = base_path / "assets" / "images"
        self.image_source_path.mkdir(parents=True, exist_ok=True)
        self._image_urls = self._load_local_images()
        self._low_res_rejections = self._load_low_res_rejections()

        # Audio Setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        sound_path = base_path / "assets" / "sounds" / "alarm.mp3"
        self.player.setSource(QUrl.fromLocalFile(str(sound_path)))
        self.audio_output.setVolume(1.0)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        # --- SCREEN BLANKING TIMER ---
        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setInterval(30000) # 30 Seconds
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.timeout.connect(self._turn_off_screen)
        
        # --- 3. INITIAL LOADS ---
        self._init_x11_defaults() 
        
        if "latitude" not in self.secrets:
            self._detect_location()
        else:
            self._fetch_weather()
            
        self._refresh_calendar()
        self._refresh_images_async(force=True)
        self._tick()

    def _load_secrets(self):
        paths = [
            Path(__file__).resolve().parent / "secrets.json",
            Path(__file__).resolve().parent / "assets/secrets.json"
        ]
        for p in paths:
            if p.exists():
                try:
                    with open(p, "r") as f: return json.load(f)
                except: pass
        return {}

    # --- SCREEN CONTROL LOGIC (X11 TIMEOUT FIX) ---
    def _init_x11_defaults(self):
        """Disable auto-blanking on startup."""
        self._set_screen_power(True)

    def _set_screen_power(self, on):
        """
        Manages screen power while preventing OS auto-timeout.
        Requires 'Screen Blanking' to be ENABLED in raspi-config for capabilities,
        but we set the timeout to 0 (infinity) here to control it manually.
        """
        env = os.environ.copy()
        env["DISPLAY"] = ":0"
        
        try:
            if on:
                print("DEBUG: Screen WAKE UP (Disabling Auto-Timeout)")
                # 1. Force screen ON
                subprocess.run(["xset", "dpms", "force", "on"], env=env, check=False)
                # 2. Reset Screensaver (Legacy)
                subprocess.run(["xset", "s", "noblank"], env=env, check=False)
                subprocess.run(["xset", "s", "0", "0"], env=env, check=False) # Timeout 0
                # 3. Enable DPMS but set timers to 0 (Infinity)
                #    This keeps DPMS active so we can force off later, but stops auto-off.
                subprocess.run(["xset", "+dpms"], env=env, check=False)
                subprocess.run(["xset", "dpms", "0", "0", "0"], env=env, check=False)
            else:
                print("DEBUG: Screen SLEEP (Forcing Off)")
                # 1. Ensure DPMS is on
                subprocess.run(["xset", "+dpms"], env=env, check=False)
                # 2. Force OFF
                subprocess.run(["xset", "dpms", "force", "off"], env=env, check=False)
        except Exception as e:
            print(f"Screen Power Error: {e}")

    def _turn_off_screen(self):
        if self._is_night_mode:
            self._set_screen_power(False)

    @Slot()
    def resetInactivityTimer(self):
        # 1. Ensure screen is ON (and reset timeout to infinity)
        self._set_screen_power(True)
        
        # 2. If night mode, restart the sleep timer
        if self._is_night_mode:
            self._inactivity_timer.start()
        else:
            self._inactivity_timer.stop()

    # --- TAPO LIGHT LOGIC ---
    def _run_tapo_loop(self):
        asyncio.set_event_loop(self.tapo_loop)
        self.tapo_loop.run_forever()

    @Property(bool, notify=lightStateChanged)
    def lightIsOn(self): return self._light_is_on

    @Slot()
    def toggleLight(self):
        if self._tapo_toggle_future is None or self._tapo_toggle_future.done():
            self._tapo_toggle_future = asyncio.run_coroutine_threadsafe(
                self._async_tapo_toggle(), self.tapo_loop
            )

    def _check_light_status(self):
        if self._tapo_status_future is None or self._tapo_status_future.done():
            self._tapo_status_future = asyncio.run_coroutine_threadsafe(
                self._async_tapo_status(), self.tapo_loop
            )

    async def _disconnect_tapo(self, device):
        try:
            await device.disconnect()
        except Exception:
            pass

    async def _get_bulb(self):
        # Called under _tapo_lock so discovery and bulb operations never overlap.
        if self._bulb_device:
            return self._bulb_device
        if not self.TAPO_EMAIL or not self.TAPO_PASSWORD:
            return None
        if time.monotonic() < self._next_tapo_discovery:
            return None
        self._next_tapo_discovery = time.monotonic() + 30
        devices = {}
        try:
            devices = await Discover.discover(
                username=self.TAPO_EMAIL,
                password=self.TAPO_PASSWORD,
                discovery_timeout=5,
                timeout=5,
            )
            bulbs = []
            for device in devices.values():
                try:
                    await device.update()
                    if device.device_type == DeviceType.Bulb:
                        bulbs.append(device)
                except Exception:
                    continue
            if self._bulb_mac:
                matches = [bulb for bulb in bulbs if bulb.mac == self._bulb_mac]
            else:
                matches = bulbs
            if len(matches) != 1:
                message = "Multiple bulbs found; select a bulb before connecting." if len(matches) > 1 else "Bulb not found or authentication failed; retrying in 30 seconds."
                print(f"[Tapo] {message}", flush=True)
                return None
            self._bulb_device = matches[0]
            self._bulb_mac = self._bulb_device.mac
            # Use a worker-local QSettings instance, not the GUI thread's instance.
            settings = QSettings("SmartDisplay", "SmartDisplay")
            settings.setValue("tapoBulbMac", self._bulb_mac)
            settings.sync()
            print("[Tapo] Discovered and connected to bulb.", flush=True)
            return self._bulb_device
        except Exception as error:
            print(f"[Tapo] Discovery failed ({type(error).__name__}); retrying in 30 seconds.", flush=True)
            return None
        finally:
            for device in devices.values():
                if device is not self._bulb_device:
                    await self._disconnect_tapo(device)

    async def _async_tapo_toggle(self):
        async with self._tapo_lock:
            bulb = await self._get_bulb()
            if not bulb:
                return
            try:
                await bulb.update()
                if bulb.is_on:
                    await bulb.turn_off()
                else:
                    await bulb.turn_on()
                await bulb.update()
                self._light_is_on = bulb.is_on
                self.lightStateChanged.emit()
            except Exception:
                self._bulb_device = None
                await self._disconnect_tapo(bulb)

    async def _async_tapo_status(self):
        async with self._tapo_lock:
            bulb = await self._get_bulb()
            if not bulb:
                return
            try:
                await bulb.update()
                if self._light_is_on != bulb.is_on:
                    self._light_is_on = bulb.is_on
                    self.lightStateChanged.emit()
            except Exception:
                self._bulb_device = None
                await self._disconnect_tapo(bulb)

    # --- LOCATION & WEATHER ---
    def _detect_location(self):
        threading.Thread(target=self._worker_location, daemon=True).start()

    def _worker_location(self):
        try:
            response = requests.get("http://ip-api.com/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.LATITUDE = data.get("lat")
                    self.LONGITUDE = data.get("lon")
                    self._fetch_weather()
        except: pass

    def _fetch_weather(self):
        threading.Thread(target=self._worker_weather, daemon=True).start()

    def _worker_weather(self):
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.LATITUDE}&longitude={self.LONGITUDE}&current_weather=true"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json().get("current_weather", {})
                self._weather_temp = f"{data.get('temperature')}°C"
                self._weather_icon = self._get_icon_for_code(data.get("weathercode"))
                self._weather_desc = self._get_desc_for_code(data.get("weathercode"))
                self.weatherChanged.emit()
        except: pass

    def _get_icon_for_code(self, code):
        filename = "cloudy.png"
        if code == 0: filename = "moon.png" if self._is_night_mode else "sun.png"
        elif code in [1, 2, 3]: filename = "cloudy.png"
        elif code in [45, 48]: filename = "fog.png"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: filename = "rain.png"
        elif code in [71, 73, 75, 77, 85, 86]: filename = "snow.png"
        elif code in [95, 96, 99]: filename = "storm.png"
        path = self.weather_asset_path / filename
        return QUrl.fromLocalFile(str(path)).toString() if path.exists() else ""

    def _get_desc_for_code(self, code):
        if code == 0: return "Clear Sky"
        if code in [1, 2, 3]: return "Cloudy"
        if code in [45, 48]: return "Foggy"
        if code in [51, 53, 55, 61, 63, 65]: return "Rain"
        if code in [71, 73, 75, 77]: return "Snow"
        if code >= 95: return "Storm"
        return "Unknown"

    @Property(str, notify=weatherChanged)
    def weatherTemp(self): return self._weather_temp
    @Property(str, notify=weatherChanged)
    def weatherIcon(self): return self._weather_icon
    @Property(str, notify=weatherChanged)
    def weatherDesc(self): return self._weather_desc

    # --- CALENDAR ---
    def _refresh_calendar(self):
        if self._is_fetching_calendar: return
        self._is_fetching_calendar = True
        threading.Thread(target=self._worker_fetch_calendars, daemon=True).start()

    def _worker_fetch_calendars(self):
        try:
            events = []
            now = datetime.now().astimezone()
            if self.cal_path.exists():
                for file in os.listdir(self.cal_path):
                    if file.lower().endswith(".ics"):
                        try:
                            with open(self.cal_path / file, 'rb') as f: self._parse_ical_data(f.read(), events, now)
                        except: pass
            urls = self._load_url_links(self.cal_links_file, self.cal_links_legacy_file)
            for url in urls:
                try:
                    r = requests.get(url, timeout=5)
                    if r.status_code == 200: self._parse_ical_data(r.content, events, now)
                except: pass
            events.sort(key=lambda x: x['sort_date'])
            self._calendar_events = events 
            self.calendarChanged.emit()
        finally: self._is_fetching_calendar = False

    def _parse_ical_data(self, content, events_list, now):
        try:
            gcal = Calendar.from_ical(content)
            for component in gcal.walk():
                if component.name == "VEVENT":
                    summary = str(component.get('summary', 'No Title'))
                    location = str(component.get('location', '')) if component.get('location') else ""
                    description = str(component.get('description', '')) if component.get('description') else ""
                    if component.get('dtstart'):
                        dtstart = component.get('dtstart').dt
                        if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                            dtstart = datetime.combine(dtstart, datetime.min.time()).astimezone()
                        if dtstart.tzinfo is None: dtstart = dtstart.astimezone()
                        if dtstart >= now - timedelta(days=60):
                            if dtstart.date() == now.date(): date_str = f"Today, {dtstart.strftime('%H:%M')}"
                            elif dtstart.date() == (now + timedelta(days=1)).date(): date_str = f"Tomorrow, {dtstart.strftime('%H:%M')}"
                            else: date_str = dtstart.strftime("%a %d %b, %H:%M")
                            events_list.append({"title": summary, "date": date_str, "date_iso": dtstart.isoformat(), "sort_date": dtstart, "location": location, "description": description})
        except: pass

    @Property(list, notify=calendarChanged)
    def calendarEvents(self): return self._calendar_events

    @Property(list, notify=imagesChanged)
    def imageList(self):
        return self._image_urls

    def _load_local_images(self):
        image_urls = []
        if self.image_source_path.exists():
            for file in os.listdir(self.image_source_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    full_path = self.image_source_path / file
                    image_urls.append(QUrl.fromLocalFile(str(full_path)).toString())
        if self.image_cache_path.exists():
            for file in os.listdir(self.image_cache_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    full_path = self.image_cache_path / file
                    image_urls.append(QUrl.fromLocalFile(str(full_path)).toString())
        random.shuffle(image_urls)
        return image_urls

    def _refresh_images_async(self, force=False):
        now = time.time()
        if not force and (now - self._last_image_refresh_at) < self._image_refresh_interval_seconds:
            return

        with self._image_refresh_lock:
            if self._image_refresh_inflight:
                return
            self._image_refresh_inflight = True
            self._last_image_refresh_at = now

        print("[Photos] Starting background image refresh...", flush=True)
        threading.Thread(target=self._worker_refresh_images, daemon=True).start()

    def _worker_refresh_images(self):
        try:
            removed_before = self._dedupe_cache_by_content()
            if removed_before:
                print(f"[Photos] Removed {removed_before} duplicate cached image(s) before refresh.", flush=True)

            urls = self._load_photo_links()
            if not urls:
                print("[Photos] No remote photo links configured. Using local images only.", flush=True)
                self._image_urls = self._load_local_images()
                print(f"[Photos] Slideshow images available: {len(self._image_urls)}", flush=True)
                self.imagesChanged.emit()
                return
            print(f"[Photos] Found {len(urls)} configured photo link(s).", flush=True)
            downloaded = self._download_remote_images(urls)
            removed_after = self._dedupe_cache_by_content()
            if removed_after:
                print(f"[Photos] Removed {removed_after} duplicate cached image(s) after refresh.", flush=True)
            self._image_urls = self._load_local_images()
            if downloaded:
                print(f"[Photos] Refresh complete. Downloaded {downloaded} new image(s). Total slideshow images: {len(self._image_urls)}", flush=True)
            else:
                print(f"[Photos] Refresh complete. No new images downloaded. Total slideshow images: {len(self._image_urls)}", flush=True)
            self.imagesChanged.emit()
        finally:
            with self._image_refresh_lock:
                self._image_refresh_inflight = False

    def _load_photo_links(self):
        return self._load_url_links(self.photo_links_file, self.photo_links_legacy_file)

    def _load_url_links(self, json_path, legacy_txt_path=None):
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    links = data.get("links", [])
                elif isinstance(data, list):
                    links = data
                else:
                    links = []
                return [u.strip() for u in links if isinstance(u, str) and u.strip()]
            except Exception as e:
                print(f"[Links] Failed to read JSON links from {json_path.name}: {e}", flush=True)

        if legacy_txt_path and legacy_txt_path.exists():
            try:
                urls = []
                with open(legacy_txt_path, "r", encoding="utf-8") as f:
                    for raw in f:
                        line = raw.strip()
                        if line and not line.startswith("#"):
                            urls.append(line)
                print(f"[Links] Using legacy link file {legacy_txt_path.name}. Consider migrating to {json_path.name}.", flush=True)
                return urls
            except Exception as e:
                print(f"[Links] Failed to read legacy links from {legacy_txt_path.name}: {e}", flush=True)

        return []

    def _extract_direct_image_urls(self, source_url):
        parsed = urlparse(source_url)
        if parsed.path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
            return [source_url]

        try:
            response = requests.get(source_url, timeout=12)
            if response.status_code != 200:
                return []
            content = response.text
            candidates = set()
            for match in re.findall(r'https?://[^"\\\']+', content):
                if re.search(r'\.(jpg|jpeg|png|bmp|webp)(\?|$)', match, flags=re.IGNORECASE):
                    candidates.add(match.replace("\\/", "/"))
            return list(candidates)
        except:
            return []

    def _extract_icloud_shared_album_token(self, source_url):
        parsed = urlparse(source_url.strip())
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        fragment = (parsed.fragment or "").strip()

        if "icloud.com" not in host or "sharedalbum" not in path or not fragment:
            return None

        token = fragment.split(";")[0].strip()
        if not re.match(r"^[A-Za-z0-9]{6,}$", token):
            return None
        return token

    def _decode_icloud_server_partition(self, token):
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        if len(token) < 2:
            return None
        try:
            if token[0] == "A":
                return chars.index(token[1])
            if len(token) < 3:
                return None
            return (chars.index(token[1]) * 62) + chars.index(token[2])
        except ValueError:
            return None

    def _collect_photo_guids(self, value, out):
        if isinstance(value, dict):
            guid = value.get("photoGuid")
            if isinstance(guid, str) and guid:
                out.add(guid)
            for child in value.values():
                self._collect_photo_guids(child, out)
            return
        if isinstance(value, list):
            for child in value:
                self._collect_photo_guids(child, out)

    def _collect_image_urls(self, value, out):
        def add_candidate(raw):
            if not isinstance(raw, str):
                return
            url = raw.strip().replace("\\/", "/")
            if not url:
                return
            if url.startswith("//"):
                url = f"https:{url}"
            elif not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
                # iCloud sometimes returns host/path without scheme.
                if url.startswith(("cvws.icloud-content.com/", "p")) or ".icloud-content.com/" in url or ".icloud.com/" in url:
                    url = f"https://{url.lstrip('/')}"
                else:
                    return
            out.add(url)

        if isinstance(value, dict):
            url_location = value.get("url_location")
            url_path = value.get("url_path")
            if isinstance(url_location, str) and isinstance(url_path, str):
                add_candidate(f"{url_location.rstrip('/')}/{url_path.lstrip('/')}")

            for key in ("url", "downloadUrl", "photoUrl", "webAssetUrl"):
                item = value.get(key)
                add_candidate(item)

            for child in value.values():
                self._collect_image_urls(child, out)
            return

        if isinstance(value, list):
            for child in value:
                self._collect_image_urls(child, out)
            return

        if isinstance(value, str):
            add_candidate(value)

    def _icloud_sharedstreams_post(self, host, token, path, payload):
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.icloud.com",
            "Referer": "https://www.icloud.com/"
        }
        url = f"https://{host}/{token}/sharedstreams/{path}"
        print(f"[Photos] iCloud request: POST {path} on {host}", flush=True)
        started = time.time()
        try:
            # iCloud sharedstreams can be very slow to return first payloads.
            response = requests.post(url, headers=headers, json=payload, timeout=(10, 70))
        except Exception as e:
            elapsed = time.time() - started
            print(f"[Photos] iCloud request error on {path} after {elapsed:.1f}s: {e}", flush=True)
            return None, host

        redirect_host = response.headers.get("X-Apple-MMe-Host")
        elapsed = time.time() - started
        print(f"[Photos] iCloud response {path}: status={response.status_code}, redirectHost={redirect_host or 'none'}, elapsed={elapsed:.1f}s", flush=True)
        data = None
        try:
            data = response.json()
        except Exception:
            data = None
        if isinstance(data, dict) and isinstance(data.get("X-Apple-MMe-Host"), str):
            redirect_host = data["X-Apple-MMe-Host"]

        if response.status_code == 330 and redirect_host:
            return None, redirect_host
        if response.status_code != 200:
            return None, host
        return data, host

    def _extract_icloud_shared_album_urls(self, source_url):
        token = self._extract_icloud_shared_album_token(source_url)
        if not token:
            return []
        print(f"[Photos] iCloud shared album detected. Token: {token[:4]}***", flush=True)

        partition = self._decode_icloud_server_partition(token)
        if partition is None:
            print("[Photos] Could not decode iCloud partition from token.", flush=True)
            return []

        host = f"p{partition:02d}-sharedstreams.icloud.com"
        print(f"[Photos] iCloud initial sharedstreams host: {host}", flush=True)

        webstream_data = None
        for attempt in range(1, 3):
            print(f"[Photos] iCloud webstream attempt {attempt}/2", flush=True)
            webstream_data, next_host = self._icloud_sharedstreams_post(host, token, "webstream", {"streamCtag": None})
            host = next_host
            if webstream_data:
                break
        if not webstream_data:
            print("[Photos] iCloud webstream request failed.", flush=True)
            return []

        photo_guids = set()
        self._collect_photo_guids(webstream_data, photo_guids)

        urls = set()
        self._collect_image_urls(webstream_data, urls)

        if photo_guids:
            payload = {"photoGuids": list(photo_guids)}
            for attempt in range(1, 3):
                print(f"[Photos] iCloud webasseturls attempt {attempt}/2", flush=True)
                webasset_data, next_host = self._icloud_sharedstreams_post(host, token, "webasseturls", payload)
                host = next_host
                if webasset_data:
                    self._collect_image_urls(webasset_data, urls)
                    break

        print(f"[Photos] iCloud album resolved. photoGuids={len(photo_guids)}, candidateUrls={len(urls)}", flush=True)
        return list(urls)

    def _resolve_source_image_urls(self, source_url):
        icloud_token = self._extract_icloud_shared_album_token(source_url)
        if icloud_token:
            return self._extract_icloud_shared_album_urls(source_url)
        return self._extract_direct_image_urls(source_url)

    def _cache_key_for_image_url(self, image_url):
        parsed = urlparse(image_url)
        host = (parsed.netloc or "").lower()
        # iCloud rotates signed query params frequently.
        # Prefer stable asset id from query param "r" when available.
        if "icloud-content.com" in host:
            try:
                asset_id = parse_qs(parsed.query).get("r", [None])[0]
            except:
                asset_id = None
            if asset_id:
                return f"icloud-asset:{asset_id}"
            if parsed.path:
                return f"{host}{parsed.path}"
        return image_url

    def _rejection_key_for_image_url(self, image_url):
        parsed = urlparse(image_url)
        host = (parsed.netloc or "").lower()
        if "icloud-content.com" in host and parsed.path:
            return f"{host}{parsed.path}"
        return self._cache_key_for_image_url(image_url)

    def _load_low_res_rejections(self):
        if not self.photo_rejections_file.exists():
            return set()
        try:
            with open(self.photo_rejections_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("low_res_rejections", []) if isinstance(data, dict) else []
            return {x.strip() for x in items if isinstance(x, str) and x.strip()}
        except Exception as e:
            print(f"[Photos] Failed to load photo rejections: {e}", flush=True)
            return set()

    def _save_low_res_rejections(self):
        try:
            payload = {"low_res_rejections": sorted(self._low_res_rejections)}
            with open(self.photo_rejections_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"[Photos] Failed to save photo rejections: {e}", flush=True)

    def _download_remote_images(self, urls):
        downloaded = 0
        min_side_px = 900
        rejections_changed = False
        cache_content_hashes = set()
        for file in self.image_cache_path.iterdir():
            if not file.is_file():
                continue
            try:
                digest = hashlib.sha256(file.read_bytes()).hexdigest()
                cache_content_hashes.add(digest)
            except Exception:
                pass

        for source_url in urls:
            source_downloaded = 0
            resolved_urls = self._resolve_source_image_urls(source_url)
            print(f"[Photos] Source: {source_url} -> {len(resolved_urls)} candidate URL(s)", flush=True)
            deduped = {}
            for image_url in resolved_urls:
                deduped[self._cache_key_for_image_url(image_url)] = image_url
            print(f"[Photos] Source deduped to {len(deduped)} cache key(s)", flush=True)

            for cache_key, image_url in deduped.items():
                try:
                    rejection_key = self._rejection_key_for_image_url(image_url)
                    if rejection_key in self._low_res_rejections:
                        continue
                    response = requests.get(image_url, timeout=15)
                    if response.status_code != 200:
                        print(f"[Photos] Skip URL (status {response.status_code}): {image_url[:120]}", flush=True)
                        continue
                    content_type = (response.headers.get("content-type") or "").lower()
                    if content_type and not content_type.startswith("image/"):
                        print(f"[Photos] Skip URL (non-image content-type {content_type}): {image_url[:120]}", flush=True)
                        continue
                    image = QImage.fromData(response.content)
                    if image.isNull():
                        print(f"[Photos] Skip URL (invalid image data): {image_url[:120]}", flush=True)
                        continue
                    if min(image.width(), image.height()) < min_side_px:
                        print(f"[Photos] Skip URL (low resolution {image.width()}x{image.height()}): {image_url[:120]}", flush=True)
                        self._low_res_rejections.add(rejection_key)
                        rejections_changed = True
                        continue
                    content_digest = hashlib.sha256(response.content).hexdigest()
                    if content_digest in cache_content_hashes:
                        continue
                    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
                    ext = ".jpg"
                    parsed = urlparse(image_url)
                    suffix = Path(parsed.path).suffix.lower()
                    if suffix in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                        ext = suffix
                    elif "png" in content_type:
                        ext = ".png"
                    elif "webp" in content_type:
                        ext = ".webp"
                    target = self.image_cache_path / f"{digest}{ext}"
                    if target.exists():
                        continue
                    with open(target, "wb") as f:
                        f.write(response.content)
                    downloaded += 1
                    source_downloaded += 1
                    cache_content_hashes.add(content_digest)
                except Exception as e:
                    print(f"[Photos] Download error: {e}", flush=True)
            print(f"[Photos] Source done: downloaded {source_downloaded} new image(s)", flush=True)
        if rejections_changed:
            self._save_low_res_rejections()
            print(f"[Photos] Saved low-res rejection keys: {len(self._low_res_rejections)}", flush=True)
        return downloaded

    def _dedupe_cache_by_content(self):
        if not self.image_cache_path.exists():
            return 0
        seen = {}
        removed = 0
        for file in sorted(self.image_cache_path.iterdir(), key=lambda p: p.name):
            if not file.is_file():
                continue
            try:
                digest = hashlib.sha256(file.read_bytes()).hexdigest()
            except Exception:
                continue
            if digest in seen:
                try:
                    file.unlink()
                    removed += 1
                except Exception:
                    pass
            else:
                seen[digest] = file
        return removed

    def _tick(self):
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = f"{now.strftime('%A, %B')} {now.day}"
        
        if time_str != self._current_time:
            self._current_time = time_str
            self.timeChanged.emit()
            # Run minute-based tasks whenever HH:MM changes.
            self._check_alarms(now)
            self._refresh_calendar()
            self._refresh_images_async()
            if now.minute % 15 == 0:
                self._fetch_weather()
        
        if date_str != self._current_date:
            self._current_date = date_str
            self.dateChanged.emit()

        self._update_night_mode(now)

        if self.TAPO_EMAIL and self.TAPO_PASSWORD and now.second % 2 == 0: self._check_light_status()

    def _update_night_mode(self, now):
        # Scheduled night mode: 22:00 inclusive to 06:00 exclusive.
        is_night = self._night_mode_setting == "on" or (
            self._night_mode_setting == "auto" and (now.hour >= 22 or now.hour < 6)
        )
        if is_night == self._is_night_mode:
            return
        self._is_night_mode = is_night
        self.nightModeChanged.emit()
        self._fetch_weather()
        self.resetInactivityTimer()

    def _load_night_mode_setting(self):
        # Preserve the previous switch preference when upgrading.
        fallback = "auto" if self._settings.value("nightModeEnabled", True, type=bool) else "off"
        mode = self._settings.value("nightModeSetting", fallback, type=str)
        return mode if mode in ("auto", "on", "off") else fallback

    @Property(str, notify=nightModeSettingChanged)
    def nightModeSetting(self):
        return self._night_mode_setting

    @Slot(str)
    def setNightModeSetting(self, mode):
        if mode not in ("auto", "on", "off") or mode == self._night_mode_setting:
            return
        self._night_mode_setting = mode
        self._settings.setValue("nightModeSetting", mode)
        self._settings.sync()
        self.nightModeSettingChanged.emit()
        self._update_night_mode(datetime.now())

    def _check_alarms(self, now_dt):
        current_time_str = now_dt.strftime("%H:%M")
        current_weekday = str(now_dt.weekday()) 

        if self._snooze_until and now_dt.replace(second=0, microsecond=0) == self._snooze_until:
            self._active_alarm_id = self._snoozed_alarm_id
            self._snoozed_alarm_id = None
            self._snooze_until = None
            self.snoozeChanged.emit()
            if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.player.play()
                self._set_screen_power(True)
            self.alarmTriggered.emit("Wake Up!")

        for alarm in database.get_active_alarms():
            if alarm['time'] == current_time_str:
                if alarm['days'] == "Daily" or current_weekday in alarm['days'].split(","):
                    self._active_alarm_id = alarm['id']
                    if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState: 
                        self.player.play()
                        self._set_screen_power(True) 
                    self.alarmTriggered.emit("Wake Up!")

    @Property(str, notify=timeChanged)
    def currentTime(self): return self._current_time
    @Property(str, notify=dateChanged)
    def currentDate(self): return self._current_date
    @Property(bool, notify=nightModeChanged)
    def isNightMode(self): return self._is_night_mode
    @Property(str, notify=snoozeChanged)
    def snoozeStatus(self):
        if self._snooze_until is None:
            return ""
        return f"Snoozed until {self._snooze_until.strftime('%H:%M')}"
    @Property(list, notify=alarmsChanged)
    def alarmList(self): return database.get_all_alarms()
    @Slot()
    def stopAlarm(self):
        self.player.stop()
        self._active_alarm_id = None
    @Slot()
    def closeApp(self): sys.exit()
    @Slot()
    def snoozeAlarm(self):
        self.player.stop()
        if self._active_alarm_id is None:
            return
        self._snoozed_alarm_id = self._active_alarm_id
        self._snooze_until = (datetime.now() + timedelta(minutes=9)).replace(second=0, microsecond=0)
        self._active_alarm_id = None
        self.snoozeChanged.emit()
    @Slot(int)
    def deleteAlarm(self, id):
        conn = database.get_connection()
        conn.execute("DELETE FROM alarms WHERE id = ?", (id,))
        conn.commit(); conn.close()
        if self._active_alarm_id == id:
            self._active_alarm_id = None
        if self._snoozed_alarm_id == id:
            self._snoozed_alarm_id = None
            self._snooze_until = None
            self.snoozeChanged.emit()
        self.alarmsChanged.emit()
    @Slot(str, str)
    def createAlarm(self, t, d): database.add_alarm(t, d); self.alarmsChanged.emit()
    @Slot(int, str, str)
    def updateAlarm(self, id, t, d): database.update_alarm(id, t, d); self.alarmsChanged.emit()
    @Slot(int, bool)
    def toggleAlarm(self, id, active): database.toggle_alarm(id, active); self.alarmsChanged.emit()

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    app.setOverrideCursor(Qt.BlankCursor) 
    engine = QQmlApplicationEngine()
    backend = SmartClockBackend(app)
    engine.backend_reference = backend 
    engine.rootContext().setContextProperty("backend", backend)
    engine.load("main.qml")
    if not engine.rootObjects(): sys.exit(-1)
    sys.exit(app.exec())
