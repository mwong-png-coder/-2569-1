import os
import requests
import base64
import io
import re
from flask import Flask, render_template, jsonify, request
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

app = Flask(__name__)

# ไอดีโฟลเดอร์ Google Drive ของนาย (ความยาว 28 ตัวอักษร)
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    try:
        # เข้าถึงหน้าเว็บแสดงผลไฟล์ของโฟลเดอร์โดยตรง
        folder_url = f"https://drive.google.com/embeddedfolderview?id={GOOGLE_DRIVE_FOLDER_ID}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(folder_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ ดึงข้อมูลโฟลเดอร์ขัดข้อง: {response.status_code}")
            return jsonify([])

        # ปรับแก้ Regex: รองรับความยาวของ Google Drive File ID ตั้งแต่ 25 ถึง 35 ตัวอักษร (แก้ปัญหาค้นหาไม่เจอ)
        raw_ids = re.findall(r'\"id\":\"([a-zA-Z0-9_-]{25,35})\"', response.text)
        
        # ค้นหาเพิ่มเติมในโครงสร้างสำรอง
        if not raw_ids:
            raw_ids = re.findall(r'id=([a-zA-Z0-9_-]{25,35})', response.text)
            
        file_ids = list(set(raw_ids))
        photo_data_list = []
        
        print(f"🔍 ตรวจพบไอดีที่น่าจะเป็นไฟล์รูปภาพ: {len(file_ids)} รายการ")

        for file_id in file_ids:
            # ข้ามไอดีของโฟลเดอร์หลัก
            if file_id == GOOGLE_DRIVE_FOLDER_ID:
                continue
                
            download_url = f"https://docs.google.com/uc?export=download&id={file_id}"
            img_resp = requests.get(download_url)
            
            if img_resp.status_code == 200:
                try:
                    # ทดสอบเปิดไฟล์เพื่อกรองเอาเฉพาะไฟล์ที่เป็นรูปภาพจริง ๆ
                    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                    img.thumbnail((600, 600))  # ย่อขนาดรูปภาพเพื่อลดปริมาณการส่งข้อมูลและทำให้ AI สแกนพิกเซลเร็วขึ้น
                    
                    output = io.BytesIO()
                    img.save(output, format="JPEG", quality=80)
                    encoded_img = base64.b64encode(output.getvalue()).decode('utf-8')
                    
                    photo_data_list.append({
                        "id": file_id,
                        "name": f"drive_image_{file_id[:6]}.jpg",
                        "base64": f"data:image/jpeg;base64,{encoded_img}"
                    })
                    print(f"✔️ โหลดและย่อรูปภาพสำเร็จ: {file_id}")
                except Exception:
                    # ข้ามไฟล์ที่ไม่ใช่รูปภาพโดยอัตโนมัติ
                    continue

        print(f"🎉 สรุปผล: ดึงภาพจากโฟลเดอร์สาธารณะของนายได้จริงสำเร็จ {len(photo_data_list)} รูป")
        return jsonify(photo_data_list)
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในส่วนดึงข้อมูลหลังบ้าน: {e}")
        return jsonify([])

@app.route('/api/convert-heic', methods=['POST'])
def convert_heic():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        file = request.files['file']
        image = Image.open(file)
        image.thumbnail((600, 600)) 
        
        output = io.BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=80)
        output.seek(0)
        
        encoded_img = base64.b64encode(output.read()).decode('utf-8')
        return jsonify({'base64': f"data:image/jpeg;base64,{encoded_img}"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)