import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_TOKEN")}

location_id = 6945  # Kurla MPCB
pm25_sensor_ids = [12235834, 19978]

resp = requests.get(f"https://api.openaq.org/v3/locations/{location_id}/sensors", headers=headers)
data = resp.json()

for sensor in data["results"]:
    if sensor["id"] in pm25_sensor_ids:
        print(f"--- sensorsId={sensor['id']} ---")
        print(json.dumps(sensor, indent=2))
        print()