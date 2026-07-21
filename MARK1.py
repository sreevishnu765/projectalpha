import pandas as pd
from PANDA import data_prep
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

# data preparation
TRNSET, VALSET = data_prep()
feature_cols_extended = ['pm25_lag1', 'pm25_lag2', 'pm25_lag3', 'pm25_lag7', 'pm25_roll7', 'tmax_lag1', 'tmin_lag1', 'wind_lag1', 'hum_lag1']
target_col = ['pm25_tgt1', 'pm25_tgt2', 'pm25_tgt3']

# model function
def train_and_eval(TRNSET, VALSET, feature_cols_extended, target_col):
    X_Train = TRNSET[feature_cols_extended]
    Y_Train = TRNSET[target_col]
    X_Val = VALSET[feature_cols_extended]
    Y_Val = VALSET[target_col]

    model = LinearRegression()
    model.fit(X_Train, Y_Train)
    predictions = model.predict(X_Val)

    rmse = np.sqrt(mean_squared_error(Y_Val, predictions))
    mae = mean_absolute_error(Y_Val, predictions)
    mape = np.mean(np.abs((Y_Val - predictions) / Y_Val)) * 100

    print(f"Target: {target_col}")
    print(f"RMSE: {rmse:.2f}    MAE: {mae:.2f}  MAPE: {mape:.2f}%")

    return model, rmse, mae, mape

# function call
model_day1, rmse1, mae1, mape1 = train_and_eval(TRNSET, VALSET, feature_cols_extended, 'pm25_tgt1')
model_day2, rmse2, mae2, mape2 = train_and_eval(TRNSET, VALSET, feature_cols_extended, 'pm25_tgt2')
model_day3, rmse3, mae3, mape3 = train_and_eval(TRNSET, VALSET, feature_cols_extended, 'pm25_tgt3')