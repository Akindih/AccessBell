# app.py — run this on your Pi
from flask import Flask, jsonify, request
from flask_cors import CORS
import os, glob, datetime

app = Flask(__name__)
CORS(app)  # allows your laptop to call the Pi

RECORDINGS_DIR = "/home/pi/recordings"  # adjust to wherever videos are saved

@app.route("/api/recordings")
def get_recordings():
    files = sorted(glob.glob(f"{RECORDINGS_DIR}/*.mp4"), reverse=True)
    recordings = []
    for i, f in enumerate(files):
        mtime = os.path.getmtime(f)
        recordings.append({
            "id": i,
            "filename": os.path.basename(f),
            "timestamp": datetime.datetime.fromtimestamp(mtime).strftime("%d %b %Y, %H:%M"),
        })
    return jsonify(recordings)

@app.route("/api/name-person", methods=["POST"])
def name_person():
    data = request.json
    print(f"Naming person in {data['video_filename']} as {data['name']}")
    # TODO: save to a DB or JSON file, trigger face training, etc.
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
