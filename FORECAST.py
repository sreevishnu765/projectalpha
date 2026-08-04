import joblib
import pandas as pd
from DATABASE import get_recent_readings
from CONVERT import pm25_to_aqi, get_advisory

def prepare_live_features():
    df = get_recent_readings()
    df = df.sort_values('date').reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'])
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
    
    return latest_row

def generate_forecast():
    feature_cols = ['pm25_lag1', 'pm25_lag2', 'pm25_lag3', 'pm25_lag7', 'pm25_roll3', 'tmax_lag1', 'tmin_lag1', 'wind_lag1', 'hum_lag1']

    latest = prepare_live_features()
    X_live = latest[feature_cols]

    model_day1 = joblib.load("model_day1.pkl")
    model_day2 = joblib.load("model_day2.pkl")
    model_day3 = joblib.load("model_day3.pkl")

    pred_day1 = model_day1.predict(X_live)[0]
    pred_day2 = model_day2.predict(X_live)[0]
    pred_day3 = model_day3.predict(X_live)[0]

    return pred_day1, pred_day2, pred_day3

def generate_full_report(sensitivity_tier="general"):
    pred_day1, pred_day2, pred_day3 = generate_forecast()
    
    report = {}
    for day, pred in zip(["day1", "day2", "day3"], [pred_day1, pred_day2, pred_day3]):
        aqi, category, caution = pm25_to_aqi(pred)
        advisory = get_advisory(category, sensitivity_tier)
        report[day] = {
            "predicted_pm25": round(pred, 1),
            "aqi": aqi,
            "category": category,
            "caution": caution,
            "advisory": advisory
        }
    return report

if __name__ == "__main__":
    print(generate_forecast())
    print(generate_full_report("sensitive"))