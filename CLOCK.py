import time
from datetime import datetime
from DATABASE import daily_update

def run_scheduler():
    while True:
        print(f"[{datetime.now()}] Running Daily Update...")
        try:
            daily_update
        except Exception as e:
            print(f"Error During Daily Update: {e}")

        time.sleep(24 * 60 * 60)

if __name__ == "__main__":
    run_scheduler()