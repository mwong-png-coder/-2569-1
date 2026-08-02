import os
import re
import json
from flask import Flask, render_template, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# ----------------- ตั้งค่า Google Drive -----------------
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

def get_drive_service():
    """เชื่อมต่อกับ Google Drive API พร้อมแก้ปัญหา Invalid JWT Signature"""
    creds_json_str = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    
    if creds_json_str:
        try:
            creds_info = json.loads(creds_json_str)
            
            # 🛠️ แก้ไขปัญหา Invalid JWT Signature โดยการแปลง \\n ใน Private Key ให้เป็น \n จริงๆ
            if 'private_key' in creds_info and isinstance(creds_info['private_key'], str):
                creds_info['private_key'] = creds_info['private_key'].replace('\\n', '\n')
                
            creds = service_account.Credentials.from_service_account_info(
                creds_info, scopes=SCOPES
            )
        except Exception:
            # หากอ่านจาก Env Var ไม่สำเร็จ ให้สลับไปอ่านจากไฟล์ local credentials.json
            creds = service_account.Credentials.from_service_account_file(
                'credentials.json', scopes=SCOPES
            )
    else:
        # กรณีรันในเครื่องตัวเอง (Local Development)
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json', scopes=SCOPES
        )
            
    return build('drive', 'v3', credentials=creds)

def extract_folder_id(url):
    """ดึง Folder ID ออกมาจาก URL ของ Google Drive"""
    match = re.search(r'folders/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return url.strip()

# ----------------- Routes -----------------

# 1. หน้าหลัก (หน้าบ้านสำหรับคนทั่วไปสแกนหน้าค้นหารูป)
@app.route('/')
def home():
    return render_template('index.html')

# 2. หน้าแอดมินสำหรับกรอกลิงก์ซิงค์รูปภาพ
@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# 3. Route สำหรับรับลิงก์โฟลเดอร์ Google Drive มาดึงข้อมูลรูปภาพ
@app.route('/admin/sync-folder', methods=['POST'])
def sync_folder():
    try:
        data = request.get_json()
        folder_url = data.get('folder_url', '')
        folder_id = extract_folder_id(folder_url)

        if not folder_id:
            return jsonify({
                'success': False, 
                'message': 'กรุณาระบุ URL โฟลเดอร์ Google Drive ให้ถูกต้อง'
            }), 400

        service = get_drive_service()

        # 1. อ่านชื่อโฟลเดอร์ใน Google Drive
        folder_metadata = service.files().get(
            fileId=folder_id, 
            fields='name'
        ).execute()
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
        return jsonify({
            'success': False, 
            'message': f'ไม่สามารถเข้าถึงโฟลเดอร์ได้: {str(e)} (กรุณาเช็กว่าได้กดแชร์โฟลเดอร์ให้ Service Account หรือยัง)'
        }), 500

# ----------------- Main Run -----------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)