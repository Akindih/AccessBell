import cv2
import os
from datetime import datetime
from itertools import count
from picamera2 import Picamera2
import time
import RPi.GPIO as GPIO
import face_recognition
import numpy as np
import pickle


# Load pre-trained face encodings
print("[INFO] loading encodings...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())
known_face_encodings = data["encodings"]
known_face_names = data["names"]

cv_scaler = 4 # this has to be a whole number

face_locations = []
face_encodings = []
face_names = []
frame_count = 0
start_time = time.time()
fps = 0

# GPIO SETUP
BUTTON_PIN = 26 #Pin 37
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#convert --indir VIDEOS --outdir VIDEOS/CONVERTED
# Change this to the name of the person you're photographing
PERSON_NAME = "aki"  

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

    # Initialize camera
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"format": "XRGB8888", "size": (640, 480)}
    )
    picam2.configure(config)
    picam2.start()

    time.sleep(2)  # Camera warmup

    frame_width = 640
    frame_height = 480

    # Create video filename with timestamp
    filename = os.path.join(
        folder, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    )

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(filename, fourcc, 20.0, (frame_width, frame_height))

    print("Waiting for button press...")
    GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
    print("Button pressed! Recording for 5 seconds...")

    duration = 10
    end_time = time.time() + duration

# Load pre-trained face encodings
print("[INFO] loading encodings...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())
known_face_encodings = data["encodings"]
known_face_names = data["names"]


cv_scaler = 4 # this has to be a whole number

face_locations = []
face_encodings = []
face_names = []
frame_count = 0
start_time = time.time()
fps = 0

def process_frame(frame):
    global face_locations, face_encodings, face_names
    
    # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
    resized_frame = cv2.resize(frame, (0, 0), fx=(1/cv_scaler), fy=(1/cv_scaler))
    
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

    while time.time() < end_time:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

        out.write(frame)
        cv2.imshow("Recording", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    print("Recording complete!")

if __name__ == "__main__":
    capture_video(PERSON_NAME)
   
def process_frame(frame):
    global face_locations, face_encodings, face_names
    
    # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
    resized_frame = cv2.resize(frame, (0, 0), fx=(1/cv_scaler), fy=(1/cv_scaler))
    
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


def calculate_fps():
    global frame_count, start_time, fps
    frame_count += 1
    elapsed_time = time.time() - start_time
    if elapsed_time > 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = time.time()
    return fps

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
    
    # Display everything over the video feed.
    cv2.imshow('Video', display_frame)
    
    # Break the loop and stop the script if 'q' is pressed
    if cv2.waitKey(1) == ord("q"):
        break 


    # Cleanup
    out.release()
    cv2.destroyAllWindows()
    picam2.stop()
    GPIO.cleanup()
