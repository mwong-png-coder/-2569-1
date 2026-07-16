import os
from flask import Flask, render_template, jsonify
import gdown

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'photos')

# 🔗 โฟลเดอร์ Google Drive รวมรูปภาพกิจกรรมของนาย
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

def sync_photos_from_drive():
    """ดึงไฟล์รูปภาพจาก Google Drive มาเก็บไว้ในเครื่องแบบ Lightweight"""
    if not os.path.exists(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR, exist_ok=True)
    try:
        print("🔄 กำลังซิงค์ข้อมูลรูปภาพจาก Google Drive...")
        gdown.download_folder(id=GOOGLE_DRIVE_FOLDER_ID, output=PHOTOS_DIR, quiet=True, remaining_ok=True)
        print("✅ ซิงค์รูปภาพลงระบบคลังหลังบ้านเรียบร้อยแล้ว!")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการดึงรูปภาพ: {e}")

# เรียกใช้งานฟังก์ชันดึงรูปภาพทันทีเมื่อเปิดเซิร์ฟเวอร์
sync_photos_from_drive()

@app.route('/')
def index():
    # ส่งหน้าเว็บหลักให้ฝั่งหน้าบ้านประมวลผล
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    """ส่งเฉพาะรายชื่อไฟล์รูปภาพให้โค้ด JavaScript หน้าบ้านเอาไปสแกนต่อ"""
    try:
        if os.path.exists(PHOTOS_DIR):
            valid_extensions = ('.jpg', '.jpeg', '.png')
            photos = [
                f for f in os.listdir(PHOTOS_DIR) 
                if f.lower().endswith(valid_extensions)
            ]
            return jsonify(photos)
        return jsonify([])
    except Exception as e:
        return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)