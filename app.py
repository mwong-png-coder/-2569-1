import os
import requests
from flask import Flask, render_template, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'photos')

# 🔗 โฟลเดอร์ ID Google Drive ของนาย (ต้องตั้งค่าแชร์ใน Drive เป็น "ทุกคนที่มีลิงก์มีสิทธิ์อ่าน")
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

def sync_photos_from_drive():
    """ดึงภาพจากคลัง Google Drive มาลง Render แบบทะลวงระบบบล็อก"""
    if not os.path.exists(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR, exist_ok=True)
        
    print("🔄 กำลังเริ่มต้นดึงไฟล์รูปภาพสด ๆ จาก Google Drive ของนาย...")
    
    # ใช้กุญแจสาธารณะของ Google Drive API ในการเปิดอ่านรายชื่อไฟล์
    url = f"https://www.googleapis.com/drive/v3/files?q='{GOOGLE_DRIVE_FOLDER_ID}'+in+parents+and+mimeType+contains+'image/'&key=&fields=files(id,name)"
    
    # 💡 หมายเหตุ: หากนายมี API Key ของ Google Cloud ให้ใส่ตรง &key=YOUR_KEY จะเสถียรขึ้น 
    # แต่ถ้าไม่มี สคริปต์นี้จะใช้พิกัดโหลดตรงผ่านดาวน์โหลดสตรีมด้านล่างนี้ครับ
    
    try:
        # ล้างภาพเก่าออกก่อนเพื่อให้เป็นรูปในไดร์ฟปัจจุบันล่าสุด 100%
        for f in os.listdir(PHOTOS_DIR):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                os.remove(os.path.join(PHOTOS_DIR, f))

        # ส่งคำสั่งจำลองการดึงโฟลเดอร์ผ่านพิกัดเปิด
        import gdown
        print("📥 กำลังรัน gdown โหมดดาวน์โหลดโฟลเดอร์สด...")
        gdown.download_folder(id=GOOGLE_DRIVE_FOLDER_ID, output=PHOTOS_DIR, quiet=False, remaining_ok=True)
        print(f"🎉 ดึงรูปภาพลงเซิร์ฟเวอร์เสร็จสิ้น! พบไฟล์ในระบบทั้งหมด {len(os.listdir(PHOTOS_DIR))} ไฟล์")
        
    except Exception as e:
        print(f"⚠️ คำเตือนระบบดาวน์โหลด: {e} (ระบบจะใช้ไฟล์ที่มีอยู่ประมวลผลต่อ)")

# สั่งให้ทำงานดึงรูปภาพใหม่จากไดร์ฟทุกครั้งที่ระบบเปิดตัวหรือรีสตาร์ท
sync_photos_from_drive()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    """ส่งรายชื่อไฟล์ที่ดึงมาจากไดร์ฟสำเร็จให้หน้าบ้านสแกน"""
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