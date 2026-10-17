import os
import sqlite3
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
DB = "alpha_data.db"

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

def get_admin_tracking_table(limit=30):
    setup_admin_tables()
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        "SELECT * FROM admin_dev_tracking ORDER BY target_date DESC LIMIT ?",
        conn, params=(limit,),
    )
    conn.close()
    return df.sort_values("target_date").reset_index(drop=True)

st.set_page_config(page_title="MK6 Tracking Dashboard", layout="wide")
st.title("MK6 Tracking Dashboard")
st.caption("MK6 is the finalised model - this page tracks how its day+1 forecast holds up against what the sensor actually reported.")

if ADMIN_PASSWORD:
    entered = st.text_input("Admin password", type="password")
    if entered != ADMIN_PASSWORD:
        st.info("Enter the admin password to view tracking data.")
        st.stop()

df = get_admin_tracking_table(limit=30)

if df.empty:
    st.info("No tracking data yet - check back after a day or two of scheduled runs.")
    st.stop()

done = df.dropna(subset=["day_avg_actual_aqi", "mk6_predicted_aqi"])
if not done.empty:
    err_vs_avg = (done["mk6_predicted_aqi"] - done["day_avg_actual_aqi"]).abs()
    in_range = ((done["mk6_predicted_aqi"] >= done["day_min_actual_aqi"]) &
                (done["mk6_predicted_aqi"] <= done["day_max_actual_aqi"])).mean()
    m1, m2, m3 = st.columns(3)
    m1.metric("Days finalized", len(done))
    m2.metric("MAE vs day average (AQI)", f"{err_vs_avg.mean():.1f}")
    m3.metric("Prediction within day's min-max", f"{in_range * 100:.0f}%")

st.divider()
st.subheader("MK6 prediction vs. closest actual, and day average")

display_cols = {
    "target_date": "Date",
    "mk6_predicted_aqi": "MK6 Pred",
    "mk6_closest_actual_aqi": "Closest Actual",
    "mk6_closest_diff": "Closest Diff",
    "day_avg_actual_aqi": "Day Avg Actual",
    "day_min_actual_aqi": "Day Min",
    "day_max_actual_aqi": "Day Max",
    "n_readings": "# Readings",
}
available_cols = [c for c in display_cols if c in df.columns]
show_df = df[available_cols].rename(columns=display_cols)
st.dataframe(show_df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Raw snapshot log")
st.caption("One reading captured per scheduled run (10am/4pm/10pm), most recent first. A reading the sensor hasn't refreshed since the last run isn't logged twice.")

conn = sqlite3.connect(DB)
raw_df = pd.read_sql_query("SELECT * FROM pm25_raw_log ORDER BY id DESC LIMIT 60", conn)
conn.close()
if raw_df.empty:
    st.info("No snapshots logged yet.")
else:
    st.dataframe(raw_df, use_container_width=True, hide_index=True)
