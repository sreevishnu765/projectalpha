import streamlit as st
import pandas as pd
from FORECAST import generate_full_report
from DATABASE import get_recent_readings, fetch_pm25
from CONVERT import pm25_to_aqi, get_advisory
from COMPARE import get_tracking_table
from datetime import datetime, timedelta

STATIONS = ["Kurla", "Bandra", "Worli", "Chembur", "Powai", "Andheri", "Dadar"]
AVAILABLE_STATIONS = {"Kurla"}

EARTH_UNAVAILABLE_SVG = """
<div style="text-align:center; padding: 32px 0 16px 0;">
<svg width="160" height="160" viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">
  <circle cx="80" cy="80" r="70" fill="#a9bdc9"/>
  <path d="M40,50 Q55,35 75,48 Q90,38 100,55 Q112,65 95,80 Q105,95 80,100 Q60,110 45,90 Q25,80 40,50 Z" fill="#8fac93" opacity="0.85"/>
  <ellipse cx="50" cy="35" rx="30" ry="10" fill="#ffffff" opacity="0.75"/>
  <ellipse cx="100" cy="118" rx="26" ry="9" fill="#ffffff" opacity="0.7"/>
  <circle cx="80" cy="80" r="70" fill="none" stroke="#7c93a1" stroke-width="1.5" opacity="0.5"/>
  <circle cx="65" cy="72" r="5" fill="#3a3a3a"/>
  <circle cx="95" cy="72" r="5" fill="#3a3a3a"/>
  <line x1="68" y1="105" x2="92" y2="92" stroke="#3a3a3a" stroke-width="4" stroke-linecap="round"/>
</svg>
</div>
"""

# CPCB AQI scale: (range_low, range_high, color, label) - matches CONVERT.py breakpoints
AQI_SCALE = [
    (0, 50, "#4CAF50", "Good"),
    (50, 100, "#A0CE4E", "Satisfactory"),
    (100, 200, "#FFD43B", "Moderate"),
    (200, 300, "#FF9800", "Poor"),
    (300, 400, "#F4511E", "Very Poor"),
    (400, 500, "#7E0023", "Severe"),
]
AQI_SCALE_MAX = 500

# AQI category -> earth accessory tier
FLOWER_CATEGORIES = {"Good", "Satisfactory"}
MASK_CATEGORIES = {"Moderate", "Poor"}
GAS_MASK_CATEGORIES = {"Very Poor", "Severe"}

# Temperature thresholds for the sun/frost badge (independent of AQI category)
HOT_THRESHOLD_C = 35
COLD_THRESHOLD_C = 15

FLOWER_ACCESSORY = """
  <path d="M135,130 Q142,122 149,130" stroke="#2b2b2b" stroke-width="4" fill="none" stroke-linecap="round"/>
  <path d="M171,130 Q178,122 185,130" stroke="#2b2b2b" stroke-width="4" fill="none" stroke-linecap="round"/>
  <path d="M148,154 Q160,166 172,154" stroke="#2b2b2b" stroke-width="3.5" fill="none" stroke-linecap="round"/>
  <g transform="translate(35,285)">
    <line x1="10" y1="-10" x2="24" y2="-24" stroke="#4caf6a" stroke-width="5" stroke-linecap="round"/>
    <circle r="13" fill="#ffdd55"/>
    <circle cx="-19" cy="-9" r="13" fill="#ff6b9d"/>
    <circle cx="19" cy="-9" r="13" fill="#ff6b9d"/>
    <circle cx="-19" cy="15" r="13" fill="#ff6b9d"/>
    <circle cx="19" cy="15" r="13" fill="#ff6b9d"/>
  </g>
"""

