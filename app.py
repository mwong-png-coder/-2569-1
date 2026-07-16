import os
import requests
import base64
import io
from flask import Flask, render_template, jsonify, request
from PIL import Image
from pillow_heif import register_heif_opener

# ลงทะเบียนระบบเปิดไฟล์ iPhone HEIC
register_heif_opener()

app = Flask(__name__)

GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    try:
        url = f"https://www.googleapis.com/drive/v3/files?q='{GOOGLE_DRIVE_FOLDER_ID}'+in+parents+and+mimeType+contains+'image/'&fields=files(id,name)&pageSize=50"
        response = requests.get(url)
        drive_files = response.json().get('files', [])
        
        photo_data_list = []
        for file in drive_files:
            file_id = file['id']
            download_url = f"https://docs.google.com/uc?export=download&id={file_id}"
            img_resp = requests.get(download_url)
            
            if img_resp.status_code == 200:
                encoded_img = base64.b64encode(img_resp.content).decode('utf-8')
                mime_type = "image/jpeg" if file['name'].lower().endswith(('.jpg', '.jpeg')) else "image/png"
                
                photo_data_list.append({
                    "id": file_id,
                    "name": file['name'],
                    "base64": f"data:{mime_type};base64,{encoded_img}"
                })
        return jsonify(photo_data_list)
    except Exception as e:
        return jsonify([])

@app.route('/api/convert-heic', methods=['POST'])
def convert_heic():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        file = request.files['file']
        image = Image.open(file)
        image.thumbnail((1024, 1024)) # บีบภาพเล็กน้อยให้โหลดเร็ว
        
        output = io.BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=85)
        output.seek(0)
        
        encoded_img = base64.b64encode(output.read()).decode('utf-8')
        return jsonify({'base64': f"data:image/jpeg;base64,{encoded_img}"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)