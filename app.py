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

YDL_BASE_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['mweb'],
        }
    },
}

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "yt-dlp API running"})

@app.route('/api/info')
def info():
    """Get video info + available formats"""
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    ydl_opts = {**YDL_BASE_OPTS, 'format': 'best'}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Build a clean list of available formats
        formats = []
        seen = set()
        for f in info.get('formats', []):
            height = f.get('height')
            ext = f.get('ext', 'mp4')
            has_audio = f.get('acodec', 'none') != 'none'
            has_video = f.get('vcodec', 'none') != 'none'

            if not has_video or not height:
                continue

            label = f"{height}p"
            key = f"{label}-{ext}-{has_audio}"
            if key in seen:
                continue
            seen.add(key)

            formats.append({
                'itag': f.get('format_id'),
                'label': label,
                'ext': ext,
                'hasAudio': has_audio,
                'filesize': f.get('filesize') or f.get('filesize_approx'),
            })

        # Sort by resolution descending
        formats.sort(key=lambda x: int(x['label'].replace('p','')), reverse=True)

        return jsonify({
            "title":     info.get('title', 'video'),
            "author":    info.get('uploader', 'Unknown'),
            "duration":  info.get('duration', 0),
            "thumbnail": info.get('thumbnail', f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'),
            "videoId":   video_id,
            "formats":   formats,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/download')
def download():
    """Get direct download URL for a specific format"""
    url = request.args.get('url', '').strip()
    itag = request.args.get('itag', '').strip()

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    fmt = itag if itag else 'best[height<=360]/bestvideo[height<=360]+bestaudio/best'

    ydl_opts = {**YDL_BASE_OPTS, 'format': fmt}

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
            "quality":     f"{info.get('height', '?')}p",
            "ext":         info.get('ext', 'mp4'),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
