import io
import os
from flask import Flask, render_template, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# 1. ประกาศตัวแปร app ก่อนเสมอเพื่อป้องกัน NameError
app = Flask(__name__)

# ----------------- ตั้งค่า Google Drive -----------------
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'credentials.json' # ไฟล์คีย์ JSON จาก Google Cloud Console

# Folder ID หลักใน Drive โรงเรียนที่คุณให้มา
MAIN_FOLDER_ID = '132CYeMEU-ZBUU0vMxsV73aw2W8zugwXm' 

def get_drive_service():
    """เชื่อมต่อกับ Google Drive API"""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def create_subfolder_in_drive(folder_name, parent_folder_id):
    """สร้างโฟลเดอร์ย่อยใหม่ตามชื่องานใน Google Drive"""
    service = get_drive_service()
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def upload_file_to_drive(file_obj, filename, target_folder_id):
    """อัปโหลดไฟล์รูปภาพเข้าโฟลเดอร์ย่อย"""
    service = get_drive_service()
    file_metadata = {
        'name': filename,
        'parents': [target_folder_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(file_obj.read()), mimetype=file_obj.content_type, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    return file

# ----------------- Routes -----------------

@app.route('/')
def home():
    return "Web Application is running!"

# Route หน้าเว็บแอดมินสำหรับอัปโหลด
@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# Route รับข้อมูลสร้างโฟลเดอร์และอัปโหลดรูป
@app.route('/admin/upload-event', methods=['POST'])
def admin_upload_event():
    try:
        event_name = request.form.get('event_name')
        files = request.files.getlist('photos')
        
        if not event_name or not files or files[0].filename == '':
            return jsonify({'success': False, 'message': 'กรุณาระบุชื่องานและเลือกรูปภาพอย่างน้อย 1 รูป'}), 400

        # 1. สร้างโฟลเดอร์ตามชื่องานใน Google Drive
        subfolder_id = create_subfolder_in_drive(event_name, MAIN_FOLDER_ID)
        
        # 2. วนลูปยิงรูปเข้าไปในโฟลเดอร์นั้น
        uploaded_count = 0
        for file in files:
            if file and file.filename != '':
                upload_file_to_drive(file, file.filename, subfolder_id)
                uploaded_count += 1

        return jsonify({
            'success': True, 
            'message': f'สร้างโฟลเดอร์ "{event_name}" และอัปโหลดรูปภาพจำนวน {uploaded_count} รูปเข้า Google Drive เรียบร้อยแล้ว!'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)