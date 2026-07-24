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

# โฟลเดอร์สำหรับเก็บคลังรูปภาพในเซิร์ฟเวอร์
UPLOAD_FOLDER = os.path.join('static', 'gallery')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    """ดึงรูปภาพทั้งหมดที่มีอยู่ในคลังมาประมวลผล"""
    photo_list = []
    
    # 1. ดึงภาพจากโฟลเดอร์คลังภาพที่อัปโหลดไว้ในเซิร์ฟเวอร์
    if os.path.exists(UPLOAD_FOLDER):
        for fname in os.listdir(UPLOAD_FOLDER):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')):
                fpath = os.path.join(UPLOAD_FOLDER, fname)
                try:
                    img = Image.open(fpath).convert("RGB")
                    img.thumbnail((600, 600))
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=80)
                    b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                    photo_list.append({
                        "id": fname,
                        "base64": f"data:image/jpeg;base64,{b64_str}"
                    })
                except Exception:
                    continue

    return jsonify({"success": True, "count": len(photo_list), "photos": photo_list})

@app.route('/api/upload-gallery', methods=['POST'])
def upload_gallery():
    """API สำหรับใส่อัปโหลดรูปภาพใหม่ๆ เข้าไปในคลังภาพ"""
    try:
        files = request.files.getlist('photos')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': 'ไม่พบไฟล์ที่เลือก'}), 400
        
        saved_count = 0
        for file in files:
            if file:
                img = Image.open(file).convert("RGB")
                img.thumbnail((1024, 1024))  # บีบขนาดไฟล์เพื่อไม่ให้กินพื้นที่ดิสก์
                
                # บันทึกลงโฟลเดอร์ static/gallery
                save_path = os.path.join(UPLOAD_FOLDER, f"gallery_{saved_count}_{file.filename}.jpg")
                img.save(save_path, format="JPEG", quality=85)
                saved_count += 1
                
        return jsonify({'success': True, 'message': f'เพิ่มรูปเข้าคลังสำเร็จ {saved_count} รูป'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)