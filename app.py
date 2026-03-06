from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import requests
import os
import tempfile
import re
import urllib.parse

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = tempfile.mkdtemp()

HTML_PAGE = open(os.path.join(os.path.dirname(__file__), "index.html")).read()

# Cobalt API instances - ফ্রি পাবলিক সার্ভার
COBALT_INSTANCES = [
    "https://cobalt.api.timur.lol",
    "https://co.wuk.sh",
    "https://api.cobalt.tools",
]

def cobalt_request(url):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "vQuality": "max",
        "filenameStyle": "pretty",
    }
    for instance in COBALT_INSTANCES:
        try:
            r = requests.post(
                instance,
                json=payload,
                headers=headers,
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("status") in ["stream", "redirect", "tunnel", "picker"]:
                    return data
        except Exception:
            continue
    return None

@app.route("/")
def index():
    return HTML_PAGE

@app.route("/info", methods=["POST"])
def get_info():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "লিংক দিন"}), 400

    result = cobalt_request(url)
    if not result:
        return jsonify({"error": "ভিডিও খুঁজে পাওয়া যায়নি। লিংক চেক করুন।"}), 400

    status = result.get("status")

    # thumbnail বের করার চেষ্টা
    thumbnail = ""
    try:
        if "youtube.com" in url or "youtu.be" in url:
            vid_id = ""
            if "v=" in url:
                vid_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                vid_id = url.split("youtu.be/")[1].split("?")[0]
            if vid_id:
                thumbnail = f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg"
    except:
        pass

    if status == "picker":
        # একাধিক ফাইল (TikTok slideshow ইত্যাদি)
        items = result.get("picker", [])
        formats = []
        for i, item in enumerate(items[:6]):
            formats.append({
                "format_id": item.get("url", ""),
                "quality": f"ফাইল {i+1}",
                "ext": "mp4",
                "size": "?",
                "height": 0,
                "direct_url": item.get("url", ""),
            })
        return jsonify({
            "title": "ভিডিও",
            "thumbnail": thumbnail,
            "duration": "",
            "uploader": "",
            "platform": "",
            "formats": formats,
            "direct": True,
        })
    else:
        direct_url = result.get("url", "")
        filename = result.get("filename", "video.mp4")
        formats = [
            {
                "format_id": "best",
                "quality": "সেরা কোয়ালিটি",
                "ext": filename.split(".")[-1] if "." in filename else "mp4",
                "size": "?",
                "height": 0,
                "direct_url": direct_url,
            }
        ]
        return jsonify({
            "title": filename.rsplit(".", 1)[0] if "." in filename else filename,
            "thumbnail": thumbnail,
            "duration": "",
            "uploader": "",
            "platform": "",
            "formats": formats,
            "direct": True,
            "direct_url": direct_url,
            "filename": filename,
        })


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url", "").strip()
    direct_url = data.get("direct_url", "").strip()
    audio_only = data.get("audio_only", False)

    if not url:
        return jsonify({"error": "লিংক দিন"}), 400

    # Audio only হলে আলাদা cobalt request
    if audio_only:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "url": url,
            "downloadMode": "audio",
            "filenameStyle": "pretty",
        }
        result = None
        for instance in COBALT_INSTANCES:
            try:
                r = requests.post(instance, json=payload, headers=headers, timeout=15)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("status") in ["stream", "redirect", "tunnel"]:
                        result = d
                        break
            except:
                continue
        if result:
            direct_url = result.get("url", "")

    if not direct_url:
        result = cobalt_request(url)
        if not result:
            return jsonify({"error": "ডাউনলোড করা যায়নি।"}), 400
        direct_url = result.get("url", "")

    if not direct_url:
        return jsonify({"error": "ডাউনলোড লিংক পাওয়া যায়নি।"}), 400

    try:
        # Proxy করে পাঠাই
        r = requests.get(direct_url, stream=True, timeout=60, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36"
        })

        content_type = r.headers.get("Content-Type", "video/mp4")
        content_disp = r.headers.get("Content-Disposition", "")

        filename = "video.mp4"
        if audio_only:
            filename = "audio.mp3"
        elif "filename=" in content_disp:
            try:
                filename = content_disp.split("filename=")[1].strip('"').strip("'")
            except:
                pass

        safe_name = re.sub(r'[^\w\s\-.]', '', filename) or "video.mp4"

        def generate():
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        response = Response(
            generate(),
            content_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"',
            }
        )
        return response

    except Exception as e:
        return jsonify({"error": f"ডাউনলোড ব্যর্থ: {str(e)}"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
