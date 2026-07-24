import os
import requests
import base64
import io
import re
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_face_app_session'

login_manager = LoginManager()
login_manager.init_app(app)

ADMIN_USER = {
    "username": "wongsakorn",
    "password": "acer336"
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

# โครงสร้างโฟลเดอร์ static/gallery/<event_name>/
UPLOAD_FOLDER = os.path.join('static', 'gallery')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_image_file(file_obj, max_size=None):
    """อ่านภาพ แก้ EXIF orientation (iPhone) และย่อขนาดถ้าระบุ max_size"""
    img = Image.open(file_obj)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    if max_size:
        img.thumbnail(max_size)
    return img

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
    return render_template('index.html')

# ----------------- Download API (ส่งไฟล์ต้นฉบับ 100% ตามโฟลเดอร์งาน) -----------------
@app.route('/download/original/<event_folder>/<filename>')
def download_original(event_folder, filename):
    folder_path = os.path.join(UPLOAD_FOLDER, event_folder, 'originals')
    return send_from_directory(folder_path, filename, as_attachment=True)

# ----------------- Photo APIs -----------------
@app.route('/api/photos')
def get_photos():
    photo_list = []
    
    # 1. Google Drive (จัดเป็นงานกลุ่ม Google Drive)
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
                
                original_url = f"https://drive.google.com/uc?export=download&id={fid}"
                img_url = f"https://docs.google.com/uc?export=download&id={fid}"
                
                img_res = requests.get(img_url, timeout=8)
                if img_res.status_code == 200:
                    try:
                        img = process_image_file(io.BytesIO(img_res.content), max_size=(600, 600))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=80)
                        b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                        
                        photo_list.append({
                            "id": fid, 
                            "event_name": "Google Drive Album", # ชื่องานสำหรับภาพ Drive
                            "base64": f"data:image/jpeg;base64,{b64_str}",
                            "download_url": original_url,
                            "is_drive": True
                        })
                    except Exception:
                        continue
    except Exception as e:
        print(f"⚠️ Google Drive error: {e}")

    # 2. Local Gallery แยกตามโฟลเดอร์งาน (Events)
    if os.path.exists(UPLOAD_FOLDER):
        for event_dir in os.listdir(UPLOAD_FOLDER):
            event_path = os.path.join(UPLOAD_FOLDER, event_dir)
            if os.path.isdir(event_path):
                # ดึงชื่อกิจกรรม (แปลงแอดเดอร์สคอร์กลับเป็นช่องว่างเพื่อความสวยงาม)
                event_display_name = event_dir.replace("_", " ")
                scan_folder = os.path.join(event_path, 'scan')
                orig_folder = os.path.join(event_path, 'originals')
                
                if os.path.exists(scan_folder):
                    for fname in os.listdir(scan_folder):
                        if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')):
                            fpath = os.path.join(scan_folder, fname)
                            orig_fname = f"orig_{fname}"
                            
                            try:
                                img = process_image_file(fpath, max_size=(600, 600))
                                buf = io.BytesIO()
                                img.save(buf, format="JPEG", quality=80)
                                b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                                
                                download_link = f"/download/original/{event_dir}/{orig_fname}"
                                
                                photo_list.append({
                                    "id": fname,
                                    "event_name": event_display_name, # ชื่องานกิจกรรม
                                    "base64": f"data:image/jpeg;base64,{b64_str}",
                                    "download_url": download_link,
                                    "is_drive": False
                                })
                            except Exception:
                                continue

    return jsonify({"success": True, "count": len(photo_list), "photos": photo_list})

@app.route('/api/upload-gallery', methods=['POST'])
@login_required
def upload_gallery():
    """🔒 เฉพาะ Admin: รับชื่องานแล้วสร้างโฟลเดอร์เก็บภาพแยกตามงาน"""
    if not current_user.is_authenticated or getattr(current_user, 'role', '') != 'admin':
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์ใช้งาน! เฉพาะ Admin เท่านั้น'}), 403
        
    try:
        event_name = request.form.get('event_name', 'General_Event').strip()
        if not event_name:
            event_name = "General_Event"
            
        # สร้างโฟลเดอร์งานแบบคลีนชื่อ
        safe_event_name = re.sub(r'[^\w\s-]', '', event_name).strip().replace(" ", "_")
        event_path = os.path.join(UPLOAD_FOLDER, safe_event_name)
        scan_folder = os.path.join(event_path, 'scan')
        orig_folder = os.path.join(event_path, 'originals')
        
        os.makedirs(scan_folder, exist_ok=True)
        os.makedirs(orig_folder, exist_ok=True)
        
        files = request.files.getlist('photos')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': 'ไม่พบไฟล์ที่เลือก'}), 400
        
        saved_count = 0
        for file in files:
            if file:
                clean_name = re.sub(r'[^a-zA-Z0-9_\.-]', '_', os.path.splitext(file.filename)[0])
                filename = f"pic_{saved_count}_{clean_name}.jpg"
                orig_filename = f"orig_{filename}"
                
                save_scan_path = os.path.join(scan_folder, filename)
                save_orig_path = os.path.join(orig_folder, orig_filename)
                
                # 1. เซฟไฟล์ต้นฉบับ HD 100%
                orig_img = process_image_file(file, max_size=None)
                orig_img.save(save_orig_path, format="JPEG", quality=100, subsampling=0)
                
                # 2. เซฟไฟล์ย่อสำหรับ AI สแกน
                scan_img = process_image_file(file, max_size=(800, 800))
                scan_img.save(save_scan_path, format="JPEG", quality=80)
                
                saved_count += 1
                
        return jsonify({'success': True, 'message': f'เพิ่มรูปเข้าอัลบั้ม "{event_name}" สำเร็จ {saved_count} รูป'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@app.route('/api/convert-heic', methods=['POST'])
def convert_heic():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ไม่พบไฟล์'}), 400
        file = request.files['file']
        
        img = process_image_file(file, max_size=(800, 800))
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85)
        output.seek(0)
        
        encoded_img = base64.b64encode(output.read()).decode('utf-8')
        return jsonify({'base64': f"data:image/jpeg;base64,{encoded_img}"})
    except Exception as e:
        return jsonify({'error': f'แปลงไฟล์ iPhone ไม่สำเร็จ: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)