import requests
import pandas as pd

def fetch(days = 14):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 19.0863, "longitude": 72.8888, "past_days": days,
        "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,relative_humidity_2m_max",
        "timezone": "auto"
    }

    response = requests.get(url, params = params)
    data = response.json()
    return data

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

def get_recent(weather_df, window_size=14):
    today = pd.Timestamp.now().normalize()
    cutoff_start = today - pd.Timedelta(days=window_size - 1)
    
    windowed = weather_df[(weather_df['date'] >= cutoff_start) & (weather_df['date'] <= today)]
    return windowed.reset_index(drop=True)

print(get_recent(parse(fetch())))