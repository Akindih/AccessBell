from flask import Flask, jsonify, request, send_from_directory, abort
import os, glob, datetime

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

RECORDINGS_DIR = os.getenv("DOORBELL_RECORDINGS_DIR", "/home/doorbellteam/FaceRec/doorbell_recordings")
VIDEO_EXTENSIONS = ("*.mp4", "*.avi", "*.mov", "*.mkv", "*.h264")


def list_recording_files():
    files = []
    for pattern in VIDEO_EXTENSIONS:
        files.extend(glob.glob(os.path.join(RECORDINGS_DIR, pattern)))
    return sorted(files, key=os.path.getmtime, reverse=True)


@app.route("/")
def root():
    return jsonify({
        "ok": True,
        "message": "Doorbell API is running",
        "recordings_dir": RECORDINGS_DIR,
        "routes": ["/api/recordings", "/api/video/<filename>", "/api/health"],
    })


@app.route("/api/health")
def health():
    files = list_recording_files()
    return jsonify({
        "ok": True,
        "recordings_dir": RECORDINGS_DIR,
        "dir_exists": os.path.isdir(RECORDINGS_DIR),
        "recording_count": len(files),
        "latest_recording": os.path.basename(files[0]) if files else None,
    })

@app.route("/api/recordings")
def get_recordings():
    if not os.path.isdir(RECORDINGS_DIR):
        return jsonify({
            "error": "recordings_dir_not_found",
            "recordings_dir": RECORDINGS_DIR,
        }), 500

    files = list_recording_files()
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
    safe_name = os.path.basename(filename)
    file_path = os.path.join(RECORDINGS_DIR, safe_name)

    if not os.path.isfile(file_path):
        abort(404)

    return send_from_directory(RECORDINGS_DIR, safe_name, as_attachment=False, conditional=True)

@app.route("/api/name-person", methods=["POST"])
def name_person():
    data = request.json
    print(f"Naming person in {data['video_filename']} as {data['name']}")
    # TODO: save to a DB or JSON file, trigger face training, etc.
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
