import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import warnings
warnings.filterwarnings("ignore")

# Setup folders
download_folder = "raw_data"
processed_folder = "processed"
os.makedirs(download_folder, exist_ok=True)
os.makedirs(processed_folder, exist_ok=True)

# --- Step 1: Download NUPRC Production Files ---
headers = {
    "User-Agent": "Mozilla/5.0"
}
url = "https://www.nuprc.gov.ng/oil-production-status-report/"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")
    links = soup.find_all("a", href=True)
    downloads = [link['href'] for link in links if any(ext in link['href'] for ext in ['.csv', '.xlsx', '.xls']) and 'production' in link['href'].lower()]
    
    for link in downloads:
        filename = link.split("/")[-1]
        full_url = link if link.startswith("http") else "https://www.nuprc.gov.ng" + link
        try:
            res = requests.get(full_url, headers=headers)
            with open(os.path.join(download_folder, filename), "wb") as f:
                f.write(res.content)
            print(f"✅ Downloaded: {filename}")
        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")
else:
    print(f"❌ Failed to access page. Status code: {response.status_code}")
    exit()

# --- Step 2: Clean and Combine ---
month_order = ['January','February','March','April','May','June','July','August','September','October','November','December']
all_data = []

# Loop through files
for file in os.listdir(download_folder):
    if file.endswith(('.csv', '.xlsx', '.xls')):
        file_path = os.path.join(download_folder, file)
        try:
            df_raw = pd.read_excel(file_path, header=None)

            # Detect header row
            header_row_idx = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains("TERMINAL/STREAM", case=False)).any(axis=1)].index[0]
            header = df_raw.iloc[header_row_idx].tolist()

            # Detect year
            year_row = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains("CRUDE OIL AND CONDENSATE PRODUCTION", case=False)).any(axis=1)]
            year_text = year_row.iloc[0].astype(str).str.cat(sep=' ')
            year_match = re.search(r'\b(20\d{2})\b', year_text)
            default_year = int(year_match.group(1)) if year_match else None

            # Assign header
            df_data = df_raw.iloc[header_row_idx + 1:].copy()
            df_data.columns = header

            # Identify columns
            id_cols = [col for col in df_data.columns if "stream" in str(col).lower() or "liquid" in str(col).lower()]
            value_cols = [col for col in df_data.columns if col not in id_cols and str(col).strip().lower() != 'total']

            # Melt
            df_melted = df_data.melt(id_vars=id_cols, value_vars=value_cols, var_name='Date', value_name='Production')

            # Parse month
            def extract_month(val):
                try:
                    dt = parser.parse(str(val), fuzzy=True)
                    return dt.strftime('%B')
                except:
                    return str(val).strip().capitalize()

            df_melted['Month'] = df_melted['Date'].apply(extract_month)
            df_melted['Year'] = default_year

            # Tidy DataFrame
            df_final = df_melted.rename(columns={id_cols[0]: 'Stream', id_cols[1]: 'Liquid Type'})
            df_final = df_final[['Year', 'Month', 'Stream', 'Liquid Type', 'Production']].dropna(subset=['Production'])

            df_final = df_final[~df_final['Liquid Type'].str.contains("total", case=False, na=False)]

            df_final['Production'] = pd.to_numeric(df_final['Production'], errors='coerce').round(0).astype('Int64')
            df_final['Stream'] = df_final['Stream'].ffill()
            df_final['Stream'] = df_final['Stream'].str.replace(r'\s*\(.*?\)', '', regex=True)

            df_final = df_final.sort_values(by='Production', ascending=False)
            df_final = df_final.drop_duplicates(subset=['Year', 'Month', 'Stream', 'Liquid Type'], keep='first')

            df_final['Month'] = pd.Categorical(df_final['Month'], categories=month_order, ordered=True)
            df_final = df_final.sort_values(by=['Year', 'Month', 'Stream']).reset_index(drop=True)

            df_final = df_final[~df_final['Stream'].str.contains("liquid", case=False, na=False)]
            df_final = df_final.applymap(lambda x: x.strip() if isinstance(x, str) and not x.replace('.', '', 1).isdigit() else x)

            # Append cleaned data
            all_data.append(df_final)

        except Exception as e:
            print(f"❌ Error processing {file}: {e}")

