from datetime import datetime
from DATABASE import daily_update
from COMPARE import setup_tracking_table, log_todays_forecast, update_actuals

log_path = "scheduler_log.txt"

def log(message):
    with open(log_path, "a") as f:
        f.write(f"{message}\n")
    print(message)

log(f"[{datetime.now()}] Scheduled update started.")

try:
    setup_tracking_table()
    daily_update()
    log_todays_forecast()
    update_actuals()
    log(f"[{datetime.now()}] Update completed successfully.")
except Exception as e:
    log(f"[{datetime.now()}] Update failed: {e}")