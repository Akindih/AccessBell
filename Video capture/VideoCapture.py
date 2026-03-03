import cv2
from itertools import count
# Open the default camera
cam = cv2.VideoCapture(0)

# Get the default frame width and height
frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output.mp4', fourcc, 20.0, (frame_width, frame_height))

saved_count = 0

for frame_idx in count():
    ret, frame = cam.read()
    if not ret:
        break

    # Save one frame every 5 frames until 10 frames are saved
    if frame_idx % 5 == 0 and saved_count < 10:
        out.write(frame)
        saved_count += 1

    cv2.imshow('Camera', frame)
    # Press 'q' to exit the loop or all frames captured
    if cv2.waitKey(1) == ord('q') or saved_count >= 10:
        break

# Release the capture and writer objects
cam.release()
out.release()
cv2.destroyAllWindows()