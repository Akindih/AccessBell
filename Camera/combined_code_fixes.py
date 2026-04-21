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
import atexit
from datetime import datetime

# Directory where recordings are saved (must match appAPI.py)
RECORDINGS_DIR = "/home/doorbellteam/FaceRec/doorbell_recordings"
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

# Load pre-trained face encodings
print("[INFO] loading encodings...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())
known_face_encodings = data["encodings"]
known_face_names = data["names"]

# GPIO setup
BUTTON_PIN = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
atexit.register(GPIO.cleanup)

# Initialize the camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1920, 1080)}))
picam2.start()

# Initialize our variables
cv_scaler = 4

face_locations = []
face_encodings = []
face_names = []
frame_count = 0
start_time = time.time()
fps = 0
frame_width = 1920
frame_height = 1080

# PostgreSQL connection
connection = psycopg2.connect(
    host="localhost",
    database="smart_doorbell",
    user="doorbelldara",
    password="doorbell19"
)
cursor = connection.cursor()


def create_folder(name):
    dataset_folder = "dataset"
    if not os.path.exists(dataset_folder):
        os.makedirs(dataset_folder)
    person_folder = os.path.join(dataset_folder, name)
    if not os.path.exists(person_folder):
        os.makedirs(person_folder)
    return person_folder


# Load encodings from PostgreSQL
def load_encodings():
    cursor.execute("""
        SELECT person_id, encoding
        FROM face_encoding;
    """)
    rows = cursor.fetchall()

    known_encodings = []
    known_ids = []

    for person_id, binary_encoding in rows:
        enc = np.frombuffer(binary_encoding, dtype=np.float64)
        known_encodings.append(enc)
        known_ids.append(person_id)
    print(f"Loaded {len(known_encodings)} encodings from DB.")
    return known_encodings, known_ids


known_encodings, known_ids = load_encodings()
print(f"Loaded {len(known_encodings)} face encodings from database.")


# Cooldown tracker to prevent flooding visitor_log
last_logged = {}


# Log visitor into visitor_log table
def log_visitor(person_id, recognised, confidence, name="Unknown", snapshot=None):
    now = time.time()
    key = person_id or "unknown"
    if key in last_logged and now - last_logged[key] < 30:
        return
    last_logged[key] = now

    cursor.execute("""
        INSERT INTO visitor_log (person_id, recognised, confidence, snapshot)
        VALUES (%s, %s, %s, %s);
    """, (person_id, recognised, confidence, snapshot))
    connection.commit()


def make_web_compatible(video_path):
    """Convert video to web-streaming format using ffmpeg"""
    temp_path = video_path + ".temp.mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-movflags", "+faststart",
            temp_path
        ], check=True, capture_output=True)
        os.replace(temp_path, video_path)
        print(f"Converted {video_path} to web format")
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg error: {e.stderr.decode()}")
        if os.path.exists(temp_path):
            os.remove(temp_path)


print("Waiting for button press to start recognition...")
GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
print("Button pressed, Starting live recognition.")


def process_frame(frame):
    global face_locations, face_encodings, face_names

    resized_frame = cv2.resize(frame, (0, 0), fx=(1 / cv_scaler), fy=(1 / cv_scaler))
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')

    face_names = []

    for face_encoding in face_encodings:
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        recognised = face_distances[best_match_index] < 0.6
        name = known_face_names[best_match_index] if recognised else "Unknown"
        person_id = known_ids[best_match_index] if recognised else None

        confidence = 1 - face_distances[best_match_index]

        log_visitor(person_id, recognised, float(confidence), name=name)

        if recognised and person_id is not None:
            cursor.execute("""
                UPDATE known_person
                SET last_seen = NOW()
                WHERE person_id = %s;
            """, (person_id,))
            connection.commit()

        face_names.append(name)

    return frame


def draw_results(frame):
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler

        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)
        cv2.rectangle(frame, (left - 3, top - 35), (right + 3, top), (244, 42, 3), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, top - 6), font, 1.0, (255, 255, 255), 1)

    return frame


def calculate_fps():
    global frame_count, start_time, fps
    frame_count += 1
    elapsed_time = time.time() - start_time
    if elapsed_time > 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = time.time()
    return fps


recording = False
out = None
recording_end_time = None
recording_filename = None
visitor_name = None

while True:
    frame = picam2.capture_array()

    # ADDED: print frame shape on first frame to confirm dimensions
    if frame_count == 0:
        print(f"Frame shape: {frame.shape}")

    processed_frame = process_frame(frame)
    display_frame = draw_results(processed_frame)

    current_fps = calculate_fps()
    cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (display_frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # If recording, write frame and check if 15 seconds is up
    if recording:
        bgr_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGRA2BGR)
        out.write(bgr_frame)
        print(f"Recording... {int(recording_end_time - time.time())}s remaining")
        if time.time() >= recording_end_time:
            out.release()
            out = None
            print(f"Recording finished. Converting to web format...")
            make_web_compatible(recording_filename)
            print(f"Video saved to: {recording_filename}")
            recording = False

    cv2.imshow('Video', display_frame)

    # Button press starts a 15 second recording
    if not recording and GPIO.input(BUTTON_PIN) == 0:
        visitor_name = face_names[0] if face_names else "unknown"
        recording_filename = os.path.join(
            RECORDINGS_DIR, f"{visitor_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # ADDED: convert frame to BGR first to get correct dimensions
        test_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        h, w = test_bgr.shape[:2]
        print(f"Starting recording at {w}x{h}")

        out = cv2.VideoWriter(recording_filename, fourcc, 20.0, (w, h))
        recording = True
        recording_end_time = time.time() + 15
        print(f"Started recording to {recording_filename}")
        time.sleep(0.5)

    if cv2.waitKey(1) == ord("q"):
        if recording and out:
            out.release()
            make_web_compatible(recording_filename)
        break

# Cleanup
cv2.destroyAllWindows()
picam2.stop()
cursor.close()
connection.close()
