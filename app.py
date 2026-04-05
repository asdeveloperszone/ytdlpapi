from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import re

app = Flask(__name__)
CORS(app)

def extract_video_id(url):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "yt-dlp API running"})

@app.route('/api/download')
def download():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'best[height<=360][ext=mp4]/best[height<=360]/best[ext=mp4]/best',
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb'],
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title":       info.get('title', 'video'),
            "author":      info.get('uploader', 'Unknown'),
            "duration":    info.get('duration', 0),
            "thumbnail":   info.get('thumbnail', f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'),
            "videoId":     video_id,
            "downloadUrl": info.get('url', ''),
            "quality":     f"{info.get('height', 360)}p",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