MASK_ACCESSORY = """
  <g clip-path="url(#cornerGlobeClip)">
    <ellipse cx="160" cy="210" rx="150" ry="110" fill="#b9d3e3" stroke="#5f7d90" stroke-width="5"/>
  </g>
  <circle cx="128" cy="72" r="11" fill="#2b2b2b"/>
  <circle cx="192" cy="72" r="11" fill="#2b2b2b"/>
  <path d="M35,135 Q0,100 40,85" stroke="#5f7d90" stroke-width="5" fill="none" stroke-linecap="round"/>
  <path d="M285,135 Q320,100 280,85" stroke="#5f7d90" stroke-width="5" fill="none" stroke-linecap="round"/>
"""

GAS_MASK_ACCESSORY = """
  <g clip-path="url(#cornerGlobeClip)">
    <ellipse cx="160" cy="190" rx="150" ry="130" fill="#6b8085" stroke="#33454a" stroke-width="5"/>
  </g>
  <circle cx="124" cy="122" r="28" fill="#cfe8ee" stroke="#33454a" stroke-width="5"/>
  <circle cx="196" cy="122" r="28" fill="#cfe8ee" stroke="#33454a" stroke-width="5"/>
  <rect x="141" y="216" width="38" height="42" rx="9" fill="#33454a"/>
  <circle cx="160" cy="276" r="18" fill="#33454a"/>
  <path d="M25,115 Q-10,85 30,72" stroke="#33454a" stroke-width="6" fill="none" stroke-linecap="round"/>
  <path d="M295,115 Q330,85 290,72" stroke="#33454a" stroke-width="6" fill="none" stroke-linecap="round"/>
"""

# Sun/frost badge, top-right - same rough size as the flower, opposite corner,
# so it never overlaps the AQI accessory regardless of which one is active.
SUN_BADGE = """
  <g transform="translate(292,28)">
    <circle r="17" fill="#ffe27a" stroke="#e08e00" stroke-width="3"/>
    <g stroke="#e08e00" stroke-width="3" stroke-linecap="round">
      <line x1="0" y1="-25" x2="0" y2="-20"/>
      <line x1="0" y1="20" x2="0" y2="25"/>
      <line x1="-25" y1="0" x2="-20" y2="0"/>
      <line x1="25" y1="0" x2="20" y2="0"/>
      <line x1="-18" y1="-18" x2="-14" y2="-14"/>
      <line x1="14" y1="14" x2="18" y2="18"/>
      <line x1="-18" y1="18" x2="-14" y2="14"/>
      <line x1="14" y1="-14" x2="18" y2="-18"/>
    </g>
  </g>
"""

FROST_BADGE = """
  <g transform="translate(292,28)">
    <circle r="17" fill="#d6f2ff" stroke="#5aa8cc" stroke-width="3"/>
    <g stroke="#3d7fa3" stroke-width="3" stroke-linecap="round">
      <line x1="0" y1="-14" x2="0" y2="14"/>
      <line x1="-12" y1="-7" x2="12" y2="7"/>
      <line x1="-12" y1="7" x2="12" y2="-7"/>
    </g>
  </g>
"""

def get_earth_accessory(category):
    if category in FLOWER_CATEGORIES:
        return FLOWER_ACCESSORY
    if category in MASK_CATEGORIES:
        return MASK_ACCESSORY
    if category in GAS_MASK_CATEGORIES:
        return GAS_MASK_ACCESSORY
    return ""

def get_temp_badge(temp_c):
    if temp_c is None:
        return ""
    if temp_c >= HOT_THRESHOLD_C:
        return SUN_BADGE
    if temp_c <= COLD_THRESHOLD_C:
        return FROST_BADGE
    return ""

