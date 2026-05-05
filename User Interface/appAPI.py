from flask import Flask, jsonify, request, send_from_directory, abort
import os, glob, datetime
import psycopg2

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "database": "smart_doorbell",
    "user": "doorbelldara",
    "password": "doorbell19"
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

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
        return jsonify({"error": "recordings_dir_not_found"}), 500

    conn = None
    try:
        conn = get_db()
        files = list_recording_files()

        with conn.cursor() as cur:
            cur.execute("""
                SELECT kp.full_name, kp.relationship, kp.last_seen,
                       COUNT(vl.log_id) AS visit_count
                FROM known_person kp
                LEFT JOIN visitor_log vl ON kp.person_id = vl.person_id
                GROUP BY kp.full_name, kp.relationship, kp.last_seen
            """)
            people_map = {
                row[0]: {
                    "relationship": row[1] or "Unknown",
                    "last_seen": str(row[2]) if row[2] else None,
                    "visit_count": row[3],
                }
                for row in cur.fetchall()
            }

        recordings = []
        for i, f in enumerate(files):
            mtime = os.path.getmtime(f)
            filename = os.path.basename(f)
            file_time = datetime.datetime.fromtimestamp(mtime)

            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT kp.full_name
                    FROM visitor_log vl
                    JOIN known_person kp ON vl.person_id = kp.person_id
                    WHERE vl.recognised = TRUE
                      AND vl.timestamp BETWEEN %s AND %s
                """, (file_time - datetime.timedelta(seconds=35), file_time + datetime.timedelta(seconds=5)))
                recognised_names = [row[0] for row in cur.fetchall()]

            known_faces = []
            for name in recognised_names:
                info = people_map.get(name, {})
                known_faces.append({
                    "name": name,
                    "relationship": info.get("relationship", "Unknown"),
                    "last_seen": info.get("last_seen"),
                    "visit_count": info.get("visit_count", 0),
                })

            recordings.append({
                "id": i,
                "filename": filename,
                "timestamp": datetime.datetime.fromtimestamp(mtime).strftime("%d %b %Y, %H:%M"),
                "known_faces": known_faces,
                "has_unknown": len(known_faces) == 0,
            })

        return jsonify(recordings)

    except Exception as e:
        print(f"[ERROR] /api/recordings: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


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
    return jsonify({"status": "ok"})


@app.route("/api/visit-frequency", methods=["GET"])
def visit_frequency():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT kp.full_name, COUNT(vl.person_id) AS visit_count
                FROM visitor_log vl
                LEFT JOIN known_person kp ON vl.person_id = kp.person_id
                WHERE vl.recognised = TRUE
                GROUP BY kp.full_name
                ORDER BY visit_count DESC;
            """)
            rows = cur.fetchall()
        return jsonify([{"name": r[0], "visits": r[1]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/most-frequent-visitor", methods=["GET"])
def most_frequent_visitor():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT kp.full_name, COUNT(vl.person_id) AS visit_count
                FROM visitor_log vl
                LEFT JOIN known_person kp ON vl.person_id = kp.person_id
                WHERE vl.recognised = TRUE
                GROUP BY kp.full_name
                ORDER BY visit_count DESC
                LIMIT 1;
            """)
            row = cur.fetchone()
        if not row:
            return jsonify({"name": None, "visits": 0})
        return jsonify({"name": row[0], "visits": row[1]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/recent-visitors", methods=["GET"])
def recent_visitors():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT kp.full_name, vl.timestamp, vl.confidence
                FROM visitor_log vl
                LEFT JOIN known_person kp ON vl.person_id = kp.person_id
                ORDER BY vl.timestamp DESC
                LIMIT 10;
            """)
            rows = cur.fetchall()
        return jsonify([{"name": r[0], "time": str(r[1]), "confidence": float(r[2])} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/visits-over-time", methods=["GET"])
def visits_over_time():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DATE(timestamp) AS day, COUNT(*) AS visits
                FROM visitor_log
                WHERE recognised = TRUE
                GROUP BY day
                ORDER BY day ASC;
            """)
            rows = cur.fetchall()
        return jsonify([{"day": str(r[0]), "visits": r[1]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/known-people", methods=["GET"])
def known_people():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT kp.person_id, kp.full_name, kp.relationship, kp.last_seen,
                       COUNT(vl.log_id) AS visit_count
                FROM known_person kp
                LEFT JOIN visitor_log vl ON kp.person_id = vl.person_id
                GROUP BY kp.person_id, kp.full_name, kp.relationship, kp.last_seen
                ORDER BY kp.last_seen DESC NULLS LAST;
            """)
            rows = cur.fetchall()
        return jsonify([
            {
                "person_id": r[0],
                "name": r[1],
                "relationship": r[2] or "Unknown",
                "last_seen": str(r[3]) if r[3] else None,
                "visit_count": r[4],
            }
            for r in rows
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
