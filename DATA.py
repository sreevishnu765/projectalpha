import pandas as pd

def data_prep():

    # dataframe declaration
    pol_df = pd.read_csv("POLSET.csv", skipinitialspace = True)
    wea_df = pd.read_csv("WEASET.csv", skiprows = 0)
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
    outlier_dates = [
        '2020-01-10', '2020-01-11', '2020-01-12', '2020-01-14', '2020-01-28', '2020-01-30',
        '2020-02-15', '2020-02-19', '2020-02-20', '2020-03-08', '2020-03-09', '2020-03-11',
        '2020-03-18', '2020-04-02', '2020-04-03', '2020-05-05', '2020-07-20', '2020-07-21',
        '2020-07-22', '2020-08-12', '2020-08-13', '2020-08-14', '2020-09-07', '2020-09-13',
        '2020-10-15', '2020-10-22', '2020-10-25', '2020-11-10', '2020-11-11', '2020-11-12',
        '2020-11-18', '2020-11-19', '2020-11-28', '2020-11-29', '2020-12-22', '2020-12-28',
        '2021-01-10', '2021-01-11', '2021-01-15', '2021-02-08', '2021-02-14', '2021-02-15',
        '2021-02-16', '2021-02-18', '2021-03-30', '2021-04-29', '2021-04-30', '2021-05-11',
        '2021-06-14', '2021-06-15', '2021-07-19', '2021-07-20', '2021-07-28', '2021-08-04',
        '2021-09-17', '2021-09-18', '2021-09-21', '2021-09-22', '2021-09-28', '2021-09-29',
        '2021-10-09', '2021-10-12', '2021-10-13', '2021-11-20', '2021-11-21', '2021-11-24',
        '2021-12-11', '2021-12-12', '2022-01-09', '2022-01-23', '2022-01-24', '2022-02-01',
        '2022-02-27', '2022-03-04', '2022-03-25', '2022-03-27', '2022-03-28', '2022-03-29',
        '2022-04-01', '2022-04-16', '2022-04-17', '2022-04-21', '2022-04-26', '2022-04-27',
        '2022-08-09', '2022-08-10', '2022-08-12', '2022-11-08', '2022-12-24', '2023-02-06',
        '2023-04-28', '2023-04-29', '2023-05-02', '2023-05-11', '2023-05-12', '2023-05-26',
        '2023-05-27', '2023-06-10', '2023-10-10', '2023-11-06', '2023-11-29', '2023-11-30',
        '2023-12-05', '2023-12-22', '2023-12-23', '2024-02-24', '2024-02-25', '2024-02-29',
        '2024-04-05', '2024-04-29', '2024-05-29', '2024-06-10', '2024-06-12', '2024-06-16',
        '2024-06-17', '2024-07-06', '2024-07-08', '2024-10-02', '2024-10-03', '2024-10-04',
        '2025-02-07', '2025-04-16', '2025-05-17', '2025-08-21', '2026-02-20', '2026-03-05',
        '2026-03-12', '2026-03-13', '2026-04-19', '2026-04-20', '2026-04-24', '2026-05-02',
        '2026-05-18', '2026-05-19',
        '2020-04-04', '2020-04-05', '2020-04-06', '2020-04-07', '2020-04-08', '2020-04-09',
        '2020-04-10', '2020-04-11', '2020-04-12', '2020-04-13', '2020-04-14', '2020-04-15',
        '2020-04-16', '2020-04-17', '2020-04-18', '2020-04-19', '2020-04-20', '2020-04-21',
        '2020-04-22', '2020-04-23', '2020-04-24', '2020-04-25', '2020-04-26', '2020-04-27',
        '2020-04-28', '2021-05-01', '2021-05-02', '2021-05-03', '2021-05-04',
    ]
    
    for d in outlier_dates:
        merged_df.loc[merged_df['date'] == pd.to_datetime(d), 'pm25'] = None
    merged_df['pm25'] = merged_df['pm25'].interpolate(method='linear')

    # missing data interpolation
    pol_cols = ['pm25']
    wea_cols = ['temperature_2m_max (°C)', 'temperature_2m_min (°C)', 'wind_speed_10m_max (km/h)', 'relative_humidity_2m_max (%)', 'precipitation_sum (mm)']
    merged_df[pol_cols + wea_cols] = merged_df[pol_cols + wea_cols].interpolate(method='linear')
    merged_df['pm25'] = merged_df['pm25'].bfill().ffill()

    # lag data
    merged_df['pm25_lag1'] = merged_df['pm25'].shift(1)
    merged_df['pm25_lag2'] = merged_df['pm25'].shift(2)
    merged_df['pm25_lag3'] = merged_df['pm25'].shift(3)
    merged_df['pm25_lag7'] = merged_df['pm25'].shift(7)
    merged_df['pm25_roll3'] = merged_df['pm25'].rolling(window = 3).mean().shift(1)
    merged_df['tmax_lag1'] = merged_df['temperature_2m_max (°C)'].shift(1)
    merged_df['tmin_lag1'] = merged_df['temperature_2m_min (°C)'].shift(1)
    merged_df['wind_lag1'] = merged_df['wind_speed_10m_max (km/h)'].shift(1)
    merged_df['hum_lag1'] = merged_df['relative_humidity_2m_max (%)'].shift(1)

    # forecasted precip flag
    PRECIP_THRESHOLD = 2.5
    merged_df['precip_flag_tgt1'] = (merged_df['precipitation_sum (mm)'].shift(-1) > PRECIP_THRESHOLD).astype(float)
    merged_df['precip_flag_tgt2'] = (merged_df['precipitation_sum (mm)'].shift(-2) > PRECIP_THRESHOLD).astype(float)
    merged_df['precip_flag_tgt3'] = (merged_df['precipitation_sum (mm)'].shift(-3) > PRECIP_THRESHOLD).astype(float)

    # target data
    merged_df['pm25_tgt1'] = merged_df['pm25'].shift(-1)
    merged_df['pm25_tgt2'] = merged_df['pm25'].shift(-2)
    merged_df['pm25_tgt3'] = merged_df['pm25'].shift(-3)

    # clear NaN values
    lag_cols = ['pm25_lag1', 'pm25_lag2', 'pm25_lag3', 'pm25_lag7', 'pm25_roll3', 'tmax_lag1', 'tmin_lag1', 'wind_lag1', 'hum_lag1']
    flag_cols = ['precip_flag_tgt1', 'precip_flag_tgt2', 'precip_flag_tgt3']
    tgt_cols = ['pm25_tgt1', 'pm25_tgt2', 'pm25_tgt3']

    model_df = merged_df.dropna(subset = lag_cols + flag_cols + tgt_cols)

    # export
    split_index = int(len(model_df) * 0.85)
    TRNSET = model_df.iloc[:split_index]
    VALSET = model_df.iloc[split_index:]
    TRNSET.to_csv("TRNSET.csv", index=False)
    VALSET.to_csv("VALSET.csv", index=False)
    return TRNSET, VALSET

if __name__ == "__main__":
    data_prep()
