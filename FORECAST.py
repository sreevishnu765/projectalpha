import joblib
import pandas as pd
from DATABASE import get_recent_readings
from CONVERT import pm25_to_aqi, get_advisory
from CALL import get_precip_flags
from CHECK_STATIONS import STATIONS


BASE_FEATURE_COLS = ['pm25_lag1', 'pm25_lag2', 'pm25_lag3', 'pm25_lag7', 'pm25_roll3',
                     'tmax_lag1', 'tmin_lag1', 'wind_lag1', 'hum_lag1']
SERIES_COLS = ['pm25', 'temperature_2m_max', 'temperature_2m_min', 'wind_speed_10m_max', 'relative_humidity_2m_max']

MAX_DATA_AGE_DAYS = 2
RECENT_REAL_DAYS_REQUIRED = 4

# lag feature preparation
def prepare_live_features(station="Kurla"):
    df = get_recent_readings(station)
    if df.empty:
        return None
    df = df.sort_values('date').reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'])

    age_days = (pd.Timestamp.now().normalize() - df['date'].iloc[-1]).days
    if age_days > MAX_DATA_AGE_DAYS:
        print(f"prepare_live_features: newest {station} reading is {age_days} days old - not forecasting")
        return None

    last_day = df['date'].iloc[-1]
    required = pd.date_range(end=last_day, periods=RECENT_REAL_DAYS_REQUIRED, freq='D')
    have = set(df['date'])
    if any(d not in have for d in required):
        print(f"prepare_live_features: fewer than {RECENT_REAL_DAYS_REQUIRED} consecutive recent days of {station} data - not forecasting yet")
        return None

    full_range = pd.date_range(df['date'].iloc[0], df['date'].iloc[-1], freq='D')
    df = df.set_index('date').reindex(full_range)
    df.index.name = 'date'
    df[SERIES_COLS] = df[SERIES_COLS].interpolate(method='linear')
    df = df.reset_index()
    n_rows = len(df)

    df['pm25_lag1'] = df['pm25'].shift(1)
    df['pm25_lag2'] = df['pm25'].shift(2) if n_rows >= 3 else df['pm25_lag1']
    df['pm25_lag3'] = df['pm25'].shift(3) if n_rows >= 4 else df['pm25_lag1']
    df['pm25_lag7'] = df['pm25'].shift(7) if n_rows >= 8 else df['pm25_lag1']
    df['pm25_roll3'] = df['pm25'].rolling(window=min(3, n_rows), min_periods=1).mean().shift(1)

    df['tmax_lag1'] = df['temperature_2m_max'].shift(1)
    df['tmin_lag1'] = df['temperature_2m_min'].shift(1)
    df['wind_lag1'] = df['wind_speed_10m_max'].shift(1)
    df['hum_lag1'] = df['relative_humidity_2m_max'].shift(1)

    latest_row = df.iloc[[-1]].copy()
    latest_row = latest_row.ffill()

    if latest_row[BASE_FEATURE_COLS].isna().any().any():
        return None

    return latest_row

# MK6 forecast generation
def generate_mk6_forecast(station="Kurla"):
    latest = prepare_live_features(station)
    if latest is None:
        return None, None, None

    coords = STATIONS[station]
    try:
        precip_flags = get_precip_flags(days=3, lat=coords["lat"], lon=coords["lon"])
    except Exception:
        precip_flags = {"precip_flag_tgt1": 0.0, "precip_flag_tgt2": 0.0, "precip_flag_tgt3": 0.0}

    preds = []
    for h in [1, 2, 3]:
        model = joblib.load(f"model_mk6_day{h}.pkl")
        X_live = latest[BASE_FEATURE_COLS].copy()
        X_live[f'precip_flag_tgt{h}'] = precip_flags[f'precip_flag_tgt{h}']
        pred = model.predict(X_live)[0]
        preds.append(float(pred))

    return preds[0], preds[1], preds[2]

UNAVAILABLE_ADVISORY = "Forecast unavailable - there aren't enough recent readings from this station."

def generate_full_report(sensitivity_tier="general", station="Kurla"):
    preds = generate_mk6_forecast(station)

    report = {}
    for day, pred in zip(["day1", "day2", "day3"], preds):
        if pred is None:
            report[day] = {
                "predicted_pm25": None, "aqi": None, "category": "Unavailable",
                "caution": None, "advisory": UNAVAILABLE_ADVISORY,
            }
            continue

        pred = max(pred, 0.0)
        aqi, category, caution = pm25_to_aqi(pred)
        report[day] = {
            "predicted_pm25": round(pred, 1),
            "aqi": aqi,
            "category": category,
            "caution": caution,
            "advisory": get_advisory(category, sensitivity_tier),
        }
    return report

if __name__ == "__main__":
    print(generate_mk6_forecast())
    print(generate_full_report("sensitive"))
