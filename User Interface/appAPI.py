from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
import os, glob, datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # allows your laptop to call the Pi

RECORDINGS_DIR = "/home/doorbellteam/fce_rec/doorbell_recordings"  # change this to your actual recordings directory

@app.route("/api/recordings")
def get_recordings():
    files = sorted(glob.glob(os.path.join(RECORDINGS_DIR, "*.mp4")), reverse=True)
    recordings = []
    for i, f in enumerate(files):
        mtime = os.path.getmtime(f)
        filename = os.path.basename(f)
        recordings.append({
            "id": i,
            "filename": filename,
            "timestamp": datetime.datetime.fromtimestamp(mtime).strftime("%d %b %Y, %H:%M"),
            "video_url": f"/api/video/{filename}",
        })
    return jsonify(recordings)


@app.route("/api/video/<path:filename>")
def get_video(filename):
    safe_name = secure_filename(filename)
    file_path = os.path.join(RECORDINGS_DIR, safe_name)

    if not os.path.isfile(file_path):
        abort(404)

    return send_from_directory(RECORDINGS_DIR, safe_name, as_attachment=False)

@app.route("/api/name-person", methods=["POST"])
def name_person():
    data = request.json
    print(f"Naming person in {data['video_filename']} as {data['name']}")
    # TODO: save to a DB or JSON file, trigger face training, etc.
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
