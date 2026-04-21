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
#import speech_recognition as sr


# Directory where recordings are saved (must match appAPI.py)
RECORDINGS_DIR = "/home/doorbellteam/FaceRec/doorbell_recordings"
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

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
picam2.configure(picam2.create_preview_configuration(
    main={"format": 'RGB888', "size": (1920, 1080)}))
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
frame_width=1920
frame_height=1080

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
def log_visitor(person_id, recognised, confidence, name="Unknown", snapshot=None):
    cursor.execute("""
        INSERT INTO visitor_log (person_id, recognised, confidence, snapshot)
        VALUES (%s, %s, %s, %s);
    """, (person_id, recognised, confidence, snapshot))
    connection.commit()

    # Create video filename with timestamp in recordings folder
<<<<<<< HEAD
    filename = os.path.join(
        RECORDINGS_DIR, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    )
=======
   # filename = os.path.join(
        #RECORDINGS_DIR, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    #)
>>>>>>> 6f99e5b2e01704624cc448c67408f9f1cba1748f

    #fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    #out = cv2.VideoWriter(filename, fourcc, 20.0, (frame_width, frame_height))


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
print("Ready — press button to start recording...")

# Initialize recognizer
#r = sr.Recognizer()

# Configure microphone
# Use the device index found in arecord -l
#mic = sr.Microphone(device_index=1) 

#print("Listening...")
#with mic as source:
 #  r.adjust_for_ambient_noise(source)
#audio = r.listen(source)

#print("Processing...")

def process_frame(frame):
    global face_locations, face_encodings, face_names

    # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
    resized_frame = cv2.resize(frame, (0, 0), fx=(1 / cv_scaler), fy=(1 / cv_scaler))

    # Convert the image from BGR to RGB colour space, the facial recognition library uses RGB, OpenCV uses BGR
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_RGB2BGR)

    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')

    face_names = []
    
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)

        if matches[best_match_index]:
            name = known_face_names[best_match_index]
            recognised = True
            person_id = known_ids[best_match_index]
        else:
            person_id = None
            name = "Unknown"
            recognised = False


        confidence = 1 - face_distances[best_match_index]

        # Log the visitor
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

<<<<<<< HEAD
=======
print("[DEBUG] Entering main loop...")

GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
print("Button pressed! Starting display and recording...")

>>>>>>> 6f99e5b2e01704624cc448c67408f9f1cba1748f
while True:
    frame = picam2.capture_array()
    print("[DEBUG] Frame captured")
    
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    processed_frame = process_frame(frame)
    display_frame = draw_results(processed_frame)

    current_fps = calculate_fps()
    cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (display_frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

<<<<<<< HEAD
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
=======
    # Check button
    button_state = GPIO.input(BUTTON_PIN)
    print(f"[DEBUG] Button state: {button_state} | Recording: {recording}")

    if not recording and button_state == 0:
        print("[DEBUG] Button pressed! Starting recording...")
        visitor_name = face_names[0] if face_names else "visitor"
        recording_filename = os.path.join(
            RECORDINGS_DIR, f"{visitor_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        print(f"[DEBUG] Saving to: {recording_filename}")
        print(f"[DEBUG] Frame size: {frame_width}x{frame_height}")
        
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(recording_filename, fourcc, 20.0, (frame_width, frame_height))
        
        if not out.isOpened():
            print("[ERROR] VideoWriter failed to open! Check path and codec.")
        else:
            print("[DEBUG] VideoWriter opened successfully")
        
        recording = True
        recording_end_time = time.time() + 20
        time.sleep(0.5)

    if recording:
        if out and out.isOpened():
            out.write(display_frame)
            remaining = recording_end_time - time.time()
            print(f"[DEBUG] Recording... {remaining:.1f}s remaining")
        else:
            print("[ERROR] out is not open during recording!")

        if time.time() >= recording_end_time:
            out.release()
            print(f"[DEBUG] Recording finished, converting...")
            make_web_compatible(recording_filename)
            recording = False
            out = None

    cv2.imshow('Video', display_frame)
    cv2.waitKey(1) 
    
interval = 0.5
duration = 20
>>>>>>> 6f99e5b2e01704624cc448c67408f9f1cba1748f
photo_count = 0
end_time = time.time() + duration

print("Capturing photos after recognition")
end_time = time.time() + duration
while time.time() < end_time:
    frame = picam2.capture_array()
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
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

if __name__ == "__main__":
    capture_video(PERSON_NAME)
