import time
import os
from datetime import datetime
import cv2
import RPi.GPIO as GPIO

# GPIO SETUP
BUTTON_PIN = 26 #Pin 37
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#  CAMERA START
picam2.start()
time.sleep(2)  # warm-up

photo_count = 0
duration = 10          # seconds
interval = 0.5         # seconds

print("Waiting for button press to start photo capture...")

#  WAIT FOR BUTTON PRESS
GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING) #The program pauses here and waits until the button is pressed
#and the pin goes from HIGH → LOW
print("Button pressed! Starting timed capture...")

end_time = time.time() + duration

#  TIMED CAPTURE LOOP
while time.time() < end_time:
    frame = picam2.capture_array()

    photo_count += 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{name}_{timestamp}.jpg"
    filepath = os.path.join(folder, filename)
    cv2.imwrite(filepath, frame)

    print(f"Photo {photo_count} saved: {filepath}")

    time.sleep(interval)

cv2.destroyAllWindows()
GPIO.cleanup()
print("Done.")