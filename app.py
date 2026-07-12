import os
import cv2
import gdown
import numpy as np
from flask import Flask, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'photos')

# ⚠️ แปะ "รหัสโฟลเดอร์แชร์ยาวๆ" จาก Google Drive ของนายลงในนี้
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHPp9ME88HVnhPdb'

if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR, exist_ok=True)

def sync_photos_from_drive():
    if GOOGLE_DRIVE_FOLDER_ID and GOOGLE_DRIVE_FOLDER_ID != '1O6e6-XFTMsz6R1MJBHPp9ME88HVnhPdb':
        try:
            print("🔄 กำลังซิงค์รูปภาพจาก Google Drive...")
            gdown.download_folder(id=GOOGLE_DRIVE_FOLDER_ID, output=PHOTOS_DIR, quiet=False, remaining_ok=True)
            
            # นับจำนวนรูปที่โหลดมาได้จริงเพื่อตรวจสอบสิทธิ์ไดร์ฟ
            total_files = 0
            for r, d, f in os.walk(PHOTOS_DIR):
                total_files += len([file for file in f if file.lower().endswith(('.png', '.jpg', '.jpeg'))])
            print(f"✅ ซิงค์เสร็จสิ้น! ตรวจพบรูปภาพในคลังทั้งหมด: {total_files} รูป")
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการดึงรูปจาก Drive: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        sync_photos_from_drive()
        
    matched_photos = []
    
    if request.method == 'POST':
        file = request.files.get('search_face')
        if file and file.filename != '':
            temp_target_path = os.path.join(BASE_DIR, 'temp_target.jpg')
            file.save(temp_target_path)
            
            target_img = cv2.imread(temp_target_path)
            if target_img is not None:
                # ใช้ตัวสแกนโมเดลพื้นฐานของระบบเพื่อความเสถียรสูงสุด
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                
                # ดึงค่าสีรูปภาพต้นฉบับ
                target_hist = cv2.calcHist([target_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                cv2.normalize(target_hist, target_hist, 0, 1, cv2.NORM_MINMAX)
                
                if os.path.exists(PHOTOS_DIR):
                    for root, dirs, files in os.walk(PHOTOS_DIR):
                        for filename in files:
                            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                file_path = os.path.join(root, filename)
                                try:
                                    current_img = cv2.imread(file_path)
                                    if current_img is not None:
                                        # เทียบโครงสร้างสีภาพ (ตั้งเกณฑ์ไว้ต่ำมากที่ 0.02 เพื่อให้ภาพยอมขึ้นมาก่อน)
                                        current_hist = cv2.calcHist([current_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                                        cv2.normalize(current_hist, current_hist, 0, 1, cv2.NORM_MINMAX)
                                        similarity = cv2.compareHist(target_hist, current_hist, cv2.HISTCMP_CORREL)
                                        
                                        if similarity > 0.02:
                                            # ป้องกันบั๊กภาษาไทยด้วยการตัด Path แบบเด็ดขาดให้เหลือเฉพาะที่ชี้จากใน static/photos/
                                            web_path = os.path.relpath(file_path, PHOTOS_DIR).replace('\\', '/')
                                            if web_path not in matched_photos:
                                                matched_photos.append(web_path)
                                except Exception as e:
                                    print(f"Error scanning {filename}: {e}")
            
            if os.path.exists(temp_target_path):
                os.remove(temp_target_path)
                            
    return render_template('index.html', matched_photos=matched_photos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)