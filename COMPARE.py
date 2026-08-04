import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from FORECAST import generate_forecast
from DATABASE import get_recent_readings

def setup_tracking_table():
    conn = sqlite3.connect("alpha_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecast_tracking (
            target_date TEXT PRIMARY KEY,
            predicted_pm25 REAL,
            predicted_aqi REAL,
            actual_pm25 REAL,
            actual_aqi REAL,
            prediction_made_on TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_todays_forecast():
    """Call this daily - logs tomorrow's prediction, made today."""
    from CONVERT import pm25_to_aqi
    
    pred_day1, _, _ = generate_forecast()
    target_date = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    aqi, _, _ = pm25_to_aqi(pred_day1)
    
    conn = sqlite3.connect("alpha_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO forecast_tracking (target_date, predicted_pm25, predicted_aqi, prediction_made_on)
        VALUES (?, ?, ?, ?)
    """, (target_date, float(pred_day1), float(aqi), today))
    conn.commit()
    conn.close()
    print(f"Logged prediction for {target_date}: PM2.5={pred_day1:.1f}, AQI={aqi}")

def update_actuals():
    """Checks all pending (unfilled) predictions and fills in actuals once that date's real data exists."""
    from CONVERT import pm25_to_aqi
    
    recent = get_recent_readings()
    
    conn = sqlite3.connect("alpha_data.db")
    pending = pd.read_sql_query(
        "SELECT target_date FROM forecast_tracking WHERE actual_aqi IS NULL", conn
    )
    
    if pending.empty:
        print("No pending predictions to update.")
        conn.close()
        return
    
    cursor = conn.cursor()
    for target_date in pending['target_date']:
        matching_row = recent[recent['date'] == target_date]
        if not matching_row.empty:
            actual_pm25 = matching_row.iloc[0]['pm25']
            actual_aqi, _, _ = pm25_to_aqi(actual_pm25)
            cursor.execute("""
                UPDATE forecast_tracking SET actual_pm25 = ?, actual_aqi = ?
                WHERE target_date = ?
            """, (float(actual_pm25), float(actual_aqi), target_date))
            print(f"Updated actuals for {target_date}: PM2.5={actual_pm25}, AQI={actual_aqi}")
    
    conn.commit()
    conn.close()

def get_tracking_table(limit=14):
    conn = sqlite3.connect("alpha_data.db")
    df = pd.read_sql_query(
        "SELECT * FROM forecast_tracking ORDER BY target_date DESC LIMIT ?",
        conn, params=(limit,)
    )
    conn.close()
    return df.sort_values('target_date').reset_index(drop=True)

if __name__ == "__main__":
    setup_tracking_table()
    log_todays_forecast()
    update_actuals()
    print(get_tracking_table())