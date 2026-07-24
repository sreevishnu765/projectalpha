import pandas as pd
from DATA import data_prep
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential                                                                              # type: ignore
from tensorflow.keras.layers import LSTM, Dense                                                                             # type: ignore
from tensorflow.keras.callbacks import EarlyStopping                                                                        # type: ignore

# data preparation
TRNSET, VALSET = data_prep()
raw_feature_cols = ['pm25', 'temperature_2m_max (°C)', 'temperature_2m_min (°C)', 'wind_speed_10m_max (km/h)', 'relative_humidity_2m_max (%)']

# window function
def create_windows(df, feature_cols, window_size = 14):
    data = df[feature_cols].values
    pm25_values = df['pm25'].values

    X, Y1, Y2, Y3 = [], [], [], []

    for i in range(len(data) - window_size - 3):
        window = data[i : i + window_size]
        target1 = pm25_values[i + window_size]
        target2 = pm25_values[i + window_size + 1]
        target3 = pm25_values[i + window_size + 2]

        X.append(window)
        Y1.append(target1)
        Y2.append(target2)
        Y3.append(target3)

    return np.array(X), np.array(Y1), np.array(Y2), np.array(Y3)

# function call
X_train, y1_train, y2_train, y3_train = create_windows(TRNSET, raw_feature_cols, window_size=14)
X_val, y1_val, y2_val, y3_val = create_windows(VALSET, raw_feature_cols, window_size=14)

# scaler
scaler = MinMaxScaler()
n_samples_train, n_timesteps, n_features = X_train.shape
X_train_reshaped = X_train.reshape(-1, n_features)
scaler.fit(X_train_reshaped)
X_train_scaled = scaler.transform(X_train_reshaped).reshape(n_samples_train, n_timesteps, n_features)
n_samples_val = X_val.shape[0]
X_val_reshaped = X_val.reshape(-1, n_features)
X_val_scaled = scaler.transform(X_val_reshaped).reshape(n_samples_val, n_timesteps, n_features)

# model function
def build_and_train_lstm(X_train, y_train, X_val, y_val, horizon_name):
    model = Sequential([LSTM(32, input_shape=(14, 5)), Dense(1)])
    model.compile(optimizer='adam', loss='mse')

    early_stop = EarlyStopping(monitor='val_loss', patience=20, restore_best_weights=True)
    model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=300, batch_size=32, callbacks=[early_stop], verbose=0)

    predictions = model.predict(X_val).flatten()
    rmse = np.sqrt(mean_squared_error(y_val, predictions))
    mae = mean_absolute_error(y_val, predictions)
    mape = np.mean(np.abs((y_val - predictions) / y_val)) * 100

    print(f"LSTM {horizon_name} - RMSE: {rmse:.2f}   MAE: {mae:.2f}   MAPE: {mape:.2f}%")
    return model, rmse, mae, mape

# function call
model_lstm_day1, rmse1, mae1, mape1 = build_and_train_lstm(X_train_scaled, y1_train, X_val_scaled, y1_val, "Day+1")
model_lstm_day2, rmse2, mae2, mape2 = build_and_train_lstm(X_train_scaled, y2_train, X_val_scaled, y2_val, "Day+2")
model_lstm_day3, rmse3, mae3, mape3 = build_and_train_lstm(X_train_scaled, y3_train, X_val_scaled, y3_val, "Day+3")