# Combine all cleaned DataFrames
df_combined = pd.concat(all_data, ignore_index=True)
df_combined.dropna(inplace= True)

# --- Step 3: Data Validation ---

# 1. Check for missing values in key columns
required_columns = ['Year', 'Month', 'Stream', 'Liquid Type', 'Production']
missing_values = df_combined[required_columns].isnull().sum()
if missing_values.any():
    print("⚠️ Warning: Missing values detected in key columns:")
    print(missing_values[missing_values > 0])
else:
    print("✅ No missing values in required columns.")

# 2. Ensure production values are non-negative
if (df_combined['Production'] < 0).any():
    print("❌ Error: Negative production values found.")
    df_combined = df_combined[df_combined['Production'] >= 0]
else:
    print("✅ All production values are non-negative.")

# 3. Validate 'Month' against expected values
valid_months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]
invalid_months = df_combined[~df_combined['Month'].isin(valid_months)]
if not invalid_months.empty:
    print("⚠️ Warning: Invalid month entries detected.")
    print(invalid_months[['Month']].drop_duplicates())
    df_combined = df_combined[df_combined['Month'].isin(valid_months)]
else:
    print("✅ All months are valid.")

# 4. Check for duplicate records
dupes = df_combined.duplicated(subset=['Year', 'Month', 'Stream', 'Liquid Type'], keep=False)
if dupes.any():
    print(f"⚠️ Found {dupes.sum()} duplicate rows. Keeping first occurrence.")
    df_combined = df_combined[~dupes | ~df_combined.duplicated(subset=['Year', 'Month', 'Stream', 'Liquid Type'], keep='first')]
else:
    print("✅ No duplicate records found.")


# Save as CSV locally
final_csv_path = os.path.join(processed_folder, "final_combined.csv")
df_combined.to_csv(final_csv_path, index=False)
print(f"✅ All files cleaned and saved to {final_csv_path}")

# --- Step 3: Upload to Google Drive as CSV ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
file_id = "1nJPxcCVl8svjaxMfWxrdUsvkAJwONMa2" 

# Authenticate
creds = None
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

# # Upload the file
service = build('drive', 'v3', credentials=creds)
from googleapiclient.http import MediaFileUpload

# 👇️ Path to the final cleaned CSV
processed_file_path = os.path.join(processed_folder, "final_combined.csv")

# 👇️ File ID of your Google Drive file to overwrite
file_id = "1YAF-deOgnUB4M3-j6AUMmZNdqF56O7TP"

# 👇️ Prepare the upload as CSV
media = MediaFileUpload(processed_file_path, mimetype='text/csv', resumable=True)

# 👇️ Update/overwrite the file on Google Drive
updated_file = service.files().update(
    fileId=file_id,
    media_body=media
).execute()

print(f"✅ File overwritten on Google Drive: {updated_file.get('name')}")

# file_metadata = {
#     'name': 'combined_cleaned_nuprc_production.csv',
#     'mimeType': 'text/csv'
# }
# media = MediaFileUpload(processed_file_path, mimetype='text/csv', resumable=True)

# uploaded_file = service.files().create(
#     body=file_metadata,
#     media_body=media,
#     fields='id, name'
# ).execute()

# print(f"✅ File created: {uploaded_file.get('name')} with ID: {uploaded_file.get('id')}")







# # media = MediaFileUpload(final_csv_path, mimetype='text/csv', resumable=True)

# # updated_file = service.files().update(
# #     fileId=file_id,
# #     media_body=media
# # ).execute()

# # print(f"📤 Final CSV uploaded and overwritten on Google Drive: {updated_file.get('name')}")
# # Upload and overwrite existing CSV file on Google Drive
# media = MediaFileUpload(final_csv_path, mimetype='text/csv', resumable=True)

# updated_file = service.files().update(
#     fileId=file_id,
#     media_body=media,
#     fields='id, name, mimeType'
# ).execute()

# print(f"📤 File updated: {updated_file['name']} (MIME type: {updated_file['mimeType']})")
