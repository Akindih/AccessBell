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
from itertools import count

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

# Add GPIO setup and needed libraries
BUTTON_PIN = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize the camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1920, 1080)}))
#picam2.configure(config)
picam2.start()

# Initialize our variables
cv_scaler = 4  # this has to be a whole number

face_locations = []
face_encodings = []
face_names = []
frame_count = 0
start_time = time.time()
fps = 0

# PostgreSQL connection
connection = psycopg2.connect(
    host="localhost",
    database="smart_doorbell",
    user="doorbelldara",
    password="doorbell19"
)
cursor = connection.cursor()

# Insert person into DB
def insert_person(full_name, relationship=None):
    cursor.execute("""
        INSERT INTO known_person (full_name, relationship)
        VALUES (%s, %s)
        RETURNING person_id;
    """, (full_name, relationship))

    person_id = cursor.fetchone()[0]
    connection.commit()
    return person_id


# Insert encoding into DB
def insert_encoding(person_id, encoding):
    binary_encoding = encoding.tobytes()

    cursor.execute("""
        INSERT INTO face_encoding (person_id, encoding)
        VALUES (%s, %s);
    """, (person_id, binary_encoding))

    connection.commit()



# Process one person's folder
def process_person_folder(PERSON_NAME, folder_path):
    print(f"\nProcessing: {PERSON_NAME}")

    encodings = []

    for filename in os.listdir(folder_path):
        image_path = os.path.join(folder_path, filename)

        image = cv2.imread(image_path)

        if image is None:
            print(f"Skipping unreadable file: {filename}")
            continue

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect face
        boxes = face_recognition.face_locations(rgb)

        if len(boxes) == 0:
            print(f"No face found in: {filename}")
            continue

        encoding = face_recognition.face_encodings(rgb, boxes)[0]
        encodings.append(encoding)

    if len(encodings) == 0:
        print(f"No usable images for {PERSON_NAME}")
        return

    # Insert person into DB
    person_id = insert_person(PERSON_NAME)

    # Insert encodings
    for enc in encodings:
        insert_encoding(person_id, enc)

    print(f"Added {len(encodings)} encodings for {PERSON_NAME} (person_id={person_id})")



# Dataset directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

if not os.path.isdir(DATASET_DIR):
    print(f"Dataset folder not found at `{DATASET_DIR}`")
    print(f"Current working directory: `{os.getcwd()}`")
    raise SystemExit(1)


# Loop through dataset folders
for PERSON_NAME in os.listdir(DATASET_DIR):
    folder_path = os.path.join(DATASET_DIR, PERSON_NAME)

    if os.path.isdir(folder_path):
        process_person_folder(PERSON_NAME, folder_path)


def create_folder(name):
    dataset_folder = "dataset"
    if not os.path.exists(dataset_folder):
        os.makedirs(dataset_folder)

    person_folder = os.path.join(dataset_folder, name)
    if not os.path.exists(person_folder):
        os.makedirs(person_folder)
    return person_folder


def capture_video(name):
    folder = create_folder(name)


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



# Log visitor into visitor_log table
def log_visitor(person_id, recognised, confidence, snapshot=None):
    cursor.execute("""
        INSERT INTO visitor_log (person_id, recognised, confidence, snapshot)
        VALUES (%s, %s, %s, %s);
    """, (person_id, recognised, confidence, snapshot))
    connection.commit()

    # Create video filename with timestamp in recordings folder
    filename = os.path.join(
        RECORDINGS_DIR, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    )

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(filename, fourcc, 20.0, (frame_width, frame_height))


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


print("Waiting for button press to start photo capture...")
# wait for button press
GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
print("Button pressed, Starting live recognition.")


def process_frame(frame):
    global face_locations, face_encodings, face_names

    # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
    resized_frame = cv2.resize(frame, (0, 0), fx=(1 / cv_scaler), fy=(1 / cv_scaler))

    # Convert the image from BGR to RGB colour space, the facial recognition library uses RGB, OpenCV uses BGR
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')

    face_names = []
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
        face_names.append(name)

    return frame


def draw_results(frame):
    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)

        # Draw a label with a name below the face
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
visitor_name = None

while True:
    # Capture a frame from camera
    frame = picam2.capture_array()

    # Process the frame with the function
    processed_frame = process_frame(frame)

    # Get the text and boxes to be drawn based on the processed frame
    display_frame = draw_results(processed_frame)

    # Calculate and update FPS
    current_fps = calculate_fps()

    # Attach FPS counter to the text and boxes
    cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (display_frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # If recording, write frame and check if 15 seconds is up
    if recording:
        out.write(display_frame)
        if time.time() >= recording_end_time:
            out.release()
            print(f"Recording finished. Converting to web format...")
            make_web_compatible(recording_filename)
            recording = False
            
    # Display everything over the video feed.
    cv2.imshow('Video', display_frame)

    # Check for button press to start recording
    # GPIO.input returns 0 when button is pressed (pull-up)
    if not recording and GPIO.input(BUTTON_PIN) == 0:
        # Start recording for 15 seconds
        visitor_name = "visitor"  # Default name
        recording_filename = os.path.join(
            RECORDINGS_DIR, f"{visitor_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(recording_filename, fourcc, 20.0, (frame.shape[1], frame.shape[0]))
        recording = True
        recording_end_time = time.time() + 15  # Record for 15 seconds
        print(f"Started recording to {recording_filename}")
        time.sleep(0.5)  # Debounce button

    # Break the loop and stop the script if 'q' is pressed
    if cv2.waitKey(1) == ord("q"):
        if recording:
            out.release()
            make_web_compatible(recording_filename)
        break

duration = 10
photo_count = 0
end_time = time.time() + duration

print("Capturing photos after recognition")
end_time = time.time() + duration
while time.time() < end_time:
    frame = picam2.capture_array()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    photo_count += 1
    cv2.imwrite(f"capture_{timestamp}.jpg", frame)
    time.sleep(interval)
print("Photo capture complete")

# By breaking the loop we run this code here which closes everything
cv2.destroyAllWindows()
picam2.stop()

# Close DB connection
cursor.close()
connection.close()

print("\nAll done. Encodings stored in PostgreSQL.")

if __name__ == "__main__":
    capture_video(PERSON_NAME)
