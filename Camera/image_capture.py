import cv2
import os
from datetime import datetime
from itertools import count
from picamera2 import Picamera2
import time
import RPi.GPIO as GPIO

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

    while time.time() < end_time:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

        out.write(frame)
        cv2.imshow("Recording", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    print("Recording complete!")

    # Cleanup
    out.release()
    cv2.destroyAllWindows()
    picam2.stop()
    GPIO.cleanup()


if __name__ == "__main__":
    capture_video(PERSON_NAME) 