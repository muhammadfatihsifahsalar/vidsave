from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import threading
import time
import re

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = tempfile.mkdtemp()

def clean_old_files():
    """পুরোনো ফাইল মুছে ফেলে (১ ঘন্টার বেশি পুরনো)"""
    while True:
        now = time.time()
        for f in os.listdir(DOWNLOAD_DIR):
            fp = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(fp) and now - os.path.getmtime(fp) > 3600:
                os.remove(fp)
        time.sleep(600)

threading.Thread(target=clean_old_files, daemon=True).start()

HTML_PAGE = open(os.path.join(os.path.dirname(__file__), "index.html")).read()

@app.route("/")
def index():
    return HTML_PAGE

@app.route("/info", methods=["POST"])
def get_info():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "লিংক দিন"}), 400

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])
        video_formats = []
        seen = set()

        for f in formats:
            h = f.get("height")
            ext = f.get("ext", "mp4")
            fid = f.get("format_id")
            if h and h not in seen and f.get("vcodec") != "none":
                seen.add(h)
                size = f.get("filesize") or f.get("filesize_approx") or 0
                video_formats.append({
                    "format_id": fid,
                    "quality": f"{h}p",
                    "ext": ext,
                    "size": format_size(size),
                    "height": h,
                })

        video_formats.sort(key=lambda x: x["height"], reverse=True)

        return jsonify({
            "title": info.get("title", "ভিডিও"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": format_duration(info.get("duration", 0)),
            "uploader": info.get("uploader", ""),
            "platform": info.get("extractor_key", ""),
            "formats": video_formats[:6],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url", "").strip()
    format_id = data.get("format_id", "best")
    audio_only = data.get("audio_only", False)

    if not url:
        return jsonify({"error": "লিংক দিন"}), 400

    out_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    if audio_only:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_path,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
        }
    else:
        ydl_opts = {
            "format": f"{format_id}+bestaudio/best",
            "outtmpl": out_path,
            "merge_output_format": "mp4",
            "quiet": True,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if audio_only:
                filename = os.path.splitext(filename)[0] + ".mp3"

        if not os.path.exists(filename):
            for f in os.listdir(DOWNLOAD_DIR):
                fp = os.path.join(DOWNLOAD_DIR, f)
                if os.path.isfile(fp):
                    filename = fp
                    break

        safe_name = re.sub(r'[^\w\s\-.]', '', os.path.basename(filename))
        return send_file(
            filename,
            as_attachment=True,
            download_name=safe_name,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 400


def format_size(b):
    if not b:
        return "?"
    for u in ["B","KB","MB","GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} GB"


def format_duration(sec):
    if not sec:
        return ""
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
