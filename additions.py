import uuid # Add at top of file

# -- New Configuration --
DATASET_DIR = "/home/doorbellteam/FaceRec/dataset"
os.makedirs(DATASET_DIR, exist_ok=True)

def recognition_worker(frame_queue, stop_event):
    global recognition_results, unknown_logged_this_session
    frame_count = 0
    photos_taken = 0
    # Unique ID for this specific doorbell press session
    session_unknown_id = f"unknown_{uuid.uuid4().hex[:8]}"
    session_dir = os.path.join(DATASET_DIR, session_unknown_id)
    
    while not stop_event.is_set():
        if not frame_queue.empty():
            frame = frame_queue.get()
            frame_count += 1
            if frame_count % PROCESS_EVERY_N_FRAME != 0: continue

            small_frame = cv2.resize(frame, (0, 0), fx=1/CV_SCALER, fy=1/CV_SCALER)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small)
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
            
            names = []
            for i, encoding in enumerate(face_encodings):
                name = "Unknown"
                if known_face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, encoding)
                    face_distances = face_recognition.face_distance(known_face_encodings, encoding)
                    best_idx = np.argmin(face_distances)
                    
                    if matches[best_idx]:
                        name = known_face_names[best_idx]
                        if name not in last_logged_names:
                            log_known_to_db(name, best_idx, float(1 - face_distances[best_idx]))
                            last_logged_names.add(name)
                    else:
                        # --- CAPTURE UNKNOWN PHOTO ---
                        if photos_taken < 10:
                            if not os.path.exists(session_dir): os.makedirs(session_dir)
                            
                            # Extract face from original high-res frame
                            top, right, bottom, left = [v * CV_SCALER for v in face_locations[i]]
                            face_img = frame[top:bottom, left:right]
                            
                            photo_path = os.path.join(session_dir, f"{photos_taken}.jpg")
                            cv2.imwrite(photo_path, face_img)
                            photos_taken += 1
                            
                        if not unknown_logged_this_session:
                            log_unknown_to_db(float(1 - face_distances[best_idx]))
                            unknown_logged_this_session = True
                
                names.append(name)
            recognition_results = {"names": names, "locations": face_locations}
def rebuild_encodings():
    known_encodings = []
    known_names = []
    
    # Loop through every person folder in dataset
    for person_name in os.listdir(DATASET_DIR):
        person_dir = os.path.join(DATASET_DIR, person_name)
        if not os.path.isdir(person_dir): continue
        
        for img_name in os.listdir(person_dir):
            img_path = os.path.join(person_dir, img_name)
            image = face_recognition.load_image_file(img_path)
            encodings = face_recognition.face_encodings(image)
            
            if len(encodings) > 0:
                known_encodings.append(encodings[0])
                known_names.append(person_name)
                
    # Save to the file the RPi script reads
    data = {"encodings": known_encodings, "names": known_names}
    with open("encodings.pickle", "wb") as f:
        f.write(pickle.dumps(data))
    print(f"Success: Re-encoded {len(known_names)} face samples.")
@app.route("/api/name-person", methods=["POST"])
def name_person():
    data = request.json
    # Assume the UI sends the 'unknown_id' generated during the session
    temp_id = data.get("unknown_id") 
    new_name = data.get("name").strip()
    
    old_path = os.path.join(DATASET_DIR, temp_id)
    new_path = os.path.join(DATASET_DIR, new_name)
    
    try:
        if os.path.exists(old_path):
            # If a folder with that name already exists, move files into it
            if os.path.exists(new_path):
                for f in os.listdir(old_path):
                    os.rename(os.path.join(old_path, f), os.path.join(new_path, f))
                os.rmdir(old_path)
            else:
                os.rename(old_path, new_path)
            
            # Update the pickle file immediately
            rebuild_encodings()
            
            return jsonify({"success": True, "message": f"Recognised as {new_name}"})
        return jsonify({"error": "Unknown ID folder not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
