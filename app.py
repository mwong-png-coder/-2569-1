import os
from flask import Flask, render_template, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'photos')

# สร้างโฟลเดอร์ไว้ล่วงหน้าถ้ายังไม่มี
if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    """ดึงรายชื่อไฟล์รูปภาพกิจกรรมในระบบส่งให้หน้าบ้านทำงาน"""
    try:
        if os.path.exists(PHOTOS_DIR):
            valid_extensions = ('.jpg', '.jpeg', '.png')
            # ดึงเฉพาะไฟล์รูปภาพในโฟลเดอร์ static/photos
            photos = [
                f for f in os.listdir(PHOTOS_DIR) 
                if f.lower().endswith(valid_extensions)
            ]
            print(f"📦 จำนวนรูปภาพในคลังที่พร้อมให้ AI สแกน: {len(photos)} รูป")
            return jsonify(photos)
        return jsonify([])
    except Exception as e:
        print(f"❌ Error ในการดึงรูปภาพ: {e}")
        return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)