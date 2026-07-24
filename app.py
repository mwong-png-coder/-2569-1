import os
import requests
import base64
import io
import re
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_face_app_session'

login_manager = LoginManager()
login_manager.init_app(app)

# บัญชีสำหรับ Admin เท่านั้น
ADMIN_USER = {
    "username": "admin",
    "password": "adminpassword" # เปลี่ยนรหัสผ่านแอดมินได้ตรงนี้ครับ
}

class User(UserMixin):
    def __init__(self, id, role):
        self.id = id
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    if user_id == ADMIN_USER["username"]:
        return User(ADMIN_USER["username"], "admin")
    return None

GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'
UPLOAD_FOLDER = os.path.join('static', 'gallery')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ----------------- Helper Function จัดการไฟล์ภาพ (iPhone HEIC + Rotation) -----------------
def process_image_file(file_obj, max_size=(600, 600)):
    """ช่วยอ่านภาพ ปรับทิศทางตาม EXIF (iPhone) และย่อขนาด"""
    img = Image.open(file_obj)
    img = ImageOps.exif_transpose(img) # แก้ปัญหารูปหมุนตะแคงจาก iPhone
    img = img.convert("RGB")
    img.thumbnail(max_size)
    return img

# ----------------- Auth Routes -----------------

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == ADMIN_USER["username"] and password == ADMIN_USER["password"]:
        user = User(username, "admin")
        login_user(user)
        return jsonify({'success': True, 'message': 'ล็อกอินแอดมินสำเร็จ'})
    else:
        return jsonify({'success': False, 'message': 'ชื่อผู้ใช้หรือรหัสผ่านแอดมินไม่ถูกต้อง'}), 401

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    # เข้าถึงได้ทุกคนโดยไม่ต้องใช้ login_required
    return render_template('index.html')

# ----------------- Photo APIs -----------------

@app.route('/api/photos')
def get_photos():
    photo_list = []
    
    # 1. Google Drive
    try:
        folder_url = f"https://drive.google.com/embeddedfolderview?id={GOOGLE_DRIVE_FOLDER_ID}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(folder_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            raw_ids = re.findall(r'\"id\":\"([a-zA-Z0-9_-]{25,38})\"', res.text)
            if not raw_ids:
                raw_ids = re.findall(r'id=([a-zA-Z0-9_-]{25,38})', res.text)
                
            for fid in list(set(raw_ids)):
                if fid == GOOGLE_DRIVE_FOLDER_ID:
                    continue
                img_url = f"https://docs.google.com/uc?export=download&id={fid}"
                img_res = requests.get(img_url, timeout=8)
                if img_res.status_code == 200:
                    try:
                        img = process_image_file(io.BytesIO(img_res.content), (600, 600))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=80)
                        b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                        photo_list.append({"id": fid, "base64": f"data:image/jpeg;base64,{b64_str}"})
                    except Exception:
                        continue
    except Exception as e:
        print(f"⚠️ Google Drive error: {e}")

    # 2. Local Static Gallery
    if os.path.exists(UPLOAD_FOLDER):
        for fname in os.listdir(UPLOAD_FOLDER):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')):
                fpath = os.path.join(UPLOAD_FOLDER, fname)
                try:
                    img = process_image_file(fpath, (600, 600))
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=80)
                    b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                    photo_list.append({"id": fname, "base64": f"data:image/jpeg;base64,{b64_str}"})
                except Exception:
                    continue

    return jsonify({"success": True, "count": len(photo_list), "photos": photo_list})

@app.route('/api/upload-gallery', methods=['POST'])
@login_required
def upload_gallery():
    """🔒 เฉพาะ Admin เท่านั้นที่อัปโหลดเข้าคลังได้"""
    if not current_user.is_authenticated or getattr(current_user, 'role', '') != 'admin':
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์ใช้งาน! เฉพาะ Admin เท่านั้น'}), 403
        
    try:
        files = request.files.getlist('photos')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': 'ไม่พบไฟล์ที่เลือก'}), 400
        
        saved_count = 0
        for file in files:
            if file:
                img = process_image_file(file, (1024, 1024))
                save_path = os.path.join(UPLOAD_FOLDER, f"gallery_{saved_count}_{os.path.splitext(file.filename)[0]}.jpg")
                img.save(save_path, format="JPEG", quality=85)
                saved_count += 1
                
        return jsonify({'success': True, 'message': f'เพิ่มรูปเข้าคลังสำเร็จ {saved_count} รูป'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@app.route('/api/convert-heic', methods=['POST'])
def convert_heic():
    """📱 รองรับการแปลงไฟล์ HEIC/HEIF จาก iPhone สำหรับสแกนหน้า"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ไม่พบไฟล์'}), 400
        file = request.files['file']
        
        img = process_image_file(file, (800, 800))
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85)
        output.seek(0)
        
        encoded_img = base64.b64encode(output.read()).decode('utf-8')
        return jsonify({'base64': f"data:image/jpeg;base64,{encoded_img}"})
    except Exception as e:
        return jsonify({'error': f'แปลงไฟล์ iPhone ไม่สำเร็จ: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)