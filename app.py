from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import re
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'mp3_downloads'

# Pastikan folder 'mp3_downloads' ada. Jika tiada, ia akan buat.
if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
        print(f"Successfully created upload folder: {UPLOAD_FOLDER}")
    except Exception as e:
        print(f"ERROR: Could not create upload folder {UPLOAD_FOLDER}: {e}")
else:
    print(f"Upload folder already exists: {UPLOAD_FOLDER}")

# Fungsi untuk memadam fail selepas respons dihantar ke browser
@app.after_request
def cleanup_files(response):
    if 'x-send-file' in response.headers:
        file_path = response.headers['x-send-file']
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                # print(f"Successfully deleted {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

    for f in os.listdir(UPLOAD_FOLDER):
        file_full_path = os.path.join(UPLOAD_FOLDER, f)
        if os.path.isfile(file_full_path):
            try:
                if (os.path.getmtime(file_full_path) + 300) < time.time():
                    os.remove(file_full_path)
            except Exception as e:
                pass
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_video():
    video_url = request.form['video_url']

    if not video_url:
        return "URL video tidak boleh kosong! Sila masukkan URL.", 400

    unique_id = str(uuid.uuid4())
    output_file_template = os.path.join(UPLOAD_FOLDER, unique_id + '.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'outtmpl': output_file_template,
        'cachedir': False,
        'quiet': True,
        'no_warnings': True,
        # 'ffmpeg_location': r'C:\ffmpeg\ffmpeg-N-120330-g8cdb47e47a-win64-gpl-shared\bin\ffmpeg.exe',
        'no_check_certificates': True,
        'extractor_args': {'youtube': ['--http-chunk-size', '1048576', '--hls-use-mpegts', '--http-chunk-size', '20M']},
        'geo_bypass': True,
        'force_ipv4': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            video_title = info_dict.get('title', 'video_yang_ditukar')

            video_title = re.sub(r'[\\/:*?"<>|]', '', video_title)
            video_title = video_title.replace(' ', '_')
            video_title = video_title.encode('ascii', 'ignore').decode('ascii')

            actual_mp3_file = None
            for f in os.listdir(UPLOAD_FOLDER):
                if f.startswith(unique_id) and f.endswith('.mp3'):
                    actual_mp3_file = os.path.join(UPLOAD_FOLDER, f)
                    break

            if actual_mp3_file and os.path.exists(actual_mp3_file):
                safe_title = "".join([c for c in video_title if c.isalnum() or c in ('-', '_', '.')]).rstrip()
                download_filename = f"{safe_title}.mp3"

                response = send_file(actual_mp3_file, as_attachment=True, download_name=download_filename, mimetype='audio/mpeg')
                response.headers['x-send-file'] = actual_mp3_file
                return response
            else:
                return "Maaf, konversi gagal atau fail MP3 tidak ditemui. Pastikan URL betul.", 500

    except Exception as e:
        return f"Terjadi ralat: {str(e)}. Pastikan URL video betul.", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
