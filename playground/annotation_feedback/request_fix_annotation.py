"""Script that takes in annotation ids and creates a json to ingest into label studio."""
import os
import sys
import json
import argparse
import pandas as pd
from PIL import Image

# Add necessary paths to import project modules
sys.path.insert(0, "../../")
sys.path.insert(0, "../../../hindsight/hindsight_server/")

from annotation_helpers import add_hindsight_frame_path, get_entity_image, annotations_to_label_studio
from annotations_db import HindsightAnnotationsDB
from db import HindsightDB
from utils import make_dir

def main(annotation_ids, output_json_path, images_output_dir):
    # Initialize databases
    annotations_db = HindsightAnnotationsDB()
    make_dir(images_output_dir)

    # Fetch parent annotations
    all_annotations = annotations_db.get_annotations()
    parent_annotations = all_annotations.loc[
        (all_annotations['id'].isin(annotation_ids))
    ]

    # Add frame paths to annotations
    parent_annotations = add_hindsight_frame_path(parent_annotations)
    parent_annotations['frame_basename'] = parent_annotations['frame_path'].apply(
        lambda x: os.path.basename(x).split('.')[0]
    )

    parent_annotations['x2'] = parent_annotations['x'] + parent_annotations['w']
    parent_annotations['y2'] = parent_annotations['y'] + parent_annotations['h']

    all_preds = []
    for _, parent_row in parent_annotations.iterrows():
        # Fetch child annotations associated with the parent annotation
        child_annotations = all_annotations.loc[
            all_annotations['parent_annotation_id'] == parent_row['id']
        ]
        if child_annotations.empty:
            print(f"No child annotations found for parent annotation ID {parent_row['id']}")
            continue  # Skip if there are no child annotations

        # Ensure necessary fields are present
        child_annotations['model_file_hash'] = child_annotations['model_file_hash'].fillna('unknown_hash')
        child_annotations['id'] = child_annotations['id'].astype(str)

        # Determine if there are multiple model_file_hash values
        model_hashes = child_annotations['model_file_hash'].drop_duplicates()
        if len(model_hashes) > 1:
            # Determine the most recent model_file_hash based on the maximum 'id'
            # Assuming higher 'id's correspond to more recent annotations
            model_hash_ids = child_annotations.groupby('model_file_hash')['id'].max().reset_index()
            # Get the row with the highest 'id'
            most_recent_row = model_hash_ids.loc[model_hash_ids['id'].idxmax()]
            most_recent_model_hash = most_recent_row['model_file_hash']

            # Filter child_annotations to only include annotations from the most recent model_file_hash
            child_annotations = child_annotations[
                child_annotations['model_file_hash'] == most_recent_model_hash
            ]
        else:
            # Only one model_file_hash
            most_recent_model_hash = child_annotations.iloc[0]['model_file_hash']

        # Proceed to generate predictions
        # Get the image of the entity (cropped region)
        im = get_entity_image(parent_row)
        im_path = os.path.join(
            images_output_dir, f"{parent_row['frame_basename']}-{parent_row['id']}.jpg"
        )
        if not os.path.exists(im_path):
            im.save(im_path)

        # For compatibility, set model_name_version to model_file_hash
        child_annotations['model_name'] = 'model'
        child_annotations['model_version'] = most_recent_model_hash

        # Generate Label Studio prediction data
        preds_d = annotations_to_label_studio(
            child_annotations, im_path, im.width, im.height
        )
        all_preds.append(preds_d)

    # Save all predictions to a JSON file
    with open(output_json_path, 'w') as outfile:
        json.dump(all_preds, outfile)

    print(f"Label Studio JSON file created at {output_json_path}")

if __name__ == '__main__':
    # Convert annotation IDs to integers
    annotation_ids = [12319, 9266, 3036, 167795, 134730, 156062, 140943, 185851, 136204, 4686, 195399, 135018, 163161, 196444, 138]
    output_json_path = "ads_annotation_feedback.json"
    images_output_dir = "/Users/connorparish/code/hindsight_parsing/data/extracted_entities/tweets/annotation_feedback/"
    main(annotation_ids, output_json_path, images_output_dir)
