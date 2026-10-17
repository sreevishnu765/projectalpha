import os
from dotenv import load_dotenv
import sqlite3
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from CALL import fetch, parse, get_recent
from CPCB import fetch_reading as fetch_cpcb_reading
from CHECK_STATIONS import STATIONS, find_pm25_sensor_ids, is_station_configured

load_dotenv()

# get api token
OPENAQ_TOKEN = os.getenv("OPENAQ_TOKEN")

conn = sqlite3.connect("alpha_data.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_readings (
        date TEXT,
        station TEXT NOT NULL DEFAULT 'Kurla',
        reading_timestamp TEXT,
        pm25 REAL,
        temperature_2m_max REAL,
        temperature_2m_min REAL,
        wind_speed_10m_max REAL,
        relative_humidity_2m_max REAL,
        PRIMARY KEY (date, station))
""")

conn.commit()
conn.close()

# data insertion
def insert_reading(date, station, reading_timestamp, pm25, temp_max, temp_min, wind, humidity):
    conn = sqlite3.connect("alpha_data.db")
    cursor = conn.cursor()
    cursor.execute("""INSERT OR REPLACE INTO daily_readings 
        (date, station, reading_timestamp, pm25, temperature_2m_max, temperature_2m_min, wind_speed_10m_max, relative_humidity_2m_max)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (date, station, reading_timestamp, pm25, temp_max, temp_min, wind, humidity))
    conn.commit()
    conn.close()

# irrelevant data deletion
def delete_old_readings(station=None):
    conn = sqlite3.connect("alpha_data.db")
    cursor = conn.cursor()
    if station:
        cursor.execute("DELETE FROM daily_readings WHERE date < date('now', '-14 days') AND station = ?", (station,))
    else:
        cursor.execute("DELETE FROM daily_readings WHERE date < date('now', '-14 days')")
    conn.commit()
    conn.close()

# database calling
def get_recent_readings(station="Kurla"):
    conn = sqlite3.connect("alpha_data.db")
    df = pd.read_sql_query(
        "SELECT * FROM daily_readings WHERE station = ? ORDER BY date ASC",
        conn, params=(station,),
    )
    conn.close()
    return df

# pollutant api call
OPENAQ_TIMEOUT_S = 20
MEASUREMENTS_PAGE_LIMIT = 1000
MEASUREMENTS_MAX_PAGES = 3

def _fetch_sensor_window(sensor_id, days):
    headers = {"X-API-Key": OPENAQ_TOKEN}
    datetime_from = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows = []
    for page in range(1, MEASUREMENTS_MAX_PAGES + 1):
        resp = requests.get(
            f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements",
            headers=headers,
            params={"datetime_from": datetime_from, "limit": MEASUREMENTS_PAGE_LIMIT, "page": page},
            timeout=OPENAQ_TIMEOUT_S,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        for r in results:
            value = r.get("value")
            if value is None or value < 0:
                continue
            period = r["period"]["datetimeFrom"]
            rows.append((period["utc"], period["local"], float(value)))
        if len(results) < MEASUREMENTS_PAGE_LIMIT:
            break
    return rows

def _fetch_openaq_window(station, days):
    location_id = STATIONS[station]["location_id"]
    if location_id is None:
        return []
    try:
        sensor_ids = find_pm25_sensor_ids(location_id)
    except (requests.RequestException, KeyError, TypeError) as e:
        print(f"openaq: sensor lookup failed for {station} (location_id={location_id}): {e}")
        return []
    if not sensor_ids:
        print(f"openaq: no pm25 sensor listed for {station} (location_id={location_id})")
        return []

    rows = []
    for sensor_id in sensor_ids:
        try:
            rows.extend(_fetch_sensor_window(sensor_id, days))
        except (requests.RequestException, KeyError, TypeError, ValueError) as e:
            print(f"openaq: {station} sensor {sensor_id} failed: {e}")

    rows.sort(key=lambda r: r[0])
    return [(local, value) for _, local, value in rows]

PM25_PROVIDERS = [p.strip().lower() for p in os.getenv("PM25_PROVIDERS", "cpcb,openaq").split(",") if p.strip()]

def fetch_pm25_window(station="Kurla", days=7):
    if not is_station_configured(station):
        return []

    candidates = []
    for provider in PM25_PROVIDERS:
        if provider == "cpcb":
            readings = fetch_cpcb_reading(STATIONS[station], station)
        elif provider == "openaq":
            readings = _fetch_openaq_window(station, days)
        else:
            continue
        if readings:
            candidates.append(readings)
            if not is_reading_stale(readings[-1][0]):
                break

    if not candidates:
        return []
    return max(candidates, key=lambda r: pd.to_datetime(r[-1][0], utc=True))

def fetch_pm25(station="Kurla", days=3):
    readings = fetch_pm25_window(station, days)
    if not readings:
        print(f"fetch_pm25: no readings for {station} in the last {days} days")
        return None, None
    return readings[-1]


# freshness check
STALE_THRESHOLD_HOURS = 18

def is_reading_stale(reading_timestamp_str, threshold_hours=STALE_THRESHOLD_HOURS):
    if reading_timestamp_str is None or pd.isna(reading_timestamp_str):
        return True
    try:
        reading_time = pd.to_datetime(reading_timestamp_str).tz_localize(None)
    except Exception:
        return True
    age = pd.Timestamp.now() - reading_time
    return age > pd.Timedelta(hours=threshold_hours)

# function for daily updation
def daily_update(station="Kurla", days=7):
    readings = fetch_pm25_window(station, days)
    if not readings:
        print(f"Failed to fetch PM2.5 for {station} - skipping update")
        return False

    latest_per_day = {}
    for local_ts, value in readings:
        ts = pd.to_datetime(local_ts).tz_localize(None)
        latest_per_day[ts.strftime("%Y-%m-%d")] = (ts, value)

    station_coords = STATIONS[station]
    try:
        weather_window = get_recent(parse(fetch(lat=station_coords["lat"], lon=station_coords["lon"])))
    except Exception as e:
        print(f"Weather fetch failed for {station}: {e} - skipping update")
        return False

    weather_cols = ['temperature_2m_max (°C)', 'temperature_2m_min (°C)', 'wind_speed_10m_max (km/h)', 'relative_humidity_2m_max (%)']
    inserted = 0
    for date_str, (ts, value) in sorted(latest_per_day.items()):
        matching_weather = weather_window[weather_window["date"].dt.strftime("%Y-%m-%d") == date_str]
        if matching_weather.empty:
            print(f"No matching weather data for {station} {date_str} - skipping that day")
            continue
        row = matching_weather.iloc[0]
        if row[weather_cols].isna().any():
            print(f"Incomplete weather data for {station} {date_str} - skipping that day")
            continue
        insert_reading(date_str, station, ts.isoformat(), float(value), float(row[weather_cols[0]]), float(row[weather_cols[1]]), float(row[weather_cols[2]]), float(row[weather_cols[3]]))
        inserted += 1

    delete_old_readings(station)
    newest = max(latest_per_day.values(), key=lambda x: x[0])
    print(f"{station}: stored {inserted} day(s); newest reading {newest[0].isoformat()} PM2.5={newest[1]}")
    return inserted > 0


def daily_update_all_stations():
    results = {}
    for station in STATIONS:
        if not is_station_configured(station):
            continue
        try:
            results[station] = daily_update(station)
        except Exception as e:
            print(f"daily_update failed for {station}: {e}")
            results[station] = False
    return results

if __name__ == "__main__":
    daily_update()
    print(get_recent_readings())
