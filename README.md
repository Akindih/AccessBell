# Accessible Doorbell (Full Project)

Raspberry Pi 4 + Pi Camera + 7" Touch Display + Button (GPIO17) + PIR (GPIO27).

## Folder
```
accessible-doorbell/
├─ app.py
├─ requirements.txt
├─ doorbell.service
├─ README.md
├─ templates/
│  └─ index.html
└─ static/
   └─ audio/
      └─ beep.wav
```

## Install (Raspberry Pi OS)
```bash
sudo apt update && sudo apt -y upgrade
sudo apt install -y python3-picamera2 python3-opencv python3-venv
cd ~/accessible-doorbell
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run
```bash
python app.py
# Open http://localhost:5000 on the Pi touchscreen
```

## Autostart (optional)
```bash
sudo cp doorbell.service /etc/systemd/system/doorbell.service
sudo systemctl daemon-reload
sudo systemctl enable --now doorbell.service
sudo systemctl status doorbell.service
```

## Wiring (BCM)
- Button → GPIO17 (pin 11) to GND (pin 9/6)
- PIR OUT → GPIO27 (pin 13); VCC → 5V (pin 2); GND → GND

## Notes
- Ensure `libcamera-hello` works before running (verifies camera).
- If you serve UI from another host/port, you might need CORS.
- To save snapshots, call `picam2.capture_array()` and `cv2.imwrite('captures/ts.jpg', frame)` in the callbacks.
