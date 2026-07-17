import os
import requests
import base64
import io
from flask import Flask, render_template, jsonify, request
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

app = Flask(__name__)

# ดึงข้อมูลจากโฟลเดอร์ Google Drive ของนายโดยตรง
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    try:
        # ดึงรายชื่อไฟล์รูปภาพผ่าน Google Drive API แบบสาธารณะ
        # หากต้องการความเสถียรสูงสุด แนะนำให้ตรวจสอบว่าแชร์โฟลเดอร์แบบ "ทุกคนที่มีลิงก์" เรียบร้อยแล้วนะครับนาย
        url = f"https://www.googleapis.com/drive/v3/files?q='{GOOGLE_DRIVE_FOLDER_ID}'+in+parents+and+mimeType+contains+'image/'&fields=files(id,name)&pageSize=50"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ Google Drive API Return Error Code: {response.status_code}")
            return jsonify([])
            
        drive_files = response.json().get('files', [])
        photo_data_list = []
        
        for file in drive_files:
            file_id = file['id']
            # โหลดพิกเซลรูปภาพมาจัดการหลังบ้าน
            download_url = f"https://docs.google.com/uc?export=download&id={file_id}"
            img_resp = requests.get(download_url)
            
            if img_resp.status_code == 200:
                try:
                    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                    # ย่อขนาดรูปภาพให้เหลือสเกล 600px เพื่อให้หน้าบ้านรัน AI สแกนพิกเซลโครงหน้าตรงกัน 100%
                    img.thumbnail((600, 600))
                    
                    output = io.BytesIO()
                    img.save(output, format="JPEG", quality=80)
                    encoded_img = base64.b64encode(output.getvalue()).decode('utf-8')
                    
                    photo_data_list.append({
                        "id": file_id,
                        "name": file['name'],
                        "base64": f"data:image/jpeg;base64,{encoded_img}"
                    })
                    print(f"✔️ โหลดภาพสำเร็จ: {file['name']}")
                except Exception as ex:
                    print(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์ {file['name']}: {ex}")
            else:
                print(f"⚠️ ไม่สามารถดาวน์โหลดไฟล์ ID: {file_id} ได้ (Status: {img_resp.status_code})")
                
        print(f"📸 สรุปผล: ดึงภาพจาก Drive ของนายสำเร็จทั้งหมด {len(photo_data_list)} รูป")
        return jsonify(photo_data_list)
    except Exception as e:
        print(f"❌ พังขณะดึงจาก Drive: {e}")
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