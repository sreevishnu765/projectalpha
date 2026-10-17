import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from DATABASE import daily_update_all_stations, fetch_pm25
from CONVERT import pm25_to_aqi
from FORECAST import generate_mk6_forecast

DB = "alpha_data.db"
log_path = "scheduler_log.txt"

def log(message):
    with open(log_path, "a") as f:
        f.write(f"{message}\n")
    print(message)

# table setup
def setup_admin_tables():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pm25_raw_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            timestamp TEXT,
            pm25 REAL,
            aqi REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_dev_tracking (
            target_date TEXT PRIMARY KEY,
            prediction_made_on TEXT,
            mk6_predicted_pm25 REAL, mk6_predicted_aqi REAL,
            mk6_closest_actual_pm25 REAL, mk6_closest_actual_aqi REAL, mk6_closest_time TEXT, mk6_closest_diff REAL,
            day_avg_actual_pm25 REAL, day_avg_actual_aqi REAL,
            day_min_actual_aqi REAL, day_max_actual_aqi REAL,
            n_readings INTEGER
        )
    """)
    conn.commit()
    conn.close()

def log_raw_reading():
    timestamp, pm25 = fetch_pm25()
    if timestamp is None:
        print("Raw log: PM2.5 fetch failed, skipping this run's snapshot")
        return

    date_str = pd.to_datetime(timestamp).tz_localize(None).strftime("%Y-%m-%d")
    aqi, _, _ = pm25_to_aqi(pm25)

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    already = cursor.execute("SELECT 1 FROM pm25_raw_log WHERE timestamp = ?", (str(timestamp),)).fetchone()
    if already:
        conn.close()
        print(f"Raw log: reading @ {timestamp} already logged - sensor hasn't reported anything new")
        return
    cursor.execute(
        "INSERT INTO pm25_raw_log (date, timestamp, pm25, aqi) VALUES (?, ?, ?, ?)",
        (date_str, str(timestamp), float(pm25), float(aqi) if aqi is not None else None),
    )
    conn.commit()
    conn.close()
    print(f"Raw log: {date_str} @ {timestamp} -> PM2.5={pm25}, AQI={aqi}")

def log_admin_forecast():
    target_date = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().date().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB)
    existing = pd.read_sql_query(
        "SELECT prediction_made_on FROM admin_dev_tracking WHERE target_date = ?",
        conn, params=(target_date,),
    )
    conn.close()
    if not existing.empty and existing.iloc[0]["prediction_made_on"] == today:
        print(f"Admin forecast for {target_date} already logged today - skipping")
        return

    mk6_day1, _, _ = generate_mk6_forecast()
    if mk6_day1 is None:
        print(f"Admin forecast for {target_date}: no fresh data to forecast from - nothing logged")
        return

    mk6_pm25 = max(float(mk6_day1), 0.0)
    mk6_aqi = pm25_to_aqi(mk6_pm25)[0]

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO admin_dev_tracking
            (target_date, prediction_made_on, mk6_predicted_pm25, mk6_predicted_aqi)
        VALUES (?, ?, ?, ?)
    """, (target_date, today, mk6_pm25, float(mk6_aqi) if mk6_aqi is not None else None))
    conn.commit()
    conn.close()
    print(f"Admin forecast logged for {target_date}: MK6={mk6_aqi}")

def finalize_admin_actuals():
    today = datetime.now().date().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB)
    pending = pd.read_sql_query(
        "SELECT target_date, mk6_predicted_aqi FROM admin_dev_tracking WHERE day_avg_actual_aqi IS NULL",
        conn,
    )

    cursor = conn.cursor()
    for _, row in pending.iterrows():
        target_date = row["target_date"]
        if target_date >= today:
            continue

        readings = pd.read_sql_query(
            "SELECT timestamp, pm25, aqi FROM pm25_raw_log WHERE date = ?",
            conn, params=(target_date,),
        )
        if readings.empty:
            continue

        day_avg_pm25 = readings["pm25"].mean()
        day_avg_aqi, _, _ = pm25_to_aqi(day_avg_pm25)

        update_fields = {
            "day_avg_actual_pm25": float(day_avg_pm25),
            "day_avg_actual_aqi": float(day_avg_aqi) if day_avg_aqi is not None else None,
            "day_min_actual_aqi": float(readings["aqi"].min()),
            "day_max_actual_aqi": float(readings["aqi"].max()),
            "n_readings": int(len(readings)),
        }

        pred_aqi = row["mk6_predicted_aqi"]
        if pred_aqi is not None and not pd.isna(pred_aqi):
            diffs = (readings["aqi"] - pred_aqi).abs()
            if not diffs.dropna().empty:
                closest = readings.loc[diffs.idxmin()]
                update_fields["mk6_closest_actual_pm25"] = float(closest["pm25"])
                update_fields["mk6_closest_actual_aqi"] = float(closest["aqi"])
                update_fields["mk6_closest_time"] = str(closest["timestamp"])
                update_fields["mk6_closest_diff"] = float(abs(closest["aqi"] - pred_aqi))

        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        cursor.execute(
            f"UPDATE admin_dev_tracking SET {set_clause} WHERE target_date = ?",
            (*update_fields.values(), target_date),
        )
        print(f"Finalized {target_date}: day_avg_aqi={update_fields['day_avg_actual_aqi']}, n_readings={update_fields['n_readings']}")

    conn.commit()
    conn.close()

def run_step(name, fn):
    try:
        return fn()
    except Exception as e:
        log(f"[{datetime.now()}] {name} failed: {e}")
        return None

def main():
    log(f"[{datetime.now()}] Scheduled update started.")

    run_step("setup_admin_tables", setup_admin_tables)

    results = run_step("station update", daily_update_all_stations) or {}
    run_step("raw log", log_raw_reading)
    run_step("admin forecast", log_admin_forecast)
    run_step("finalize actuals", finalize_admin_actuals)

    updated = [s for s, ok in results.items() if ok]
    silent = [s for s, ok in results.items() if not ok]
    summary = f"stations updated: {len(updated)}/{len(results)}"
    if silent:
        summary += f" (no new data: {', '.join(silent)})"
    log(f"[{datetime.now()}] Update finished - {summary}")

if __name__ == "__main__":
    main()
