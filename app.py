import os
import cv2
import gdown
import pickle
import numpy as np
import face_recognition
from flask import Flask, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'photos')
DB_PATH = os.path.join(BASE_DIR, 'face_database.pkl')

# ⚠️ ใส่ ID โฟลเดอร์ Google Drive โรงเรียนของนายตรงนี้
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHPp9ME88HVnhPdb'

if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR, exist_ok=True)

def build_face_database():
    """ฟังก์ชันเจาะลึกทุกชั้นโฟลเดอร์ย่อย ดึงรูปภาพ และวิเคราะห์โครงสร้างใบหน้าแบบประหยัด RAM"""
    if GOOGLE_DRIVE_FOLDER_ID:
        try:
            print("🔄 1. กำลังดึงรูปภาพมุดทะลุทุกโฟลเดอร์ย่อยจาก Google Drive...")
            gdown.download_folder(id=GOOGLE_DRIVE_FOLDER_ID, output=PHOTOS_DIR, quiet=True, remaining_ok=True)
            print("✅ ดาวน์โหลดและซิงค์โครงสร้างรูปภาพเสร็จสิ้น!")
            
            face_db = {}
            print("🔄 2. AI กำลังวิเคราะห์จดจำใบหน้าจากรูปภาพทั้งหมด (โหมดประหยัด RAM)...")
            
            # มุดลึกเข้าไปหาในทุกชั้นโฟลเดอร์ย่อย (โฟลเดอร์เดือน -> กิจกรรม -> วันที่)
            for root, dirs, files in os.walk(PHOTOS_DIR):
                for filename in files:
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        file_path = os.path.join(root, filename)
                        try:
                            img = cv2.imread(file_path)
                            if img is not None:
                                # 💡 ย่อขนาดรูปภาพลง 50% เพื่อป้องกัน RAM บนคลาวด์ Render เต็ม
                                small_img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
                                rgb_small_img = cv2.cvtColor(small_img, cv2.COLOR_BGR2RGB)
                                
                                # AI ทำการถอดรหัสใบหน้า (รองรับหน้าเอียง แสงเปลี่ยน)
                                encodings = face_recognition.face_encodings(rgb_small_img)
                                
                                if len(encodings) > 0:
                                    relative_path = os.path.relpath(file_path, PHOTOS_DIR).replace('\\', '/')
                                    face_db[relative_path] = encodings
                        except Exception as e:
                            pass
            
            with open(DB_PATH, 'wb') as f:
                pickle.dump(face_db, f)
            print(f"🎉 คลังใบหน้าพร้อมใช้งาน! บันทึกแล้ว: {len(face_db)} รูป")
            
        except Exception as e:
            print(f"❌ บั๊กในระบบฐานข้อมูล: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if not os.path.exists(DB_PATH):
        build_face_database()
        
    matched_photos = []
    
    if request.method == 'POST':
        file = request.files.get('search_face')
        if file and file.filename != '':
            temp_target_path = os.path.join(BASE_DIR, 'temp_target.jpg')
            file.save(temp_target_path)
            
            try:
                target_img = cv2.imread(temp_target_path)
                if target_img is not None:
                    # ย่อรูปภาพที่อัปโหลดค้นหาด้วยเพื่อเซฟทรัพยากร
                    small_target = cv2.resize(target_img, (0, 0), fx=0.5, fy=0.5)
                    rgb_target = cv2.cvtColor(small_target, cv2.COLOR_BGR2RGB)
                    
                    target_encodings = face_recognition.face_encodings(rgb_target)
                    
                    if len(target_encodings) > 0:
                        my_face_encoding = target_encodings[0]
                        
                        if os.path.exists(DB_PATH):
                            with open(DB_PATH, 'rb') as f:
                                face_db = pickle.load(f)
                            
                            for relative_path, encodings_in_photo in face_db.items():
                                # tolerance=0.55 ช่วยให้หน้าเอียงเล็กน้อยหรือแสงเปลี่ยนยังหาเจอได้ดี
                                matches = face_recognition.compare_faces(encodings_in_photo, my_face_encoding, tolerance=0.55)
                                if True in matches:
                                    matched_photos.append(relative_path)
                    else:
                        print("❌ ตรวจไม่พบใบหน้าคนในรูปที่อัปโหลดค้นหา")
            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดขณะค้นหา: {e}")
                
            if os.path.exists(temp_target_path):
                os.remove(temp_target_path)
                
    return render_template('index.html', matched_photos=matched_photos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)