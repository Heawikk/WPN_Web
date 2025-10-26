import asyncio
from flask import Flask, jsonify, render_template_string
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
from winsdk.windows.storage.streams import DataReader
import io
from PIL import Image
import base64

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {
  background: transparent;
  color: white;
  font-family: "Segoe UI", sans-serif;
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
}
img {
  width: 100px;
  height: 100px;
  border-radius: 12px;
  object-fit: cover;
}
.info { flex: 1; }
.title { font-size: 20px; font-weight: bold; }
.artist { font-size: 16px; opacity: 0.8; }
.bar {
  height: 8px;
  background: rgba(255,255,255,0.2);
  border-radius: 5px;
  margin-top: 8px;
  overflow: hidden;
}
.progress {
  height: 100%;
  background: linear-gradient(90deg, #ff0080, #ffcc00);
  width: 0%;
  transition: width 0.5s linear;
}
</style>
</head>
<body>
  <img id="cover" src="">
  <div class="info">
    <div class="title" id="title">—</div>
    <div class="artist" id="artist">—</div>
  </div>
<script>
async function update() {
  try {
    const res = await fetch('/api');
    const d = await res.json();
    if (d.error) return;
    document.getElementById('title').textContent = d.title || 'Unkown';
    document.getElementById('artist').textContent = d.artist || '';
    if (d.cover) document.getElementById('cover').src = d.cover;
    const p = Math.min(100, (d.position / d.duration) * 100);
    document.getElementById('progress').style.width = p + '%';
  } catch (e) {}
}
setInterval(update, 1000);
update();
</script>
</body>
</html>
"""

async def get_media_info():
    try:
        manager = await MediaManager.request_async()
        session = manager.get_current_session()
        if not session:
            return {"error": "No active player"}
        info = await session.try_get_media_properties_async()
        title = info.title
        artist = info.artist
        stream_ref = info.thumbnail
        cover_b64 = None
        if stream_ref:
            stream = await stream_ref.open_read_async()
            size = stream.size
            reader = DataReader(stream)
            await reader.load_async(size)
            buf = reader.read_buffer(size)
            img_bytes = bytes(buf)
            cover_b64 = "data:image/png;base64," + base64.b64encode(img_bytes).decode()
        timeline = session.get_timeline_properties()
        pos = timeline.position.total_seconds()
        dur = timeline.end_time.total_seconds()
        return {
            "title": title,
            "artist": artist,
            "cover": cover_b64,
            "position": pos,
            "duration": dur
        }
    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api")
def api():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(get_media_info())
    return jsonify(data)

if __name__ == "__main__":
    app.run(port=9050)
