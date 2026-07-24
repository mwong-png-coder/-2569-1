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

# ID โฟลเดอร์ Google Drive ของนาย
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    """ดึงไฟล์รูปภาพและแปลงให้พร้อมส่งไปประมวลผลใบหน้าบนหน้าบ้าน"""
    try:
        # ดึงรายชื่อไฟล์จาก Google Drive
        folder_url = f"https://drive.google.com/embeddedfolderview?id={GOOGLE_DRIVE_FOLDER_ID}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(folder_url, headers=headers, timeout=15)
        
        # ดึง File ID ทั้งหมดจากโครงสร้างหน้าเว็บ
        file_ids = list(set(re.findall(r'\"id\":\"([a-zA-Z0-9_-]{25,38})\"', response.text)))
        if not file_ids:
            file_ids = list(set(re.findall(r'id=([a-zA-Z0-9_-]{25,38})', response.text)))

        photo_list = []
        for fid in file_ids:
            if fid == GOOGLE_DRIVE_FOLDER_ID:
                continue
            
            # ดึงไฟล์รูปภาพและบีบขนาดให้พอดีสำหรับการตรวจจับพิกเซลใบหน้า
            img_url = f"https://docs.google.com/uc?export=download&id={fid}"
            res = requests.get(img_url, timeout=10)
            if res.status_code == 200:
                try:
                    img = Image.open(io.BytesIO(res.content)).convert("RGB")
                    img.thumbnail((600, 600))  # สเกลมาตรฐาน 600px
                    
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=80)
                    b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                    
                    photo_list.append({
                        "id": fid,
                        "base64": f"data:image/jpeg;base64,{b64_str}"
                    })
                except Exception:
                    continue

        return jsonify({"success": True, "count": len(photo_list), "photos": photo_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "photos": []})

@app.route('/api/convert-heic', methods=['POST'])
def convert_heic():
    """แปลงรูปภาพ iPhone (.HEIC) เป็น JPEG สำหรับสแกน"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ไม่พบไฟล์'}), 400
        file = request.files['file']
        image = Image.open(file).convert("RGB")
        image.thumbnail((600, 600))
        
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=80)
        output.seek(0)
        
        encoded_img = base64.b64encode(output.read()).decode('utf-8')
        return jsonify({'base64': f"data:image/jpeg;base64,{encoded_img}"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)