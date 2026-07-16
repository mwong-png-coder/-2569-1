import os
import requests
import base64
from flask import Flask, render_template, jsonify

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
        print(f"❌ Error: {e}")
        return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)