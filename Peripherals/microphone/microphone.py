import speech_recognition as sr

# Initialize recognizer
r = sr.Recognizer()

# Configure microphone
# Use the device index found in arecord -l
mic = sr.Microphone(device_index=1) 

print("Listening...")
with mic as source:
    r.adjust_for_ambient_noise(source)
    audio = r.listen(source)

print("Processing...")

