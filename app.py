from flask import Flask, request, jsonify, send_file
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
    while True:
        now = time.time()
        for f in os.listdir(DOWNLOAD_DIR):
            fp = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(fp) and now - os.path.getmtime(fp) > 3600:
                os.remove(fp)
        time.sleep(600)

threading.Thread(target=clean_old_files, daemon=True).start()

HTML_PAGE = open(os.path.join(os.path.dirname(__file__), "index.html")).read()

def get_ydl_opts(extra={}):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "web"],
                "player_skip": ["webpage", "configs"],
            }
        },
        "http_headers": {
            "User-Agent": "com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "socket_timeout": 30,
    }
    opts.update(extra)
    return opts

@app.route("/")
def index():
    return HTML_PAGE

@app.route("/info", methods=["POST"])
def get_info():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "লিংক দিন"}), 400

    ydl_opts = get_ydl_opts({"skip_download": True})

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

        if not video_formats:
            video_formats = [
                {"format_id": "best", "quality": "সেরা কোয়ালিটি", "ext": "mp4", "size": "?", "height": 0},
            ]

        return jsonify({
            "title": info.get("title", "ভিডিও"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": format_duration(info.get("duration", 0)),
            "uploader": info.get("uploader", ""),
            "platform": info.get("extractor_key", ""),
            "formats": video_formats[:6],
        })

    except Exception as e:
        err = str(e)
        # ফ্রেন্ডলি error message
        if "Sign in" in err or "bot" in err:
            return jsonify({"error": "YouTube এই ভিডিওটি ডাউনলোড করতে দিচ্ছে না। অন্য একটি ভিডিও চেষ্টা করুন।"}), 400
        if "Private" in err:
            return jsonify({"error": "এই ভিডিওটি Private, ডাউনলোড করা যাবে না।"}), 400
        return jsonify({"error": f"সমস্যা হয়েছে: {err}"}), 400


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
        extra = {
            "format": "bestaudio/best",
            "outtmpl": out_path,
        }
    else:
        extra = {
            "format": f"{format_id}+bestaudio/best",
            "outtmpl": out_path,
            "merge_output_format": "mp4",
        }

    ydl_opts = get_ydl_opts(extra)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if audio_only:
                base = os.path.splitext(filename)[0]
                for ext in [".m4a", ".webm", ".opus", ".mp3"]:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break

        if not os.path.exists(filename):
            files = sorted(
                [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
                key=os.path.getmtime, reverse=True
            )
            if files:
                filename = files[0]

        safe_name = re.sub(r'[^\w\s\-.]', '', os.path.basename(filename))
        return send_file(filename, as_attachment=True, download_name=safe_name)

    except Exception as e:
        err = str(e)
        if "Sign in" in err or "bot" in err:
            return jsonify({"error": "YouTube এই ভিডিওটি ডাউনলোড করতে দিচ্ছে না।"}), 400
        return jsonify({"error": f"ডাউনলোড ব্যর্থ: {err}"}), 400


def format_size(b):
    if not b:
        return "?"
    for u in ["B", "KB", "MB", "GB"]:
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
