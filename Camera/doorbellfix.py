import face_recognition
import cv2
import numpy as np
import psycopg2
from picamera2 import Picamera2
import time
import RPi.GPIO as GPIO
import pickle
import os
import subprocess
from datetime import datetime

# ── Directories ────────────────────────────────────────────────────────────────
RECORDINGS_DIR = "/home/doorbellteam/FaceRec/doorbell_recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# ── Load encodings from pickle ─────────────────────────────────────────────────
print("[INFO] Loading encodings from pickle...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())
known_face_encodings = data["encodings"]   # used by compare_faces
known_face_names     = data["names"]

# ── GPIO ───────────────────────────────────────────────────────────────────────
BUTTON_PIN = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ── Camera ─────────────────────────────────────────────────────────────────────
FRAME_WIDTH  = 1920
FRAME_HEIGHT = 1080

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (FRAME_WIDTH, FRAME_HEIGHT)}
))
picam2.start()

# ── PostgreSQL ─────────────────────────────────────────────────────────────────
connection = psycopg2.connect(
    host="localhost",
    database="smart_doorbell",
    user="doorbelldara",
    password="doorbell19"
)
cursor = connection.cursor()

# ── Load DB encodings (used for distance matching) ─────────────────────────────
def load_encodings():
    cursor.execute("SELECT person_id, encoding FROM face_encoding;")
    rows = cursor.fetchall()
    known_encodings, known_ids = [], []
    for person_id, binary_encoding in rows:
        enc = np.frombuffer(binary_encoding, dtype=np.float64)
        known_encodings.append(enc)
        known_ids.append(person_id)
    print(f"[INFO] Loaded {len(known_encodings)} encodings from DB.")
    return known_encodings, known_ids

known_encodings, known_ids = load_encodings()

# ── Globals ────────────────────────────────────────────────────────────────────
cv_scaler     = 4
face_locations = []
face_names     = []
frame_count    = 0
start_time     = time.time()
fps            = 0

# ── Helpers ────────────────────────────────────────────────────────────────────
def log_visitor(person_id, recognised, confidence, snapshot=None):
    cursor.execute(
        "INSERT INTO visitor_log (person_id, recognised, confidence, snapshot) "
        "VALUES (%s, %s, %s, %s);",
        (person_id, recognised, confidence, snapshot)
    )
    connection.commit()


def make_web_compatible(video_path, audio_path=None): ##################
    """Re-encode with ffmpeg, merging audio if provided."""
    temp_path = video_path + ".temp.mp4"
    try:
        cmd = ["ffmpeg", "-y", "-i", video_path]
        if audio_path and os.path.exists(audio_path):
            cmd += ["-i", audio_path]
        cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac",
            "-movflags", "+faststart",
            temp_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        os.replace(temp_path, video_path)
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)   # clean up temp wav
        print(f"[INFO] Converted {video_path} to web format.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] ffmpeg failed: {e.stderr.decode()}")
        if os.path.exists(temp_path):
            os.remove(temp_path) ########################



def process_frame(frame):
    """Detect faces, match against DB encodings, log results."""
    global face_locations, face_names

    resized        = cv2.resize(frame, (0, 0), fx=1/cv_scaler, fy=1/cv_scaler)
    rgb_resized    = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)   # face_recognition wants RGB

    face_locations = face_recognition.face_locations(rgb_resized)
    face_encodings = face_recognition.face_encodings(rgb_resized, face_locations, model="large")

    face_names = []

    for face_encoding in face_encodings:
        name       = "Unknown"
        person_id  = None
        recognised = False

        if known_face_encodings:
            # compare_faces and face_distance must use the SAME list
            matches        = face_recognition.compare_faces(known_face_encodings, face_encoding)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_idx       = int(np.argmin(face_distances))

            if matches[best_idx]:
                name       = known_face_names[best_idx]
                recognised = True
                # Map pickle index → DB person_id (lists are same length and order)
                if best_idx < len(known_ids):
                    person_id = known_ids[best_idx]

        confidence = float(1 - face_distances[best_idx]) if known_face_encodings else 0.0
        log_visitor(person_id, recognised, confidence)

        if recognised and person_id is not None:
            cursor.execute(
                "UPDATE known_person SET last_seen = NOW() WHERE person_id = %s;",
                (person_id,)
            )
            connection.commit()

        face_names.append(name)

    return frame


def draw_results(frame):
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top    *= cv_scaler
        right  *= cv_scaler
        bottom *= cv_scaler
        left   *= cv_scaler

        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)
        cv2.rectangle(frame, (left - 3, top - 35), (right + 3, top), (244, 42, 3), cv2.FILLED)
        cv2.putText(frame, name, (left + 6, top - 6),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)
    return frame


def calculate_fps():
    global frame_count, start_time, fps
    frame_count += 1
    elapsed = time.time() - start_time
    if elapsed > 1:
        fps        = frame_count / elapsed
        frame_count = 0
        start_time  = time.time()
    return fps


# ── Main ───────────────────────────────────────────────────────────────────────
RECORDING_SECONDS = 30

print("[INFO] Ready — waiting for button press...")
GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
print("[INFO] Button pressed — opening window and starting recording.")

# Build output filename before the loop
print("[INFO] Ready — waiting for button press...")
GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
print("[INFO] Button pressed — opening window and starting recording.")

# Build output filenames
visitor_name       = "visitor" ###########
recording_filename = os.path.join(
    RECORDINGS_DIR,
    f"{visitor_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
)
audio_filename = recording_filename.replace(".mp4", "_audio.wav")

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out    = cv2.VideoWriter(recording_filename, fourcc, 20.0, (FRAME_WIDTH, FRAME_HEIGHT))

if not out.isOpened():
    print("[ERROR] VideoWriter failed to open — check codec and path.")
else:
    print(f"[INFO] Recording to: {recording_filename}")

# Start audio recording in background
stop_audio   = threading.Event()
audio_thread = threading.Thread(
    target=record_audio,
    args=(audio_filename, RECORDING_SECONDS, stop_audio),
    daemon=True
)
audio_thread.start()

recording_end_time = time.time() + RECORDING_SECONDS ####

while True:
    frame = picam2.capture_array()
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    processed_frame = process_frame(frame)
    display_frame   = draw_results(processed_frame)

    # Update visitor name from first recognised face (for logging context)
    if face_names and face_names[0] != "Unknown":
        visitor_name = face_names[0]

    current_fps = calculate_fps()
    cv2.putText(display_frame, f"FPS: {current_fps:.1f}",
                (display_frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    remaining = max(0, recording_end_time - time.time())
    cv2.putText(display_frame, f"REC {remaining:.0f}s",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Doorbell", display_frame)
    cv2.waitKey(1)

    if out and out.isOpened():
        out.write(display_frame)

    # Stop after 30 seconds
    if time.time() >= recording_end_time:
        print("[INFO] Recording complete.")
        break

# ── Cleanup ────────────────────────────────────────────────────────────────────
out.release()
cv2.destroyAllWindows()
picam2.stop()
cursor.close()
connection.close()
GPIO.cleanup()

print("[INFO] Converting video for web streaming...")
make_web_compatible(recording_filename)
print(f"[INFO] Saved: {recording_filename}")
