import joblib
import pandas as pd
from DATABASE import get_recent_readings
from CONVERT import pm25_to_aqi, get_advisory

LSTM_FEATURE_COLS = ['pm25', 'temperature_2m_max', 'temperature_2m_min', 'wind_speed_10m_max', 'relative_humidity_2m_max']
LSTM_WINDOW = 14

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

def prepare_live_lstm_window():
    """Builds the last-14-day raw feature window for live LSTM prediction.
    Returns None if there isn't enough history yet (e.g. fresh DB)."""
    df = get_recent_readings()
    df = df.sort_values('date').reset_index(drop=True)

    if len(df) < LSTM_WINDOW:
        return None

    window_df = df.tail(LSTM_WINDOW)
    window = window_df[LSTM_FEATURE_COLS].values

    scaler = joblib.load("lstm_scaler.pkl")
    n_timesteps, n_features = window.shape
    window_scaled = scaler.transform(window).reshape(1, n_timesteps, n_features)
    return window_scaled

def generate_lstm_forecast():
    """Returns (pred_day1, pred_day2, pred_day3) as PM2.5 values, or (None, None, None)
    if there isn't enough recent history to build a 14-day window yet."""
    from tensorflow.keras.models import load_model # type: ignore

    X_live = prepare_live_lstm_window()
    if X_live is None:
        return None, None, None

    model_day1 = load_model("model_lstm_day1.keras")
    model_day2 = load_model("model_lstm_day2.keras")
    model_day3 = load_model("model_lstm_day3.keras")

    pred_day1 = float(model_day1.predict(X_live, verbose=0)[0][0])
    pred_day2 = float(model_day2.predict(X_live, verbose=0)[0][0])
    pred_day3 = float(model_day3.predict(X_live, verbose=0)[0][0])

    return pred_day1, pred_day2, pred_day3

def generate_full_report(sensitivity_tier="general"):
    pred_day1, pred_day2, pred_day3 = generate_forecast()
    lstm_day1, lstm_day2, lstm_day3 = generate_lstm_forecast()

    lr_preds = [pred_day1, pred_day2, pred_day3]
    lstm_preds = [lstm_day1, lstm_day2, lstm_day3]

    report = {}
    for day, lr_pred, lstm_pred in zip(["day1", "day2", "day3"], lr_preds, lstm_preds):
        # Category/advisory stay driven by the LR prediction, since LR remains
        # the production model. LSTM is shown alongside for comparison only.
        aqi, category, caution = pm25_to_aqi(lr_pred)
        advisory = get_advisory(category, sensitivity_tier)

        lstm_aqi = pm25_to_aqi(lstm_pred)[0] if lstm_pred is not None else None

        report[day] = {
            "predicted_pm25": round(lr_pred, 1),
            "aqi": aqi,
            "lstm_aqi": lstm_aqi,
            "category": category,
            "caution": caution,
            "advisory": advisory
        }
    return report

if __name__ == "__main__":
    print(generate_forecast())
    print(generate_lstm_forecast())
    print(generate_full_report("sensitive"))