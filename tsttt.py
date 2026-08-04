import sqlite3
import pandas as pd

conn = sqlite3.connect("alpha_data.db")   # replace with your database filename

df = pd.read_sql_query("SELECT * FROM daily_readings;", conn)   # replace daily_data with your table name

print(df)

conn.close()