def render_earth_corner(category, temp_c, size = 130):
    """Renders the earth mascot in the header corner - no background/CSS tricks,
    just a normal inline SVG. Carries two independent accessories: the AQI-linked
    one (flower/mask/gas mask, bottom-left) and the temperature badge (sun/frost,
    top-right), so both can show at once without colliding."""
    accessory_svg = get_earth_accessory(category)
    temp_badge_svg = get_temp_badge(temp_c)

    earth_html = f"""
    <div style="text-align:center;">
    <svg width="{size}" height="{size}" viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="cornerEarthShade" cx="35%" cy="30%" r="75%">
          <stop offset="0%" stop-color="#6fc6e8"/>
          <stop offset="60%" stop-color="#3fa6d8"/>
          <stop offset="100%" stop-color="#2778a8"/>
        </radialGradient>
        <clipPath id="cornerGlobeClip">
          <circle cx="160" cy="160" r="140"/>
        </clipPath>
      </defs>
      <circle cx="160" cy="160" r="140" fill="url(#cornerEarthShade)"/>
      <path d="M80,100 Q110,70 150,96 Q180,76 200,110 Q224,130 190,160 Q210,190 160,200 Q120,220 90,180 Q50,160 80,100 Z" fill="#4caf6a" opacity="0.9"/>
      <path d="M190,70 Q224,60 244,90 Q260,116 230,136 Q204,120 190,70 Z" fill="#4caf6a" opacity="0.85"/>
      <ellipse cx="90" cy="70" rx="56" ry="20" fill="#ffffff" opacity="0.9"/>
      <ellipse cx="200" cy="240" rx="52" ry="18" fill="#ffffff" opacity="0.85"/>
      <circle cx="160" cy="160" r="140" fill="none" stroke="#1c5f88" stroke-width="2" opacity="0.4"/>
      {accessory_svg}
      {temp_badge_svg}
    </svg>
    </div>
    """
    st.markdown(earth_html, unsafe_allow_html = True)

