import requests
import pandas as pd
import os
from datetime import datetime

# File path
file_path = r'/c/Users/elamuruganm/Documents/Projects/BT/NiftyData/nifty_futures_1min_2016_2023.csv'
upload_url = 'https://postgresql-production-ac4f.up.railway.app/api/data/upload'

print("Reading CSV file...")
df = pd.read_csv(file_path)
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)}")

# Map columns
df['date'] = pd.to_datetime(df['DateTime']).dt.date
df['time'] = pd.to_datetime(df['DateTime']).dt.time

# Use 2020-2022 data for manageable size
df_sample = df[(pd.to_datetime(df['DateTime']) >= '2020-01-01') & (pd.to_datetime(df['DateTime']) < '2023-01-01')].copy()
print(f"Rows to upload (2020-2022): {len(df_sample)}")

# Prepare output with correct column names
df_export = df_sample[['date', 'time', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
df_export.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']

# Save to temp file
temp_file = r'C:\Users\elamuruganm\Documents\Projects\Strategy\ORB_Strategy\nifty_fut_2020_2022.csv'
df_export.to_csv(temp_file, index=False)

print(f"Prepared file: {temp_file}")
print(f"File size: {os.path.getsize(temp_file) / (1024*1024):.1f} MB")

# Upload
files = {'file': open(temp_file, 'rb')}
data = {'symbol': 'NIFTY_FUT'}

print("\nUploading to Railway...")
response = requests.post(upload_url, files=files, data=data, timeout=180)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Result: {result}")

if result.get('status') == 'success':
    print(f"✅ Success: {result['message']}")
    if 'uploaded' in result:
        print(f"   Records uploaded: {result['uploaded']}")
else:
    print(f"❌ Error: {result.get('error')}")
