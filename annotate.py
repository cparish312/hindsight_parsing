import os
from PIL import Image
import json

from ultralytics import YOLO
from annotation_db import HindsightAnnotationsDB 

import sys
sys.path.insert(0, "../hindsight/hindsight_server/")

from db import HindsightDB
from utils import make_dir
    
MODEL_PATH = '/Users/connorparish/code/hindsight_parsing/notebooks/runs/detect/train15/weights/best.pt'
model_name = 'YOLOv5_train15'
model_version = 'v0.0'

# Initialize the YOLO model
trained_model = YOLO(MODEL_PATH)

db = HindsightDB()
annotation_db = HindsightAnnotationsDB()

def annotate_images(frames):
    images = [Image.open(f) for f in frames['path']]

    results = trained_model(images)
    for result in results:
        frame_row = frames.loc[frames['path'] == result.path].iloc[0]
        for i, box in enumerate(result.boxes):
            x = float(box.xyxy[0][0])
            y = float(box.xyxy[0][1])
            w = (float(box.xyxy[0][2]) - float(box.xyxy[0][0]))
            h = (float(box.xyxy[0][3]) - float(box.xyxy[0][1]))
            rotation = 0  # Assuming no rotation, adjust if your data includes rotation
            label = result.names[int(box.cls[0])]
            conf = float(box.conf[0])

            # Insert annotation into the database
            annotation_db.insert_annotation(int(frame_row['id']), x, y, w, h, rotation, label, conf, model_name, model_version)

def annotate_images_batches(frames, batch_size=50):
    num_batches = len(frames) // batch_size + (1 if len(frames) % batch_size > 0 else 0)
    for i in range(num_batches):
        print(f"Annotation Batch {i} out of {num_batches}")
        start_index = i * batch_size
        end_index = start_index + batch_size
        frames_batch = frames.iloc[start_index:end_index]
        annotate_images(frames_batch)

if __name__ == "__main__":
    frames = db.get_frames(impute_applications=False)
    frames = frames.loc[frames['application'] == "Twitter"]
    frames = frames.tail(2000)
    annotate_images_batches(frames)