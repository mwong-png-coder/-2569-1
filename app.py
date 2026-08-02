import io
import os
import re
import json
from flask import Flask, render_template, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# ----------------- ตั้งค่า Google Drive -----------------
SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.metadata.readonly']

def get_drive_service():
    """เชื่อมต่อกับ Google Drive API"""
    creds_json_str = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if creds_json_str:
        try:
            creds_info = json.loads(creds_json_str)
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        except Exception:
            creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    else:
        creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            
    return build('drive', 'v3', credentials=creds)

def extract_folder_id(url):
    """ดึง Folder ID จาก URL ของ Google Drive"""
    match = re.search(r'folders/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return url.strip()

# ----------------- Routes -----------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# Route สำหรับซิงค์ข้อมูลรูปจากโฟลเดอร์ Google Drive
@app.route('/admin/sync-folder', methods=['POST'])
def sync_folder():
    try:
        data = request.get_json()
        folder_url = data.get('folder_url', '')
        folder_id = extract_folder_id(folder_url)

        if not folder_id:
            return jsonify({'success': False, 'message': 'กรุณาระบุ URL โฟลเดอร์ Google Drive ให้ถูกต้อง'}), 400

        service = get_drive_service()

        # 1. ดึงชื่อโฟลเดอร์
        folder_metadata = service.files().get(fileId=folder_id, fields='name').execute()
        folder_name = folder_metadata.get('name', 'ไม่ทราบชื่อโฟลเดอร์')

        # 2. ค้นหารูปภาพทั้งหมดในโฟลเดอร์นั้น
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="files(id, name, webViewLink, thumbnailLink)"
        ).execute()

        photos = results.get('files', [])

        return jsonify({
            'success': True,
            'message': f'พบอัลบั้ม "{folder_name}" พร้อมรูปภาพจำนวน {len(photos)} รูปใน Google Drive เรียบร้อยแล้ว!'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'ไม่สามารถเข้าถึงโฟลเดอร์ได้: {str(e)} (กรุณาเช็กว่าได้กดแชร์โฟลเดอร์ให้ Service Account หรือยัง)'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)