def render_aqi_scale_bar(aqi_value):
    """Renders a horizontal color-coded AQI scale bar with a marker at aqi_value."""
    aqi_clamped = max(0, min(aqi_value, AQI_SCALE_MAX))
    marker_pct = (aqi_clamped / AQI_SCALE_MAX) * 100

    gradient_stops = []
    for low, high, color, _ in AQI_SCALE:
        gradient_stops.append(f"{color} {low / AQI_SCALE_MAX * 100:.2f}%")
        gradient_stops.append(f"{color} {high / AQI_SCALE_MAX * 100:.2f}%")
    gradient_css = ", ".join(gradient_stops)

    ticks = [0, 50, 100, 200, 300, 400, 500]
    tick_spans = "".join(
        f'<span style="position:absolute; left:{t / AQI_SCALE_MAX * 100:.2f}%; '
        f'transform:translateX(-50%); font-size:11px; color:#6b7280;">{t}</span>'
        for t in ticks
    )

    bar_html = f"""
    <div style="margin: 4px 0 24px 0;">
      <div style="position: relative; height: 40px;">
        <div style="position: absolute; top: 0; left: calc({marker_pct:.2f}% - 16px);
                    font-size: 13px; font-weight: 600; color: #1f2937; white-space: nowrap;">{aqi_clamped}</div>
        <div style="position: relative; top: 20px; height: 14px; border-radius: 7px;
                    background: linear-gradient(90deg, {gradient_css});">
          <div style="position: absolute; top: -3px; left: {marker_pct:.2f}%; width: 3px; height: 20px;
                      background: #1f2937; transform: translateX(-50%); border-radius: 2px;"></div>
        </div>
        <div style="position: relative; top: 24px; height: 14px;">{tick_spans}</div>
      </div>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html = True)

st.set_page_config(page_title = "AQI Forecasting Dashboard", layout = "wide")

top_left, _ = st.columns([1, 3])
with top_left:
    selected_station = st.selectbox("Station", STATIONS, index = STATIONS.index("Kurla"))

if selected_station not in AVAILABLE_STATIONS:
    st.title("AQI Forecasting Dashboard")
    st.caption(f"{selected_station} Monitoring Station")
    st.markdown(EARTH_UNAVAILABLE_SVG, unsafe_allow_html = True)
    st.subheader("Station unavailable")
    st.info(f"Live monitoring for {selected_station} isn't set up yet. Switch back to Kurla to see live readings.")
    st.stop()

recent_data = get_recent_readings()
latest_reading = recent_data.iloc[-1]

live_timestamp, live_pm25 = fetch_pm25()

if live_pm25 is not None:
    today_aqi, today_category, today_caution = pm25_to_aqi(live_pm25)
    display_pm25 = live_pm25
    reading_time_note = live_timestamp
else:
    today_aqi, today_category, today_caution = pm25_to_aqi(latest_reading['pm25'])
    display_pm25 = latest_reading['pm25']
    reading_time_note = f"{latest_reading['date']} (from database, live fetch failed)"

header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.title("AQI Forecasting Dashboard")
    st.caption("Kurla Monitoring Station")
with header_col2:
    render_earth_corner(today_category, latest_reading['temperature_2m_max'])

last_date = recent_data['date'].iloc[-1]
st.caption(f"Last Updated: {last_date}")

sensitivity = st.radio("Sensitivity",
                       options = ["general", "sensitive"],
                       format_func = lambda x : "General Public" if x == "general" else "Sensitive Groups",
                       horizontal = True)

report = generate_full_report(sensitivity)

st.divider()

col1, col2, col3 = st.columns(3)
col4, col5, col6= st.columns(3)

with col1:
    st.metric("Current AQI", today_aqi)
with col2:
    st.metric("PM2.5", f"{display_pm25:.1f} µg/m³")
with col3:
    st.metric("Temperature", f"{latest_reading['temperature_2m_max']:.1f} °C")
with col4:
    st.metric("Humidity", f"{latest_reading['relative_humidity_2m_max']:.0f}%")
with col5:
    st.metric("Wind Speed", f"{latest_reading['wind_speed_10m_max']:.1f} km/h")
with col6:
    st.metric("Category", today_category)

render_aqi_scale_bar(today_aqi)

st.caption(f"Reading as of: {reading_time_note}")

st.divider()

st.subheader("Advisory")
today_advisory = get_advisory(today_category, sensitivity)
st.info(today_advisory)

if today_caution:
    st.warning(today_caution)

st.subheader("3-Day Forecast")
st.caption("LR | LSTM")
forecast_col1, forecast_col2, forecast_col3 = st.columns(3)

today = datetime.now().date()
forecast_labels = [
    (today + timedelta(days=1)).strftime("%a, %d %b"),
    (today + timedelta(days=2)).strftime("%a, %d %b"),
    (today + timedelta(days=3)).strftime("%a, %d %b"),
]

forecast_days = [
    (forecast_labels[0], "day1", forecast_col1),
    (forecast_labels[1], "day2", forecast_col2),
    (forecast_labels[2], "day3", forecast_col3),
]

for label, key, col in forecast_days:
    with col:
        lr_aqi = report[key]['aqi']
        lstm_aqi = report[key]['lstm_aqi']
        display_value = f"{lr_aqi} | {lstm_aqi}" if lstm_aqi is not None else f"{lr_aqi} | —"
        st.metric(label, display_value, help=report[key]['category'])
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

st.subheader("Predicted vs Actual (Last 14 Days)")
tracking_df = get_tracking_table()

if tracking_df.empty:
    st.info("No tracking data yet - check back after a few days of predictions.")
else:
    display_df = tracking_df[['target_date', 'predicted_aqi', 'actual_aqi']].copy()
    display_df.columns = ['Date', 'Predicted AQI', 'Actual AQI']
    st.dataframe(display_df, use_container_width=True)

st.divider()

st.subheader("System Status")
status_col1, status_col2, status_col3, status_col4 = st.columns(4)

with status_col1:
    if live_pm25 is not None:
        st.success("✓ API Connected")
    else:
        st.error("✗ API Unavailable")

with status_col2:
    try:
        _ = get_recent_readings()
        st.success("✓ SQLite Connected")
    except Exception:
        st.error("✗ SQLite Error")

with status_col3:
    st.success("✓ Model Loaded")

with status_col4:
    last_update_date = recent_data['date'].iloc[-1]
    today_date = datetime.now().date()
    if pd.to_datetime(last_update_date).date() == today_date:
        st.success("✓ Scheduler Current")
    else:
        st.warning(f"⚠ Last run: {last_update_date}")