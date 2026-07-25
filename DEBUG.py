import os
from dotenv import load_dotenv
import requests
from CONVERT import pm25_to_aqi

load_dotenv()
OPENAQ_TOKEN = os.getenv("OPENAQ_TOKEN")

LOCATION_ID = 3409484
PM25_SENSOR_ID = 12238393

def fetch_current_pm25():
    url = f"https://api.openaq.org/v3/locations/{LOCATION_ID}/latest"
    headers = {"X-API-Key": OPENAQ_TOKEN}
    response = requests.get(url, headers=headers)
    data = response.json()
    for result in data["results"]:
        if result["sensorsId"] == PM25_SENSOR_ID:
            return result["datetime"]["local"], result["value"]
    return None, None

timestamp, pm25 = fetch_current_pm25()

if pm25 is not None:
    aqi, category, caution = pm25_to_aqi(pm25)
    print(f"Timestamp: {timestamp}")
    print(f"PM2.5: {pm25} µg/m³")
    print(f"AQI: {aqi}")
    print(f"Category: {category}")
    if caution:
        print(f"Caution: {caution}")
else:
    print("Failed to fetch PM2.5 reading")