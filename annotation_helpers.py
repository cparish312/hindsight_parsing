from PIL import Image, ImageDraw, ImageFont

import sys
sys.path.insert(0, "../hindsight/hindsight_server/")

from db import HindsightDB

db = HindsightDB()

def add_hindsight_frame_path(annotations):
    frames = db.get_frames(frame_ids=set(annotations['frame_id']), impute_applications=False)
    frame_id_to_path = {f : p for f, p in zip(frames['id'], frames['path'])}
    annotations['frame_path'] = annotations['frame_id'].map(frame_id_to_path)
    return annotations

def get_entity_image(entity_row):
    if "frame_path" in entity_row:
        im = Image.open(entity_row['frame_path'])
    else:
        im_path = db.get_frames(frame_ids=[entity_row['frame_id']]).iloc[0]['path']
        im = Image.open(im_path)
    e = im.crop([entity_row['x'], entity_row['y'], entity_row['x2'], entity_row['y2']])
    e.filename = str(entity_row['id'])
    return e

def visualize_annotations(im, annotations):
    im_c = im.copy()
    annotations = annotations.copy()
    annotations['x2'] = annotations['x'] + annotations['w']
    annotations['y2'] = annotations['y'] + annotations['h']

    font = ImageFont.load_default()

    draw = ImageDraw.Draw(im_c)
    for i, row in annotations.iterrows():
        draw.rectangle((row['x'], row['y'], row['x2'], row['y2']), outline="red", width=5)
        text_position = (row['x'], row['y'] - 10)
        draw.text(text_position, row['label'], fill="white", font=font)
        # text_position = (row['x'], row['y'] - 10)  # Position the label above the rectangle
        # Optionally add a background for text for better readability
        # text_width, text_height = font.getsize(row['label'])
        # draw.rectangle((text_position[0], text_position[1], text_position[0] + text_width, text_position[1] + text_height), fill="black")
        # draw.text(text_position, row['label'], fill="white", font=font)
    return im_c

def annotations_to_label_studio(annotations, image_path, image_width, image_height):
    annotations['model_name_version'] = annotations['model_name'] + "-" + annotations['model_version']
    assert len(set(annotations['model_name_version'])) == 1, "Trying to export from predictions from multiple models"

    model_name_version = annotations['model_name_version'].iloc[0]

    image_preds_d = {}
    label_studio_image_path = f"/data/local-files/?d={image_path}"
    image_preds_d['data'] = {"image" : label_studio_image_path}
    predictions_d = {"model_version": model_name_version, "score": 1.0}
    result_d_template = {"type": "rectanglelabels",        
            "from_name": "label", "to_name": "image",
            "original_width": image_width, "original_height": image_height,
            "image_rotation": 0}
    
    converted_results = list()
    for i, row  in annotations.iterrows():
        result_d = result_d_template.copy()
        result_d['id'] = f"result_{row['id']}"
        value_d = {"rotation" : 0,
                "x" : ((row['x'] / image_width) * 100),
                "y" : ((row['y'] / image_height) * 100),
                "width" : ((row['w'] / image_width) * 100), 
                "height": ((row['h'] / image_height) * 100), 
                "rectanglelabels": [row['label']]}
        result_d['value'] = value_d
        converted_results.append(result_d)
        
    predictions_d["result"] = converted_results
    image_preds_d['predictions'] = [predictions_d]
    return image_preds_d
    