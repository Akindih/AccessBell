# Accessible Doorbell - Backend (Flask + Picamera2 + GPIO)
# Raspberry Pi 4 + Pi Camera + Button (GPIO17) + PIR (GPIO27)

from flask import Flask, render_template, Response, jsonify
from picamera2 import Picamera2
import RPi.GPIO as GPIO
import cv2
import time
import atexit

app = Flask(__name__)

# --- GPIO CONFIG ---
BUTTON_PIN = 17  # Doorbell button
PIR_PIN = 27     # PIR motion sensor

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIR_PIN, GPIO.IN)

doorbell_active = False
motion_active = False
last_ring_ts = 0.0
last_motion_ts = 0.0
RING_COOLDOWN = 1.0      # seconds
MOTION_COOLDOWN = 1.0    # seconds


def button_callback(channel):
    global doorbell_active, last_ring_ts
    now = time.time()
    if now - last_ring_ts > RING_COOLDOWN:
        doorbell_active = True
        last_ring_ts = now
        print('[GPIO] Doorbell pressed')


def pir_callback(channel):
    global motion_active, last_motion_ts
    now = time.time()
    if now - last_motion_ts > MOTION_COOLDOWN:
        motion_active = True
        last_motion_ts = now
        print('[GPIO] Motion detected')


GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=button_callback, bouncetime=300)
GPIO.add_event_detect(PIR_PIN, GPIO.RISING, callback=pir_callback, bouncetime=500)

# --- CAMERA CONFIG (Picamera2) ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (1280, 720)})
picam2.configure(config)
picam2.start()


def gen_frames():
    """Generate an MJPEG stream from the Pi Camera."""
    while True:
        frame = picam2.capture_array()  # RGB888 numpy array
        ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            continue
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/status')
def status():
    """Return one-shot flags that UI polls. Flags reset after read."""
    global doorbell_active, motion_active
    payload = {"doorbell": doorbell_active, "motion": motion_active}
    doorbell_active = False
    motion_active = False
    return jsonify(payload)


@app.route('/health')
def health():
    return {'ok': True}, 200


def cleanup():
    try:
        picam2.stop()
    except Exception:
        pass
    try:
        GPIO.cleanup()
    except Exception:
        pass

atexit.register(cleanup)


if __name__ == '__main__':
    # threaded=True allows streaming + polling simultaneously
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
