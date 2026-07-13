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

# ⚠️ รหัสโฟลเดอร์ Google Drive (แนะนำให้ใช้เมลส่วนตัวทำโฟลเดอร์แชร์เพื่อป้องกันระบบโรงเรียนบล็อก)
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHPp9ME88HVnhPdb'

if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR, exist_ok=True)

def build_face_database():
    """ฟังก์ชันมุดโฟลเดอร์ซ้อนย่อยเพื่อดาวน์โหลดรูปภาพและทำดัชนีใบหน้าคน"""
    if GOOGLE_DRIVE_FOLDER_ID:
        try:
            print("🔄 1. กำลังดึงรูปภาพจาก Google Drive มุดทะลุทุกโฟลเดอร์ย่อย...")
            gdown.download_folder(id=GOOGLE_DRIVE_FOLDER_ID, output=PHOTOS_DIR, quiet=True, remaining_ok=True)
            print("✅ ดาวน์โหลดรูปภาพลงเซิร์ฟเวอร์เสร็จสิ้น!")
            
            # เริ่มกระบวนการแกะรหัสใบหน้าเก็บไว้เป็นฐานข้อมูลออฟไลน์
            face_db = {}
            print("🔄 2. AI กำลังวิเคราะห์และจดจำใบหน้าจากรูปภาพทั้งหมด (ทำครั้งแรก)...")
            
            for root, dirs, files in os.walk(PHOTOS_DIR):
                for filename in files:
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        file_path = os.path.join(root, filename)
                        try:
                            # โหลดรูปภาพเข้าสู่ AI Model
                            image = face_recognition.load_image_file(file_path)
                            # ค้นหาตำแหน่งและถอดรหัสใบหน้า (หันข้างหรือแสงเปลี่ยนก็ถอดรหัสได้)
                            encodings = face_recognition.face_encodings(image)
                            
                            if len(encodings) > 0:
                                # บันทึกที่อยู่ไฟล์ภาพสัมพัทธ์คู่กับรหัสใบหน้า (เก็บทุกหน้าที่เจอในรูปนั้น)
                                relative_path = os.path.relpath(file_path, PHOTOS_DIR).replace('\\', '/')
                                face_db[relative_path] = encodings
                        except Exception as e:
                            print(f"ข้ามไฟล์เนื่องจากมีข้อผิดพลาด {filename}: {e}")
            
            # เซฟฐานข้อมูลใบหน้าเป็นไฟล์ระบบเล็กๆ เพื่อเรียกใช้ได้ทันที 24 ชม.
            with open(DB_PATH, 'wb') as f:
                pickle.dump(face_db, f)
            print(f"🎉 สร้างคลังรหัสใบหน้าเสร็จสมบูรณ์! บันทึกรูปภาพที่มีใบหน้าแล้ว: {len(face_db)} รูป")
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในระบบฐานข้อมูล: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    # ตรวจสอบว่าถ้าเปิดเว็บครั้งแรกและยังไม่มีฐานข้อมูลใบหน้า ให้ทำระบบซิงค์ข้อมูลก่อน
    if not os.path.exists(DB_PATH):
        build_face_database()
        
    matched_photos = []
    
    if request.method == 'POST':
        file = request.files.get('search_face')
        if file and file.filename != '':
            temp_target_path = os.path.join(BASE_DIR, 'temp_target.jpg')
            file.save(temp_target_path)
            
            try:
                # 1. ถอดรหัสใบหน้าจากรูปที่เราอัปโหลดเข้าไปหา
                target_image = face_recognition.load_image_file(temp_target_path)
                target_encodings = face_recognition.face_encodings(target_image)
                
                if len(target_encodings) > 0:
                    my_face_encoding = target_encodings[0]
                    
                    # 2. โหลดฐานข้อมูลใบหน้ารูปทั้งหมดขึ้นมาเทียบ
                    if os.path.exists(DB_PATH):
                        with open(DB_PATH, 'rb') as f:
                            face_db = pickle.dump = pickle.load(f)
                        
                        # วิ่งไล่เช็คทีละรูปภาพ
                        for relative_path, encodings_in_photo in face_db.items():
                            # เปรียบเทียบรหัสใบหน้าเรา กับทุกใบหน้าที่อยู่ในรูปนั้นๆ
                            # tolerance=0.55 คือค่าความยืดหยุ่นสูง หน้าเอียง แสงเปลี่ยน หรือใส่แมสก์ก็หาเจอ
                            matches = face_recognition.compare_faces(encodings_in_photo, my_face_encoding, tolerance=0.55)
                            
                            if True in matches:
                                matched_photos.append(relative_path)
                else:
                    print("❌ ไม่พบใบหน้าในรูปภาพต้นแบบที่อัปโหลดมา")
            except Exception as e:
                print(f"Error during search: {e}")
                
            if os.path.exists(temp_target_path):
                os.remove(temp_target_path)
                
    return render_template('index.html', matched_photos=matched_photos)

if __name__ == '__main__':
    # รันบนเครื่องคอม Local หรือ คลาวด์
    app.run(host='0.0.0.0', debug=True, port=5000)