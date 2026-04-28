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
import pyaudio
import wave
import threading
from queue import Queue

# -- Settings --
RECORDINGS_DIR = "/home/doorbellteam/FaceRec/doorbell_recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)
BUTTON_PIN = 26
FRAME_WIDTH, FRAME_HEIGHT = 1920, 1080
RECORDING_SECONDS = 30
CV_SCALER = 4  # Scale down for faster recognition
PROCESS_EVERY_N_FRAME = 5 # Only run recognition every 5th frame

# -- Database & Encodings --
print("[INFO] Loading resources...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())
known_face_encodings = data["encodings"]
known_face_names = data["names"]

connection = psycopg2.connect(host="localhost", database="smart_doorbell", user="doorbelldara", password="doorbell19")
cursor = connection.cursor()

def load_db_ids():
    cursor.execute("SELECT person_id, encoding FROM face_encoding;")
    return {i: row[0] for i, row in enumerate(cursor.fetchall())}
known_ids_map = load_db_ids()

# -- Global State for Threading --
recognition_results = {"names": [], "locations": []}
last_logged_names = set() # Session-based cooldown

# -- Logic Functions --
def recognition_worker(frame_queue, stop_event):
    """Background thread to handle heavy CPU face recognition."""
    global recognition_results
    frame_count = 0
    
    while not stop_event.is_set():
        if not frame_queue.empty():
            frame = frame_queue.get()
            frame_count += 1
            
            # Only process every Nth frame to save CPU
            if frame_count % PROCESS_EVERY_N_FRAME != 0:
                continue

            # Resize and convert for recognition
            small_frame = cv2.resize(frame, (0, 0), fx=1/CV_SCALER, fy=1/CV_SCALER)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small)
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
            
            names = []
            for encoding in face_encodings:
                name = "Unknown"
                if known_face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, encoding)
                    face_distances = face_recognition.face_distance(known_face_encodings, encoding)
                    best_idx = np.argmin(face_distances)
                    if matches[best_idx]:
                        name = known_face_names[best_idx]
                        # Database logging (Once per name per session)
                        if name not in last_logged_names:
                            log_to_db(name, best_idx, float(1 - face_distances[best_idx]))
                            last_logged_names.add(name)
                names.append(name)
            
            recognition_results = {"names": names, "locations": face_locations}

def log_to_db(name, idx, confidence):
    try:
        person_id = known_ids_map.get(idx)
        cursor.execute(
            "INSERT INTO visitor_log (person_id, recognised, confidence) VALUES (%s, %s, %s);",
            (person_id, True, confidence)
        )
        if person_id:
            cursor.execute("UPDATE known_person SET last_seen = NOW() WHERE person_id = %s;", (person_id,))
        connection.commit()
        print(f"[DB] Logged: {name}")
    except Exception as e:
        print(f"[ERROR] DB Log failed: {e}")

def record_audio(output_path, stop_event):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
    frames = []
    while not stop_event.is_set():
        frames.append(stream.read(1024, exception_on_overflow=False))
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsamplewidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b"".join(frames))

# -- Camera Setup --
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (FRAME_WIDTH, FRAME_HEIGHT)})
picam2.configure(config)
picam2.start()

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- Main Loop ---
try:
    while True:
        print("[INFO] Waiting for button press...")
        GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
        
        last_logged_names.clear()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        raw_vid = os.path.join(RECORDINGS_DIR, f"raw_{timestamp}.avi")
        raw_aud = os.path.join(RECORDINGS_DIR, f"audio_{timestamp}.wav")
        final_out = os.path.join(RECORDINGS_DIR, f"visitor_{timestamp}.mp4")

        # VideoWriter at a fixed 20 FPS
        out = cv2.VideoWriter(raw_vid, cv2.VideoWriter_fourcc(*"XVID"), 20.0, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # Threading Events
        stop_event = threading.Event()
        frame_queue = Queue(maxsize=10)
        
        # Start Threads
        rec_thread = threading.Thread(target=recognition_worker, args=(frame_queue, stop_event))
        aud_thread = threading.Thread(target=record_audio, args=(raw_aud, stop_event))
        rec_thread.start()
        aud_thread.start()

        print("[INFO] Recording started...")
        end_time = time.time() + RECORDING_SECONDS
        frames_captured = 0
        loop_start = time.time()

        while time.time() < end_time:
            frame = picam2.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Send to recognition worker if queue isn't full
            if not frame_queue.full():
                frame_queue.put(frame.copy())

            # Draw boxes (using the most recent background results)
            res = recognition_results
            for (top, right, bottom, left), name in zip(res["locations"], res["names"]):
                top, right, bottom, left = [v * CV_SCALER for v in [top, right, bottom, left]]
                cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            out.write(frame)
            frames_captured += 1
            
            cv2.imshow("Doorbell", cv2.resize(frame, (960, 540))) # Preview at half size
            if cv2.waitKey(1) & 0xFF == ord('q'): break

        # Calculate actual FPS for FFmpeg re-encoding
        actual_fps = frames_captured / (time.time() - loop_start)
        print(f"[INFO] Finished. Actual Capture FPS: {actual_fps:.2f}")

        # Cleanup Session
        stop_event.set()
        rec_thread.join()
        aud_thread.join()
        out.release()
        cv2.destroyAllWindows()

        # Merge with FFmpeg using ACTUAL FPS
        print("[INFO] Merging and re-encoding...")
        subprocess.run([
            "ffmpeg", "-y", "-r", str(actual_fps), "-i", raw_vid, "-i", raw_aud,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25", "-c:a", "aac",
            "-movflags", "+faststart", "-shortest", final_out
        ], capture_output=True)
        
        os.remove(raw_vid)
        os.remove(raw_aud)
        print(f"[SUCCESS] Saved: {final_out}")

except KeyboardInterrupt:
    print("\n[EXIT] Cleaning up...")
finally:
    picam2.stop()
    GPIO.cleanup()
    cursor.close()
    connection.close()
