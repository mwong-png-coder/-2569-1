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
            print("✅ ซิงค์รูปภาพเสร็จสิ้น!")
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
            
            # 1. อ่านรูปเป้าหมายที่อัปโหลดมาหา
            target_img = cv2.imread(temp_target_path)
            if target_img is not None:
                cascade_url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
                cascade_path = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
                
                if not os.path.exists(cascade_path):
                    import urllib.request
                    try:
                        urllib.request.urlretrieve(cascade_url, cascade_path)
                    except Exception as e:
                        print(f"Error downloading cascade: {e}")

                face_cascade = cv2.CascadeClassifier(cascade_path)
                
                if not face_cascade.empty():
                    # ทำรูปเป้าหมายให้เป็นขาวดำ และตัดเอาเฉพาะส่วนที่เป็น "ใบหน้า" ออกมาเทียบ
                    gray_target = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
                    faces_target = face_cascade.detectMultiScale(gray_target, 1.1, 4)
                    
                    # ตรวจสอบว่าในรูปที่ส่งมาเจอใบหน้าไหม ถ้าเจอให้ตัดเอาใบหน้าแรกมาเป็นต้นแบบ
                    if len(faces_target) > 0:
                        x, y, w, h = faces_target[0]
                        face_sample = gray_target[y:y+h, x:x+w]
                        
                        # 2. เริ่มมุดหาในโฟลเดอร์ย่อยทั้งหมด
                        if os.path.exists(PHOTOS_DIR):
                            for root, dirs, files in os.walk(PHOTOS_DIR):
                                for filename in files:
                                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                        file_path = os.path.join(root, filename)
                                        try:
                                            current_img = cv2.imread(file_path)
                                            if current_img is not None:
                                                gray_current = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                                                
                                                # หาใบหน้าทุกคนที่อยู่ในรูปภาพในคลังภาพคราวละรูป
                                                faces_in_current = face_cascade.detectMultiScale(gray_current, 1.1, 4)
                                                
                                                for (cx, cy, cw, ch) in faces_in_current:
                                                    # ตัดหน้าคนในรูปคลังภาพออกมา
                                                    current_face = gray_current[cy:cy+ch, cx:cx+cw]
                                                    
                                                    # ปรับขนาดหน้าให้เท่ากับรูปต้นแบบเพื่อเข้าสูตรคำนวณเทียบพิกเซล
                                                    resized_face = cv2.resize(current_face, (w, h))
                                                    
                                                    # สแกนเทียบความคล้าย
                                                    res = cv2.matchTemplate(resized_face, face_sample, cv2.TM_CCOEFF_NORMED)
                                                    _, max_val, _, _ = cv2.minMaxLoc(res)
                                                    
                                                    # ตั้งเกณฑ์ความคล้ายแบบยืดหยุ่น (0.2 โอกาสเจอสูงขึ้นมาก)
                                                    if max_val > 0.20:
                                                        relative_path = os.path.relpath(file_path, PHOTOS_DIR).replace('\\', '/')
                                                        if relative_path not in matched_photos:
                                                            matched_photos.append(relative_path)
                                                        break # เจอคนนี้ในรูปแล้ว ข้ามไปรูปถัดไปได้เลย
                                        except Exception as e:
                                            print(f"Error scanning {filename}: {e}")
                    else:
                        print("❌ รูปที่อัปโหลดมาตรวจไม่พบใบหน้าคน กรุณาเปลี่ยนรูปที่เห็นหน้าชัดๆ ครับ")
                else:
                    print("❌ ไม่สามารถโหลดไฟล์ตรวจจับใบหน้าได้")
            
            if os.path.exists(temp_target_path):
                os.remove(temp_target_path)
                            
    return render_template('index.html', matched_photos=matched_photos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)