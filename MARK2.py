import pandas as pd
from PANDA import data_prep
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
import tensorflow as tf

train_df, val_df = data_prep()
raw_feature_cols = ['pm25', 'temperature_2m_max (°C)', 'temperature_2m_min (°C)', 'wind_speed_10m_max (km/h)', 'relative_humidity_2m_max (%)']

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

X_train, y1_train, y2_train, y3_train = create_windows(train_df, raw_feature_cols, window_size=14)
X_val, y1_val, y2_val, y3_val = create_windows(val_df, raw_feature_cols, window_size=14)

print(X_train.shape)
print(y1_train.shape, y2_train.shape, y3_train.shape)