import os
import requests
import base64
import io
from flask import Flask, render_template, jsonify, request
from PIL import Image
from pillow_heif import register_heif_opener
import face_recognition
import numpy as np

# เปิดระบบรองรับไฟล์รูปภาพ iPhone HEIC/HEIF
register_heif_opener()

app = Flask(__name__)

# ID โฟลเดอร์ Google Drive เก็บรูปภาพกิจกรรมโรงเรียนของนาย
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

# ตัวแปร Global สำหรับเก็บแคชรูปภาพและเวกเตอร์ใบหน้าในไดร์ฟ (ช่วยให้กดสแกนแล้วเจอทันที ไม่ต้องโหลดใหม่ทุกรอบ)
cached_photos = []

def load_drive_photos():
    """โหลดไฟล์ภาพทั้งหมดจาก Drive มาประมวลผลหาใบหน้าเก็บไว้ในหน่วยความจำล่วงหน้า"""
    global cached_photos
    try:
        print("⚡ กำลังเริ่มดึงข้อมูลรูปภาพจาก Google Drive...")
        url = f"https://www.googleapis.com/drive/v3/files?q='{GOOGLE_DRIVE_FOLDER_ID}'+in+parents+and+mimeType+contains+'image/'&fields=files(id,name)&pageSize=100"
        response = requests.get(url)
        drive_files = response.json().get('files', [])
        
        temporary_cache = []
        for file in drive_files:
            file_id = file['id']
            download_url = f"https://docs.google.com/uc?export=download&id={file_id}"
            img_resp = requests.get(download_url)
            
            if img_resp.status_code == 200:
                try:
                    # โหลดรูปภาพและแปลงระบบสีเป็น RGB เพื่อให้โมเดล AI สแกนได้แม่นยำ
                    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                    # ย่อขนาดรูปในไดร์ฟลงมาเล็กน้อยเพื่อประหยัด RAM และให้สแกนไวขึ้น
                    img.thumbnail((800, 800))
                    img_np = np.array(img)
                    
                    # คำนวณเวกเตอร์ใบหน้าทั้งหมดในรูปภาพนั้น (รองรับรูปหมู่หลายๆ คน)
                    face_encodings = face_recognition.face_encodings(img_np)
                    
                    # แปลงรูปภาพกลับเป็น Base64 เพื่อส่งไปแสดงผลบนหน้าเว็บ
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG", quality=80)
                    encoded_img = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    temporary_cache.append({
                        "id": file_id,
                        "name": file['name'],
                        "base64": f"data:image/jpeg;base64,{encoded_img}",
                        "encodings": face_encodings
                    })
                    print(f"✔️ ประมวลผลรูปภาพสำเร็จ: {file['name']}")
                except Exception as ex:
                    print(f"❌ ข้ามการสแกนไฟล์ {file['name']}: {ex}")
                    
        cached_photos = temporary_cache
        print(f"🎉 โหลดคลังรูปภาพและบันทึกเวกเตอร์สำเร็จทั้งหมด: {len(cached_photos)} รูป")
    except Exception as e:
        print(f"💥 เกิดข้อผิดพลาดในการเชื่อมต่อ Google Drive: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/init-status')
def init_status():
    """ดึงสถานะระบบ ถ้าแคชว่างให้สั่งโหลดใหม่ให้อัตโนมัติ"""
    if not cached_photos:
        load_drive_photos()
    return jsonify({"status": "ready", "total": len(cached_photos)})

@app.route('/api/search-face', methods=['POST'])
def search_face():
    """รับภาพหัวเชื้อจากผู้ใช้ -> ตรวจหาใบหน้า -> เปรียบเทียบหาพิกเซลที่ตรงกันในไดร์ฟ"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'กรุณาอัปโหลดรูปภาพหัวเชื้อ'}), 400
            
        file = request.files['file']
        
        # โหลดรูปภาพหัวเชื้อที่นายส่งมาค้นหา
        target_img = Image.open(file).convert("RGB")
        target_img.thumbnail((800, 800))
        target_np = np.array(target_img)
        
        # ค้นหาเวกเตอร์ใบหน้าในภาพหัวเชื้อ
        target_encodings = face_recognition.face_encodings(target_np)
        
        if not target_encodings:
            return jsonify({'error': 'AI ตรวจไม่พบใบหน้าคนในรูปภาพหัวเชื้อของนายเลยครับ ลองใช้รูปหน้าตรงชัดๆ ดูนะ'}), 400
            
        target_encoding = target_encodings[0]
        matched_results = []
        
        # วนลูปเปรียบเทียบพิกเซลกับรูปที่แคชไว้ทั้งหมด
        for photo in cached_photos:
            if not photo["encodings"]:
                continue
                
            # เปรียบเทียบใบหน้า (ค่า tolerance=0.55 เหมาะกับรูปทำกิจกรรมที่มีการหันหน้า เอียง หรือแสงเปลี่ยน)
            matches = face_recognition.compare_faces(photo["encodings"], target_encoding, tolerance=0.55)
            
            if True in matches:
                matched_results.append({
                    "id": photo["id"],
                    "name": photo["name"],
                    "base64": photo["base64"]
                })
                
        return jsonify({"matches": matched_results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # รันการดึงรูปภาพจากไดร์ฟมาแคชตั้งแต่สตาร์ทเครื่องเซิร์ฟเวอร์
    load_drive_photos()
    app.run(host='0.0.0.0', port=5000, debug=True)