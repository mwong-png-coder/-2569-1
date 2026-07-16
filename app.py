import os
import gdown
from flask import Flask, render_template, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'photos')

# ⚠️ รหัสโฟลเดอร์ Google Drive อันล่าสุดของนายเรียบร้อยครับ
GOOGLE_DRIVE_FOLDER_ID = '1G3-i_p57ReBsRHzkZj4ID1YAdfjPLrbq'

if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR, exist_ok=True)

def sync_photos_from_drive():
    if GOOGLE_DRIVE_FOLDER_ID:
        try:
            print("🔄 กำลังดึงไฟล์รูปภาพจาก Google Drive...")
            gdown.download_folder(id=GOOGLE_DRIVE_FOLDER_ID, output=PHOTOS_DIR, quiet=True, remaining_ok=True)
            print("✅ ดาวน์โหลดรูปภาพทั้งหมดจากโฟลเดอร์เสร็จสิ้น!")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการดึงรูปภาพ: {e}")

@app.route('/')
def index():
    sync_photos_from_drive()
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    """ส่งรายชื่อไฟล์รูปภาพทั้งหมดในคลังออกไปให้หน้าบ้านประมวลผล AI"""
    photo_list = []
    if os.path.exists(PHOTOS_DIR):
        for root, dirs, files in os.walk(PHOTOS_DIR):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(root, filename)
                    web_path = os.path.relpath(file_path, PHOTOS_DIR).replace('\\', '/')
                    photo_list.append(web_path)
    return jsonify(photo_list)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)