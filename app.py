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

# ไอดีโฟลเดอร์ Google Drive ของนาย
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    try:
        # ดึงหน้าเว็บแชร์สาธารณะของ Google Drive (วิธีนี้เลี่ยงการใช้ API Key ได้ 100%)
        folder_url = f"https://drive.google.com/embeddedfolderview?id={GOOGLE_DRIVE_FOLDER_ID}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(folder_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ ไม่สามารถดึงหน้าเว็บโฟลเดอร์ได้: {response.status_code}")
            return jsonify([])

        # ใช้ Regex ค้นหารหัส File ID ของรูปภาพทั้งหมดที่ซ่อนอยู่ในหน้าเว็บ
        # ปกติไฟล์ใน Google Drive จะมี ID ความยาว 33 ตัวอักษรประกอบด้วยตัวอักษรและตัวเลข
        file_ids = list(set(re.findall(r'\"id\":\"([a-zA-Z0-9_-]{33})\"', response.text)))
        
        # ป้องกันกรณีแพทเทิร์น ID ยาวต่างกัน (มองหารูปแบบดึงไฟล์ทั่วไป)
        if not file_ids:
            file_ids = list(set(re.findall(r'id=([a-zA-Z0-9_-]{25,})', response.text)))

        photo_data_list = []
        print(f"🔍 ตรวจพบไฟล์ดิบในไดรฟ์ของนาย: {len(file_ids)} ไฟล์ กำลังแปลงพิกเซล...")

        for file_id in file_ids:
            # ข้าม ID โฟลเดอร์ตัวเอง
            if file_id == GOOGLE_DRIVE_FOLDER_ID:
                continue
                
            download_url = f"https://docs.google.com/uc?export=download&id={file_id}"
            img_resp = requests.get(download_url)
            
            if img_resp.status_code == 200:
                try:
                    # โหลดและแปลงไฟล์ภาพ
                    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                    img.thumbnail((600, 600))  # บีบพิกเซลให้เบาลงเพื่อสแกนเร็วขึ้น
                    
                    output = io.BytesIO()
                    img.save(output, format="JPEG", quality=80)
                    encoded_img = base64.b64encode(output.getvalue()).decode('utf-8')
                    
                    photo_data_list.append({
                        "id": file_id,
                        "name": f"drive_image_{file_id[:6]}.jpg",
                        "base64": f"data:image/jpeg;base64,{encoded_img}"
                    })
                except Exception as ex:
                    # ข้ามไฟล์ที่ไม่ใช่รูปภาพ (เช่น ไฟล์เอกสารอื่นๆ ในไดรฟ์)
                    continue

        print(f"🎉 สำเร็จ! โหลดและเปิดใช้งานรูปภาพจาก Google Drive ได้จริง: {len(photo_data_list)} รูป")
        return jsonify(photo_data_list)
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดทางเทคนิค: {e}")
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