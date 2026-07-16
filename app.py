import os
import requests
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# 🔗 โฟลเดอร์ ID Google Drive ของนาย (ตรวจสอบให้แน่ใจว่าตั้งค่าแชร์เป็น "ทุกคนที่มีลิงก์มีสิทธิ์อ่าน" แล้ว)
GOOGLE_DRIVE_FOLDER_ID = '1O6e6-XFTMsz6R1MJBHp9ME88HVnhPdb'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    """ดึงเฉพาะ ID และชื่อไฟล์รูปภาพจาก Google Drive ส่งไปให้หน้าบ้านสแกน"""
    try:
        # ดึงรายชื่อไฟล์ในโฟลเดอร์ผ่าน API สาธารณะของ Google Drive
        url = f"https://www.googleapis.com/drive/v3/files?q='{GOOGLE_DRIVE_FOLDER_ID}'+in+parents+and+mimeType+contains+'image/'&fields=files(id,name)&pageSize=1000"
        response = requests.get(url)
        data = response.json()
        
        if 'files' in data:
            # ส่งข้อมูลอาร์เรย์ที่มีโครงสร้าง [{id: "...", name: "..."}, ...] ไปให้หน้าบ้าน
            return jsonify(data['files'])
        print(f"⚠️ Google Drive Response: {data}")
        return jsonify([])
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดหลังบ้าน: {e}")
        return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)