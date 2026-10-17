import time
import requests
import pandas as pd
from CHECK_STATIONS import STATIONS

# Kurla's coordinates
DEFAULT_LAT, DEFAULT_LON = STATIONS["Kurla"]["lat"], STATIONS["Kurla"]["lon"]

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def _get_daily(params, retries=3, backoff_s=(3, 10)):
    last_err = None
    for attempt in range(retries):
        try:
            response = requests.get(OPEN_METEO_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            if "daily" not in data:
                raise ValueError(f"no 'daily' block in response: {str(data)[:200]}")
            return data
        except (requests.RequestException, ValueError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff_s[min(attempt, len(backoff_s) - 1)])
    raise RuntimeError(f"Open-Meteo request failed after {retries} attempts: {last_err}")

# weather api call
def fetch(days = 14, lat = DEFAULT_LAT, lon = DEFAULT_LON):
    params = {
        "latitude": lat, "longitude": lon, "past_days": days,
        "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,relative_humidity_2m_max",
        "timezone": "auto"
    }
    return _get_daily(params)

# data parsing
def parse(data):
    weather_df = pd.DataFrame({
        "date": data["daily"]["time"],
        "temperature_2m_max (°C)": data["daily"]["temperature_2m_max"],
        "temperature_2m_min (°C)": data["daily"]["temperature_2m_min"],
        "wind_speed_10m_max (km/h)": data["daily"]["wind_speed_10m_max"],
        "relative_humidity_2m_max (%)": data["daily"]["relative_humidity_2m_max"]
    })
    weather_df["date"] = pd.to_datetime(weather_df["date"])
    return weather_df

# data filtering
def get_recent(weather_df, window_size=14):
    today = pd.Timestamp.now().normalize()
    cutoff_start = today - pd.Timedelta(days=window_size - 1)
    
    windowed = weather_df[(weather_df['date'] >= cutoff_start) & (weather_df['date'] <= today)]
    return windowed.reset_index(drop=True)

# forecasted precipitation call
PRECIP_FORECAST_THRESHOLD = 2.5

def fetch_precip_forecast(days = 3, lat = DEFAULT_LAT, lon = DEFAULT_LON):
    params = {
        "latitude": lat, "longitude": lon, "forecast_days": days,
        "daily": "precipitation_sum",
        "timezone": "auto"
    }
    return _get_daily(params)

# parse forecasted precipitation
def get_precip_flags(days = 3, threshold = PRECIP_FORECAST_THRESHOLD, lat = DEFAULT_LAT, lon = DEFAULT_LON):
    data = fetch_precip_forecast(days = days, lat = lat, lon = lon)
    today = pd.Timestamp.now().normalize()

    forecast_df = pd.DataFrame({
        "date": pd.to_datetime(data["daily"]["time"]),
        "precipitation_sum (mm)": data["daily"]["precipitation_sum"]
    })

    flags = {}
    for h in range(1, days + 1):
        target_date = today + pd.Timedelta(days=h)
        matching = forecast_df[forecast_df["date"] == target_date]
        if matching.empty:
            flags[f"precip_flag_tgt{h}"] = 0.0
        else:
            precip_value = matching.iloc[0]["precipitation_sum (mm)"]
            flags[f"precip_flag_tgt{h}"] = float(precip_value > threshold)

    return flags
