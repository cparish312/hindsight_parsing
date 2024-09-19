import os
from PIL import Image
import json

from ultralytics import YOLO
from annotations_db import HindsightAnnotationsDB 

import sys
sys.path.insert(0, "../hindsight/hindsight_server/")

from db import HindsightDB
from utils import make_dir, hash_file
    
MODEL_PATH = '/Users/connorparish/code/hindsight_parsing/notebooks/runs/detect/train162/weights/best.pt'
model_name = 'YOLOv5_train162'
model_version = 'v0.0'
model_file_hash = str(hash_file(MODEL_PATH))

# Initialize the YOLO model
trained_model = YOLO(MODEL_PATH)

db = HindsightDB()
annotation_db = HindsightAnnotationsDB()

def annotate_images(frames):
    images = [Image.open(f) for f in frames['path']]

    results = trained_model(images, device="mps")
    for result in results:
        frame_row = frames.loc[frames['path'] == result.path].iloc[0]
        if len(result.boxes) == 0:
            annotation_db.insert_annotation(frame_id=int(frame_row['id']), x=0, y=0, w=0, h=0, rotation=0,
                                             label=None, conf=0, model_name=model_name, model_version=model_version, model_file_hash=model_file_hash)
        for i, box in enumerate(result.boxes):
            x = float(box.xyxy[0][0])
            y = float(box.xyxy[0][1])
            w = (float(box.xyxy[0][2]) - float(box.xyxy[0][0]))
            h = (float(box.xyxy[0][3]) - float(box.xyxy[0][1]))
            rotation = 0  # Assuming no rotation, adjust if your data includes rotation
            label = result.names[int(box.cls[0])]
            conf = float(box.conf[0])

            # Insert annotation into the database
            annotation_db.insert_annotation(frame_id=int(frame_row['id']), x=x, y=y, w=w, h=h, rotation=rotation,
                                             label=label, conf=conf, model_name=model_name, model_version=model_version, model_file_hash=model_file_hash)

def annotate_images_batches(frames, batch_size=200):
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

    all_annotations = annotation_db.get_annotations()
    annotations = all_annotations.loc[all_annotations['model_file_hash'] == model_file_hash]
    annotations_frame_ids = set(annotations['frame_id'])
    frames = frames.loc[~frames['id'].isin(annotations_frame_ids)]
    annotate_images_batches(frames)