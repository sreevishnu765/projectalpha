import os
from dotenv import load_dotenv
import sqlite3
import pandas as pd
import requests
from CALL import fetch, parse, get_recent

load_dotenv()
API_TOKEN = os.getenv("AQICN_TOKEN")
OPENAQ_TOKEN = os.getenv("OPENAQ_TOKEN")

conn = sqlite3.connect("alpha_data.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_readings (
        date TEXT PRIMARY KEY,
        pm25 REAL,
        temperature_2m_max REAL,
        temperature_2m_min REAL,
        wind_speed_10m_max REAL,
        relative_humidity_2m_max REAL)
""")

conn.commit()
conn.close()

def insert_reading(date, pm25, temp_max, temp_min, wind, humidity):
    conn = sqlite3.connect("alpha_data.db")
    cursor = conn.cursor()
    cursor.execute("""INSERT OR REPLACE INTO daily_readings 
        (date, pm25, temperature_2m_max, temperature_2m_min, wind_speed_10m_max, relative_humidity_2m_max)
        VALUES (?, ?, ?, ?, ?, ?)""", (date, pm25, temp_max, temp_min, wind, humidity))
    conn.commit()
    conn.close()

def delete_old_readings():
    conn = sqlite3.connect("alpha_data.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_readings WHERE date < date('now', '-14 days')")
    conn.commit()
    conn.close()

def get_recent_readings():
    conn = sqlite3.connect("alpha_data.db")
    df = pd.read_sql_query("SELECT * FROM daily_readings ORDER BY date ASC", conn)
    conn.close()
    return df

def fetch_pm25():
    location_id = 3409484
    url = f"https://api.openaq.org/v3/locations/{location_id}/latest"
    headers = {"X-API-Key": OPENAQ_TOKEN}
    response = requests.get(url, headers=headers)
    data = response.json()
    for result in data["results"]:
        if result["sensorsId"] == 12252658:
            return result["datetime"]["local"], result["value"]
    return None, None

def daily_update():
    weather_raw = fetch()
    weather_df = parse(weather_raw)
    weather_window = get_recent(weather_df)
    
    date_str, pm25 = fetch_pm25()
    if date_str is None:
        print("Failed to fetch PM2.5 - skipping update")
        return
    
    pollutant_date = pd.to_datetime(date_str).tz_localize(None).strftime("%Y-%m-%d")
    matching_weather = weather_window[weather_window["date"].dt.strftime("%Y-%m-%d") == pollutant_date]
    
    if matching_weather.empty:
        print(f"No matching weather data for {pollutant_date} - skipping insert")
        return
    
    row = matching_weather.iloc[0]
    insert_reading(
    pollutant_date,
    float(pm25),
    float(row['temperature_2m_max (°C)']),
    float(row['temperature_2m_min (°C)']),
    float(row['wind_speed_10m_max (km/h)']),
    float(row['relative_humidity_2m_max (%)'])
    )
    
    delete_old_readings()
    print(f"Inserted reading for {pollutant_date}: PM2.5={pm25}")

if __name__ == "__main__":
    date, pm25 = fetch_pm25()
    print(date, pm25)
    daily_update()
    print(get_recent_readings())