import os
import cv2
import psycopg2
import numpy as np
import face_recognition
import hashlib

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
    SELECT person_id FROM known_person
    WHERE full_name = %s
    """, (full_name,))
    result = cursor.fetchone()
    if result:
        # If person already exists, reuse their face encodings and ID
        person_id = result[0]

    else:
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
    encoding_hash = hashlib.sha256(binary_encoding).hexdigest()

    cursor.execute("""
        SELECT 1 FROM face_encoding
        WHERE person_id = %s AND encoding_hash = %s
    """, (person_id, encoding_hash))

    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO face_encoding (person_id, encoding, encoding_hash)
            VALUES (%s, %s, %s)
        """, (person_id, binary_encoding, encoding_hash))
        connection.commit()


# Optional dataset check
try:
    f = open("dataset.csv", "r")
    print("dataset opened")
    f.close()
except FileNotFoundError:
    print("data.csv not found")
except Exception as e:
    print("error:", e)


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


# Close DB connection
cursor.close()
connection.close()

print("\nAll done. Encodings stored in PostgreSQL.")
