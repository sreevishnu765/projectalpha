import math
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from CONVERT import aqi_to_pm25

FEED_URL = "https://airquality.cpcb.gov.in/caaqms/rss_feed"
HEADERS = {"User-Agent": "Mozilla/5.0 (AQURA research project)"}
FEED_TIMEOUT_S = 20
FEED_TTL_S = 600
FAILURE_BACKOFF_S = 60
MAX_MATCH_KM = 2.5
PM25_FIELD = "Hourly_sub_index"

_cache = {"at": 0.0, "stations": None, "failed_at": 0.0}


def _num(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_feed(content):
    root = ET.fromstring(content)
    stations = []
    for st in root.iter("Station"):
        pm25 = None
        for pi in st.findall("Pollutant_Index"):
            if pi.get("id") == "PM2.5":
                pm25 = {k: _num(pi.get(k)) for k in ("Min", "Max", "Avg", "Hourly_sub_index")}
        stations.append({
            "name": st.get("id"),
            "lat": _num(st.get("latitude")),
            "lon": _num(st.get("longitude")),
            "lastupdate": st.get("lastupdate"),
            "pm25": pm25,
        })
    return stations


def get_feed():
    now = time.time()
    if _cache["stations"] is not None and now - _cache["at"] < FEED_TTL_S:
        return _cache["stations"]
    if now - _cache["failed_at"] < FAILURE_BACKOFF_S:
        return []

    last_err = None
    for attempt in range(2):
        try:
            resp = requests.get(FEED_URL, headers=HEADERS, timeout=FEED_TIMEOUT_S)
            resp.raise_for_status()
            stations = parse_feed(resp.content)
            if not stations:
                raise ValueError("feed parsed but contained no stations")
            _cache["at"], _cache["stations"] = time.time(), stations
            return stations
        except (requests.RequestException, ET.ParseError, ValueError) as e:
            last_err = e
            if attempt == 0:
                time.sleep(2)
    _cache["failed_at"] = time.time()
    print(f"CPCB feed unavailable: {type(last_err).__name__}: {last_err}")
    return []


def _km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def find_station(feed, cfg):
    name = cfg.get("cpcb_name")
    if name:
        for s in feed:
            if s["name"] == name:
                return s, None
        for s in feed:
            if s["name"] and s["name"].lower() == name.lower():
                return s, None
        return None, None

    best, best_d = None, None
    for s in feed:
        if s["lat"] is None or s["lon"] is None:
            continue
        d = _km(cfg["lat"], cfg["lon"], s["lat"], s["lon"])
        if d <= MAX_MATCH_KM and (best_d is None or d < best_d):
            best, best_d = s, d
    return best, best_d


def reading_from_station(s):
    if not s or not s["pm25"]:
        return None
    index = s["pm25"].get(PM25_FIELD)
    if index is None or index < 0 or index > 500:
        return None
    try:
        ts = pd.to_datetime(s["lastupdate"], format="%d-%m-%Y %H:%M:%S")
    except (ValueError, TypeError):
        return None
    return ts.strftime("%Y-%m-%dT%H:%M:%S") + "+05:30", float(aqi_to_pm25(index))


def fetch_reading(station_cfg, station_label=""):
    feed = get_feed()
    if not feed:
        return []
    s, dist = find_station(feed, station_cfg)
    if s is None:
        print(f"CPCB: no feed station for {station_label or station_cfg.get('cpcb_name')}")
        return []
    if dist is not None:
        print(f"CPCB: {station_label} matched by location to '{s['name']}' ({dist:.1f} km) - pin it as cpcb_name in CHECK_STATIONS.py if correct")
    reading = reading_from_station(s)
    return [reading] if reading else []
