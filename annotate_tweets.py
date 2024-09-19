import os
from PIL import Image
import json

from ultralytics import YOLO
from annotations_db import HindsightAnnotationsDB 

import sys
sys.path.insert(0, "../hindsight/hindsight_server/")

from db import HindsightDB
from utils import make_dir, hash_file
    
MODEL_PATH = '/Users/connorparish/code/hindsight_parsing/data/runs/tweet_parse-2024-09-19-17-46-d20a4703/tweet_parse-2024-09-19-17-46-d20a47032/weights/best.pt'
model_name = 'YOLOv8_tweet_parse'
model_version = 'v0.0'
model_file_hash = str(hash_file(MODEL_PATH))

# Initialize the YOLO model
trained_model = YOLO(MODEL_PATH)

db = HindsightDB()
annotation_db = HindsightAnnotationsDB()

def get_entity_image(entity_row):
    im = Image.open(entity_row['frame_path'])
    e = im.crop([entity_row['x'], entity_row['y'], entity_row['x2'], entity_row['y2']])
    e.filename = str(entity_row['id'])
    return e

def annotate_entities(entities):
    images = list()
    for i, entity_row in entities.iterrows():
        images.append(get_entity_image(entity_row=entity_row))

    results = trained_model(images, device="mps")
    for result in results:
        entity_row = entities.loc[entities['id'] == int(result.path)].iloc[0]
        if len(result.boxes) == 0:
            annotation_db.insert_annotation(parent_annotation_id=int(entity_row['id']), x=0, y=0, w=0, h=0, rotation=0,
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
            annotation_db.insert_annotation(parent_annotation_id=int(entity_row['id']), x=x, y=y, w=w, h=h, rotation=rotation,
                                             label=label, conf=conf, model_name=model_name, model_version=model_version, model_file_hash=model_file_hash)

def annotate_entities_batches(entities, batch_size=200):
    num_batches = len(entities) // batch_size + (1 if len(entities) % batch_size > 0 else 0)
    for i in range(num_batches):
        print(f"Annotation Batch {i} out of {num_batches}")
        start_index = i * batch_size
        end_index = start_index + batch_size
        entities_batch = entities.iloc[start_index:end_index]
        annotate_entities(entities_batch)

complete_y_min = 160
complete_y_max = 2200
def tweet_complete(row):
    im_annotations = annotations.loc[annotations['frame_id'] == row['frame_id']]
    all_im_annotations = set(im_annotations['label'])
    y_min = complete_y_min
    y_max = complete_y_max
    if "twitter_top_menu" in all_im_annotations:
        y_min += im_annotations.loc[im_annotations['label'] == "twitter_top_menu"].iloc[0]['y2']
    
    if "twitter_bottom_menu" in all_im_annotations:
        y_max -= im_annotations.loc[im_annotations['label'] == "twitter_bottom_menu"].iloc[0]['y']

    return row['y'] >= y_min and row['y2'] <= y_max

def filter_annotations(annotations):
    filtered_annotations = annotations.copy()
    filtered_annotations['tweet_complete'] = filtered_annotations.apply(lambda row: tweet_complete(row), axis=1)
    filtered_annotations = filtered_annotations.loc[filtered_annotations['tweet_complete']]
    return filtered_annotations

if __name__ == "__main__":
    parent_label = "tweet"
    all_annotations = annotation_db.get_annotations()
    annotations = all_annotations.loc[all_annotations['label'] == parent_label]

    already_processed_parent_ids = set(all_annotations.loc[all_annotations['model_file_hash'] == model_file_hash]['parent_annotation_id'])
    annotations = annotations.loc[~annotations['id'].isin(already_processed_parent_ids)]

    frames = db.get_frames(frame_ids=set(annotations['frame_id']), impute_applications=False)
    frame_id_to_path = {f : p for f, p in zip(frames['id'], frames['path'])}
    annotations['frame_path'] = annotations['frame_id'].map(frame_id_to_path)

    annotations['x2'] = annotations['x'] + annotations['w']
    annotations['y2'] = annotations['y'] + annotations['h']

    annotations = filter_annotations(annotations)

    print(len(annotations))

    annotate_entities_batches(annotations)