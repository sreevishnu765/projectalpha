import pandas as pd

def data_prep():

    # dataframe declaration
    pol_df = pd.read_csv("POLSET.csv", skipinitialspace = True)
    wea_df = pd.read_csv("WEASET.csv")
    pol_df.columns = pol_df.columns.str.strip()
    wea_df.columns = wea_df.columns.str.strip()

    # datetime standardization
    pol_df["date"] = pd.to_datetime(pol_df["date"], format = "%Y/%m/%d")
    wea_df["time"] = pd.to_datetime(wea_df["time"], format = "%Y-%m-%d")
    wea_df.rename(columns = {"time":"date"}, inplace = True)
    merged_df = pd.merge(pol_df, wea_df, on = "date", how = "inner")

    # reindexing
    full_range = pd.date_range(start=merged_df['date'].min(), end=merged_df['date'].max(), freq='D')
    merged_df = merged_df.set_index('date')
    merged_df = merged_df.reindex(full_range)
    merged_df.index.name = 'date'
    merged_df = merged_df.reset_index()

    # outlier data interpolation
    outlier_dates = ['2022-01-23', '2022-03-27', '2023-04-28', '2024-02-24', '2024-07-05', '2024-10-02']
    merged_df.loc[merged_df['date'].isin(outlier_dates), 'pm25'] = None
    merged_df['pm25'] = merged_df['pm25'].interpolate(method='linear')

    # missing data interpolation
    pol_cols = ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co']
    wea_cols = ['temperature_2m_max (°C)', 'temperature_2m_min (°C)', 'wind_speed_10m_max (km/h)', 'relative_humidity_2m_max (%)']
    merged_df[pol_cols + wea_cols] = merged_df[pol_cols + wea_cols].interpolate(method='linear')
    merged_df['pm25'] = merged_df['pm25'].bfill().ffill()

    # lag data
    merged_df['pm25_lag1'] = merged_df['pm25'].shift(1)
    merged_df['pm25_lag2'] = merged_df['pm25'].shift(2)
    merged_df['pm25_lag3'] = merged_df['pm25'].shift(3)
    merged_df['pm25_lag7'] = merged_df['pm25'].shift(7)
    merged_df['pm25_roll7'] = merged_df['pm25'].rolling(window = 7).mean().shift(1)
    merged_df['tmax_lag1'] = merged_df['temperature_2m_max (°C)'].shift(1)
    merged_df['tmin_lag1'] = merged_df['temperature_2m_min (°C)'].shift(1)
    merged_df['wind_lag1'] = merged_df['wind_speed_10m_max (km/h)'].shift(1)
    merged_df['hum_lag1'] = merged_df['relative_humidity_2m_max (%)'].shift(1)
    merged_df['pm10_lag1'] = merged_df['pm10'].shift(1)
    merged_df['o3_lag1'] = merged_df['o3'].shift(1)
    merged_df['no2_lag1'] = merged_df['no2'].shift(1)
    merged_df['so2_lag1'] = merged_df['so2'].shift(1)
    merged_df['co_lag1'] = merged_df['co'].shift(1)

    # target data
    merged_df['pm25_tgt1'] = merged_df['pm25'].shift(-1)
    merged_df['pm25_tgt2'] = merged_df['pm25'].shift(-2)
    merged_df['pm25_tgt3'] = merged_df['pm25'].shift(-3)

    # clear NaN values
    model_df = merged_df.dropna(subset=['pm25_lag1', 'pm25_lag2', 'pm25_lag3', 'pm25_lag7', 'pm25_roll7', 'tmax_lag1', 'tmin_lag1', 'wind_lag1', 'hum_lag1', 'pm10_lag1', 'o3_lag1', 'no2_lag1', 'so2_lag1', 'co_lag1', 'pm25_tgt1', 'pm25_tgt2', 'pm25_tgt3'])
    
    # export
    split_index = int(len(model_df) * 0.85)
    train_df = model_df.iloc[:split_index]
    val_df = model_df.iloc[split_index:]
    train_df.to_csv("train_df.csv", index=False)
    val_df.to_csv("val_df.csv", index=False)
    return train_df, val_df