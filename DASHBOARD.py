import streamlit as st
import pandas as pd
from FORECAST import generate_full_report
from DATABASE import get_recent_readings, fetch_pm25
from CONVERT import pm25_to_aqi, get_advisory
from datetime import datetime

st.set_page_config(page_title = "AQI Forecasting Dashboard", layout = "wide")

st.title("AQI Forecasting Dashboard")
st.caption("Kurla Monitoring Station")

recent_data = get_recent_readings()
last_date = recent_data['date'].iloc[-1]
st.caption(f"Last Updated: {last_date}")

sensitivity = st.radio("Sensitivity",
                       options = ["general", "sensitive"],
                       format_func = lambda x : "General Public" if x == "general" else "Sensitive Groups",
                       horizontal = True)

report = generate_full_report(sensitivity)

latest_reading = recent_data.iloc[-1]
st.divider()

today_aqi, today_category, today_caution = pm25_to_aqi(latest_reading['pm25'])

col1, col2, col3 = st.columns(3)
col4, col5, col6= st.columns(3)

with col1:
    st.metric("Current AQI", today_aqi)
with col2:
    (st.metric("PM2.5", f"{latest_reading['pm25']:.1f} µg/m³"))
with col3:
    st.metric("Temperature", f"{latest_reading['temperature_2m_max']:.1f} °C")
with col4:
    st.metric("Humidity", f"{latest_reading['relative_humidity_2m_max']:.0f}%")
with col5:
    st.metric("Wind Speed", f"{latest_reading['wind_speed_10m_max']:.1f} km/h")
with col6:
    st.metric("Category", today_category)

st.divider()

st.subheader("Advisory")
today_advisory = get_advisory(today_category, sensitivity)  # need get_advisory imported too
st.info(today_advisory)

if today_caution:
    st.warning(today_caution)

st.subheader("3-Day Forecast")
forecast_col1, forecast_col2, forecast_col3 = st.columns(3)

forecast_days = [("Day 1", "day1", forecast_col1), ("Day 2", "day2", forecast_col2), ("Day 3", "day3", forecast_col3),]

for label, key, col in forecast_days:
    with col:
        st.metric(label, report[key]['aqi'], help = report[key]['category'])
        st.caption(report[key]['category'])
        st.write(report[key]['advisory'])
        if report[key]['caution']:
            st.warning(report[key]['caution'])

st.divider()

st.subheader("Recent AQI Trend (14 Days)")
recent_data['aqi'] = recent_data['pm25'].apply(lambda x: pm25_to_aqi(x)[0])
chart_data = recent_data[['date', 'aqi']].set_index('date')
st.line_chart(chart_data)

st.divider()

st.subheader("Recent PM2.5 Trend (14 Days)")
chart_data = recent_data[['date', 'pm25']].set_index('date')
st.line_chart(chart_data)

st.divider()

st.subheader("System Status")
status_col1, status_col2, status_col3, status_col4 = st.columns(4)

with status_col1:
    try:
        timestamp, pm25 = fetch_pm25()

        if pm25 is not None:
            st.success("✓ API Connected")
        else:
            st.error("✗ API Unavailable")

    except Exception:
        st.error("✗ API Unavailable")

with status_col2:
    try:
        _ = get_recent_readings()
        st.success("✓ SQLite Connected")
    except Exception:
        st.error("✗ SQLite Error")

with status_col3:
    st.success("✓ Model Loaded")
    st.caption("MAPE: 16.79% (Day+1)")

with status_col4:
    from datetime import datetime
    last_update_date = recent_data['date'].iloc[-1]
    today = datetime.now().date()
    if pd.to_datetime(last_update_date).date() == today:
        st.success("✓ Scheduler Current")
    else:
        st.warning(f"⚠ Last run: {last_update_date}")