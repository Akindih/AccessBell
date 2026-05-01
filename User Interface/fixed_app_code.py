from flask import Flask, jsonify, request, send_from_directory, abort
import os
import glob
import datetime
import psycopg2
import main  # module that exposes current_visitor_profile

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
connection = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    dbname=os.getenv("DB_NAME", "doorbell"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
RECORDINGS_DIR = os.getenv(
    "DOORBELL_RECORDINGS_DIR", "/home/doorbellteam/FaceRec/doorbell_recordings"
)
VIDEO_EXTENSIONS = ("*.mp4", "*.avi", "*.mov", "*.mkv", "*.h264")


def list_recording_files():
    files = []
    for pattern in VIDEO_EXTENSIONS:
        files.extend(glob.glob(os.path.join(RECORDINGS_DIR, pattern)))
    return sorted(files, key=os.path.getmtime, reverse=True)


# ---------------------------------------------------------------------------
# General routes
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Recording routes
# ---------------------------------------------------------------------------
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

    return send_from_directory(RECORDINGS_DIR, safe_name, as_attachment=False)


@app.route("/api/name-person", methods=["POST"])
def name_person():
    data = request.json
    print(f"Naming person in {data['video_filename']} as {data['name']}")
    # TODO: save to a DB or JSON file, trigger face training, etc.
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Visitor analytics routes
# ---------------------------------------------------------------------------
@app.route("/api/visit-frequency", methods=["GET"])
def visit_frequency():
    cursor = connection.cursor()
    cursor.execute("""
        SELECT kp.full_name,
               COUNT(vl.person_id) AS visit_count
        FROM visitor_log vl
        LEFT JOIN known_person kp ON vl.person_id = kp.person_id
        WHERE vl.recognised = TRUE
        GROUP BY kp.full_name
        ORDER BY visit_count DESC;
    """)
    rows = cursor.fetchall()
    cursor.close()

    return jsonify([
        {"name": r[0], "visits": r[1]}
        for r in rows
    ])


@app.route("/api/most-frequent-visitor", methods=["GET"])
def most_frequent_visitor():
    cursor = connection.cursor()
    cursor.execute("""
        SELECT kp.full_name,
               COUNT(vl.person_id) AS visit_count
        FROM visitor_log vl
        LEFT JOIN known_person kp ON vl.person_id = kp.person_id
        WHERE vl.recognised = TRUE
        GROUP BY kp.full_name
        ORDER BY visit_count DESC
        LIMIT 1;
    """)
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return jsonify({"name": None, "visits": 0})

    return jsonify({"name": row[0], "visits": row[1]})


@app.route("/api/recent-visitors", methods=["GET"])
def recent_visitors():
    cursor = connection.cursor()
    cursor.execute("""
        SELECT kp.full_name,
               vl.timestamp,
               vl.confidence
        FROM visitor_log vl
        LEFT JOIN known_person kp ON vl.person_id = kp.person_id
        ORDER BY vl.timestamp DESC
        LIMIT 10;
    """)
    rows = cursor.fetchall()
    cursor.close()

    return jsonify([
        {"name": r[0], "time": r[1], "confidence": float(r[2])}
        for r in rows
    ])


@app.route("/api/visits-over-time", methods=["GET"])
def visits_over_time():
    cursor = connection.cursor()
    cursor.execute("""
        SELECT DATE(timestamp) AS day,
               COUNT(*) AS visits
        FROM visitor_log
        WHERE recognised = TRUE
        GROUP BY day
        ORDER BY day ASC;
    """)
    rows = cursor.fetchall()
    cursor.close()

    return jsonify([
        {"day": str(r[0]), "visits": r[1]}
        for r in rows
    ])


@app.route("/visitor", methods=["GET"])
def get_visitor():
    if main.current_visitor_profile is None:
        return jsonify({"visitor": None})
    return jsonify({"visitor": main.current_visitor_profile})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"RECORDINGS_DIR = {RECORDINGS_DIR}")
    print(f"Dir exists: {os.path.isdir(RECORDINGS_DIR)}")
    print(f"Files found: {list_recording_files()}")
    app.run(host="0.0.0.0", port=5000)