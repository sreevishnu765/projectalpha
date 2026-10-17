import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
OPENAQ_TOKEN = os.getenv("OPENAQ_TOKEN")

STATIONS = {
    "Kurla":                {"location_id": 6945,    "cpcb_name": "Kurla, Mumbai - MPCB",                  "lat": 19.0728, "lon": 72.8826},
    "Bandra Kurla Complex": {"location_id": 3409482, "cpcb_name": "Bandra Kurla Complex, Mumbai - MPCB",   "lat": 19.0669, "lon": 72.8686},
    "Worli":                {"location_id": 3409323, "cpcb_name": "Siddharth Nagar-Worli, Mumbai - IITM",  "lat": 19.0176, "lon": 72.8168},
    "Byculla":              {"location_id": 3409510, "cpcb_name": "Byculla, Mumbai - BMC",                 "lat": 18.9757, "lon": 72.8325},
    "Chembur":              {"location_id": 3409483, "cpcb_name": "Chembur, Mumbai - MPCB",                "lat": 19.0522, "lon": 72.8994},
    "Powai":                {"location_id": 6956,    "cpcb_name": None,                                    "lat": 19.1176, "lon": 72.9060},
    "Andheri":              {"location_id": None,    "cpcb_name": "Chakala-Andheri East, Mumbai - IITM",   "lat": 19.1197, "lon": 72.8468},
    "Dadar":                {"location_id": None,    "cpcb_name": None,                                    "lat": 19.0178, "lon": 72.8478},
}

SENSOR_CACHE_TTL_S = 3600
_sensor_ids_cache = {}


def find_pm25_sensor_ids(location_id):
    cached = _sensor_ids_cache.get(location_id)
    if cached and time.time() - cached[0] < SENSOR_CACHE_TTL_S:
        return cached[1]

    url = f"https://api.openaq.org/v3/locations/{location_id}"
    headers = {"X-API-Key": OPENAQ_TOKEN}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()

    ids = []
    for result in data.get("results", []):
        for sensor in result.get("sensors", []):
            if sensor.get("parameter", {}).get("name") == "pm25":
                ids.append(sensor["id"])

    if ids:
        _sensor_ids_cache[location_id] = (time.time(), ids)
    return ids


def is_station_configured(station):
    cfg = STATIONS.get(station)
    if cfg is None:
        return False
    return cfg["location_id"] is not None or bool(cfg.get("cpcb_name"))
