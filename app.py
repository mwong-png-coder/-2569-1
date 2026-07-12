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
            
            # อ่านรูปที่เราต้องการหา
            target_img = cv2.imread(temp_target_path)
            if target_img is not None:
                # แก้ปัญหาตัวตรวจจับใบหน้า: ดึงไฟล์ xml ตรงจาก github มาเซ็ตค่า
                cascade_url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
                cascade_path = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
                
                if not os.path.exists(cascade_path):
                    import urllib.request
                    try:
                        urllib.request.urlretrieve(cascade_url, cascade_path)
                    except Exception as e:
                        print(f"Error downloading cascade: {e}")

                face_cascade = cv2.CascadeClassifier(cascade_path)
                
                # เช็คว่าโหลดโมเดลเข้าตัวแปรสำเร็จไหมก่อนเริ่มทำงาน
                if not face_cascade.empty():
                    gray_target = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
                    faces_target = face_cascade.detectMultiScale(gray_target, 1.1, 4)
                    
                    # ค้นหาภาพโดยการใช้ os.walk มุดเข้าไปในทุกโฟลเดอร์ย่อย
                    if os.path.exists(PHOTOS_DIR):
                        for root, dirs, files in os.walk(PHOTOS_DIR):
                            for filename in files:
                                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    file_path = os.path.join(root, filename)
                                    try:
                                        current_img = cv2.imread(file_path)
                                        if current_img is not None:
                                            # เช็คความคล้ายของพิกเซลภาพหน้าจอ
                                            res = cv2.matchTemplate(cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY), gray_target, cv2.TM_CCOEFF_NORMED)
                                            _, max_val, _, _ = cv2.minMaxLoc(res)
                                            
                                            # เกณฑ์ความเหมือน
                                            if max_val > 0.15: 
                                                # แปลงที่อยู่ไฟล์ย่อยให้เป็น Path สำหรับใช้แสดงผลบนหน้าเว็บ Static HTML
                                                relative_path = os.path.relpath(file_path, PHOTOS_DIR).replace('\\', '/')
                                                matched_photos.append(relative_path)
                                    except Exception as e:
                                        print(f"Error scanning {filename}: {e}")
                else:
                    print("❌ ไม่สามารถโหลดไฟล์ Haar Cascade สำหรับตรวจจับใบหน้าได้")
            
            if os.path.exists(temp_target_path):
                os.remove(temp_target_path)
                            
    return render_template('index.html', matched_photos=matched_photos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)