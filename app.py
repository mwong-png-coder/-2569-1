import os
import cv2
import gdown
import numpy as np
from flask import Flask, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'photos')

# ⚠️ รหัสโฟลเดอร์ Google Drive โรงเรียนของนาย
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHPp9ME88HVnhPdb'

if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR, exist_ok=True)

def sync_photos_from_drive():
    if GOOGLE_DRIVE_FOLDER_ID:
        try:
            print("🔄 กำลังดึงรูปภาพแบบมุดทุกโฟลเดอร์ย่อยจาก Google Drive...")
            gdown.download_folder(id=GOOGLE_DRIVE_FOLDER_ID, output=PHOTOS_DIR, quiet=True, remaining_ok=True)
            
            total_files = 0
            for r, d, f in os.walk(PHOTOS_DIR):
                total_files += len([file for file in f if file.lower().endswith(('.png', '.jpg', '.jpeg'))])
            print(f"✅ ซิงค์เสร็จสิ้น! พบรูปภาพในคลังทั้งหมด: {total_files} รูป")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการดึงรูปภาพ: {e}")

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
                # โหลดโมเดลผ่าน path สัมบูรณ์เพื่อความชัวร์บน Linux ของ Render
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
                
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
                                        gray_current = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                                        
                                        faces = face_cascade.detectMultiScale(gray_current, 1.1, 4)
                                        profiles = profile_cascade.detectMultiScale(gray_current, 1.1, 4)
                                        
                                        current_hist = cv2.calcHist([current_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                                        cv2.normalize(current_hist, current_hist, 0, 1, cv2.NORM_MINMAX)
                                        similarity = cv2.compareHist(target_hist, current_hist, cv2.HISTCMP_CORREL)
                                        
                                        if len(faces) > 0 or len(profiles) > 0 or similarity > 0.65:
                                            web_path = os.path.relpath(file_path, PHOTOS_DIR).replace('\\', '/')
                                            if web_path not in matched_photos:
                                                matched_photos.append(web_path)
                                except Exception as e:
                                    pass
            
            if os.path.exists(temp_target_path):
                os.remove(temp_target_path)
                            
    return render_template('index.html', matched_photos=matched_photos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)