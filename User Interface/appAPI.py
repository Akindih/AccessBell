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

@app.route("/api/recordings")from flask import Flask, jsonify, request, send_from_directory, abort
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
        "recordings_dir": RECORDINGS_DI
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


#Frequency per person
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

#most frequent visitor
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

#Recent visitors
@app.route("/api/recent-visitors", methods=["GET"])
def recent_visitors():
    cursor = connection.cursor()
    cursor.execute("""
        SELECT kp.full_name,
               vl.created_at,
               vl.confidence
        FROM visitor_log vl
        LEFT JOIN known_person kp ON vl.person_id = kp.person_id
        ORDER BY vl.created_at DESC
        LIMIT 10;
    """)
    rows = cursor.fetchall()
    cursor.close()

    return jsonify([
        {"name": r[0], "time": r[1], "confidence": float(r[2])}
        for r in rows
    ])

# Visits over time (grouped by date)
@app.route("/api/visits-over-time", methods=["GET"])
def visits_over_time():
    cursor = connection.cursor()
    cursor.execute("""
        SELECT DATE(created_at) AS day,
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

@app.get("/visitor")
def get_visitor():
    if main.current_visitor_profile is None:
        return {"visitor": None}
    return {"visitor": main.current_visitor_profile}

if __name__ == "__main__":
    print(f"RECORDINGS_DIR = {RECORDINGS_DIR}")
    print(f"Dir exists: {os.path.isdir(RECORDINGS_DIR)}")
    print(f"Files found: {list_recording_files()}")
    app.run(host="0.0.0.0", port=5000)                                                                               
