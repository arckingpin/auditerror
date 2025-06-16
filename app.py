import streamlit as st
import pandas as pd
from datetime import datetime
import io
import traceback
import json
import tempfile

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread
from PIL import Image  # ✅ For image compression

# ✅ Must be the first Streamlit command
st.set_page_config(page_title="Auditor Error Logger", layout="centered")

# --- CONFIGURATION ---
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

FOLDER_ID = '17-Ar-v76PqqtSGYF3L92zCesW2HaYeQC'
SPREADSHEET_ID = '1GmS-3ZjpKcUgyntzBTS0Wss3fAL2xJ2gBh8s14mZg5M'
SHEET_NAME = 'Form Entries'  # Must match tab name in sheet

# --- AUTHENTICATE GOOGLE APIs ---
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=credentials)
    gc = gspread.authorize(credentials)
    worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
except Exception as e:
    st.error("❌ Authentication or Access Error:")
    st.code(traceback.format_exc())
    st.stop()

# --- FUNCTION: Compress and Upload Screenshot to Google Drive ---
def upload_to_drive(file, filename):
    try:
        # Open image using PIL
        image = Image.open(file)

        # Optional: Resize if larger than 1280px in either dimension
        max_size = (1280, 1280)
        image.thumbnail(max_size)

        # Convert to JPEG and compress
        compressed_buffer = io.BytesIO()
        image.convert("RGB").save(
            compressed_buffer,
            format="JPEG",
            quality=75,          # You can increase to 85 if needed
            optimize=True
        )
        compressed_buffer.seek(0)

        # Upload to Google Drive
        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
        media = MediaIoBaseUpload(compressed_buffer, mimetype="image/jpeg")
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        return uploaded_file.get("id")

    except Exception as e:
        st.error("❌ Failed to compress and upload image")
        st.code(traceback.format_exc())
        return None

# --- STREAMLIT FORM UI ---
st.title("📝 Auditor Error Logger")

with st.form("error_form"):
    auditor = st.text_input("👤 Auditor Name")
    file_no = st.text_input("📁 File No")
    error_desc = st.text_area("🔍 Description of Error")
    screenshot = st.file_uploader("📸 Upload Screenshot (optional)", type=["jpg", "jpeg", "png"])

    submitted = st.form_submit_button("✅ Submit Entry")

if submitted:
    with st.spinner("⏳ Please wait while we submit your entry..."):
        now = datetime.now().strftime("%d-%m-%Y %H:%M")
        screenshot_link = ""

        if screenshot and file_no:
            filename = f"{file_no} {now.split()[0]}.jpg"  # Force JPG for consistency
            file_id = upload_to_drive(screenshot, filename)
            if file_id:
                screenshot_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

        # Add headers if missing
        headers = ["DateTime", "Auditor", "File No", "Error Description", "Screenshot Link"]
        values = worksheet.get_all_values()
        if not values or values[0] != headers:
            worksheet.insert_row(headers, 1)

        # Append data
        worksheet.append_row([
            now,
            auditor,
            file_no,
            error_desc,
            screenshot_link
        ])

    st.success("✅ Entry submitted successfully!")
    if screenshot_link:
        st.markdown(f"[📎 View Screenshot]({screenshot_link})")

# --- FOOTER ---
st.markdown("---")
st.caption("")
