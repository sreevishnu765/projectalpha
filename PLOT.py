import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# dataframe declaration
pol_df = pd.read_csv("POLSET.csv", skipinitialspace = True)
wea_df = pd.read_csv("WEASET.csv", skipinitialspace = True)
pol_df.columns = pol_df.columns.str.strip()
wea_df.columns = wea_df.columns.str.strip()

# datetime standardization
pol_df["date"] = pd.to_datetime(pol_df["date"], format = "%Y/%m/%d")
wea_df["time"] = pd.to_datetime(wea_df["time"], format = "%Y-%m-%d")
wea_df.rename(columns = {"time":"date"}, inplace = True)
merged_df = pd.merge(pol_df, wea_df, on = "date", how = "inner")

# outlier data interpolation
outlier_dates = ['2022-01-23', '2022-03-27', '2023-04-28', '2024-02-24', '2024-07-05', '2024-10-02']
merged_df.loc[merged_df['date'].isin(outlier_dates), 'pm25'] = None
merged_df['pm25'] = merged_df['pm25'].interpolate(method='linear')

# missing data interpolation
pol_cols = ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co']
merged_df[pol_cols] = merged_df[pol_cols].interpolate(method='linear')

# tidying graph
plt.plot(merged_df["date"], merged_df["pm25"])
plt.xlabel("Date")
plt.ylabel("PM2.5")
plt.xticks(rotation=45)
plt.gca().xaxis.set_major_locator(mdates.YearLocator())
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

# generate graph
plt.grid(True)
plt.show()