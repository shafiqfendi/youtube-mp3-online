from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import re
import time # Penting: Pastikan ini diimport untuk fungsi pemadaman fail
from werkzeug.utils import secure_filename # Untuk nama fail yang selamat

app = Flask(__name__)
UPLOAD_FOLDER = 'mp3_downloads' # Folder untuk menyimpan fail sementara

# Pastikan folder 'mp3_downloads' ada. Jika tiada, ia akan buat.
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Fungsi untuk memadam fail selepas respons dihantar ke browser
@app.after_request
def cleanup_files(response):
    # Jika respons mengandungi header x-send-file (fail yang dihantar)
    if 'x-send-file' in response.headers:
        file_path = response.headers['x-send-file']
        # Pastikan fail wujud sebelum cuba padam
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                # print(f"Successfully deleted {file_path}") # Boleh aktifkan untuk debugging
            except Exception as e:
                # Jika ada ralat semasa padam (cth: fail masih digunakan), cetak ralat
                print(f"Error deleting file {file_path}: {e}")

    # Ini adalah untuk membersihkan fail-fail lama yang mungkin tertinggal
    # dari cubaan sebelum ini yang gagal dipadamkan
    for f in os.listdir(UPLOAD_FOLDER):
        file_full_path = os.path.join(UPLOAD_FOLDER, f)
        # Pastikan ia adalah fail (bukan folder)
        if os.path.isfile(file_full_path):
            try:
                # Padam fail yang lebih lama dari 5 minit (300 saat)
                if (os.path.getmtime(file_full_path) + 300) < time.time():
                    os.remove(file_full_path)
            except Exception as e:
                # Abaikan ralat jika fail sedang digunakan oleh proses lain
                pass
    return response

@app.route('/')
def index():
    # Laman utama yang ada borang untuk masukkan URL
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_video():
    video_url = request.form['video_url'] # Ambil URL dari borang input

    if not video_url:
        return "URL video tidak boleh kosong! Sila masukkan URL.", 400

    # Hasilkan nama fail unik untuk setiap konversi, supaya tak bertindih
    unique_id = str(uuid.uuid4())
    # Tentukan laluan lengkap untuk fail audio sementara yang akan disimpan
    # yt-dlp akan muat turun dalam format asalnya (cth: .webm) sebelum tukar ke MP3
    output_file_template = os.path.join(UPLOAD_FOLDER, unique_id + '.%(ext)s')

    # Opsyen untuk yt-dlp: muat turun audio terbaik dan tukar ke MP3
    ydl_opts = {
        'format': 'bestaudio/best', # Pilih format audio terbaik
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',       # Tukar ke format MP3
            'preferredquality': '0',        # Kualiti terbaik yang tersedia
        }],
        'outtmpl': output_file_template, # Laluan untuk simpan fail sementara
        'cachedir': False,               # Jangan guna cache yt-dlp
        'quiet': True,                   # Jangan tunjuk output di konsol (boleh komenkan untuk debugging)
        'no_warnings': True,             # Sembunyikan amaran (boleh komenkan untuk debugging)
        # 'ffmpeg_location': r'C:\ffmpeg\ffmpeg-N-120330-g8cdb47e47a-win64-gpl-shared\bin\ffmpeg.exe', # Komenkan ini untuk deployment online
        'no_check_certificates': True,   # Cuba elak masalah sijil SSL
        'extractor_args': {'youtube': ['--http-chunk-size', '1048576', '--hls-use-mpegts', '--http-chunk-size', '20M']}, # Strategi muat turun berbeza
    }

    try:
        # Muat turun dan tukar video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            video_title = info_dict.get('title', 'video_yang_ditukar')

            # Bersihkan tajuk video untuk nama fail yang selamat
            video_title = re.sub(r'[\\/:*?"<>|]', '', video_title)
            video_title = video_title.replace(' ', '_')
            video_title = video_title.encode('ascii', 'ignore').decode('ascii')

            # Cari fail MP3 yang sebenar selepas konversi
            actual_mp3_file = None
            for f in os.listdir(UPLOAD_FOLDER):
                if f.startswith(unique_id) and f.endswith('.mp3'): # Cari fail .mp3
                    actual_mp3_file = os.path.join(UPLOAD_FOLDER, f)
                    break

            if actual_mp3_file and os.path.exists(actual_mp3_file):
                # Bersihkan tajuk video untuk nama fail yang sangat selamat
                safe_title = "".join([c for c in video_title if c.isalnum() or c in ('-', '_', '.')]).rstrip()
                download_filename = f"{safe_title}.mp3" # Pastikan ekstensi sesuai dengan format MP3

                # Hantar fail MP3 kepada pengguna untuk dimuat turun
                response = send_file(actual_mp3_file, as_attachment=True, download_name=download_filename, mimetype='audio/mpeg')
                # Beritahu fungsi after_request fail mana yang perlu dipadam
                response.headers['x-send-file'] = actual_mp3_file
                return response
            else:
                return "Maaf, konversi gagal atau fail MP3 tidak ditemui. Pastikan URL betul.", 500

    except Exception as e:
        # Tangani sebarang ralat yang mungkin berlaku
        return f"Terjadi ralat: {str(e)}. Pastikan URL video betul.", 500

# Jalankan aplikasi Flask
if __name__ == '__main__':
    # Untuk deployment online (Render.com), gunakan host dan port dari environment variables
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))