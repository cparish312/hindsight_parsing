import json
import yaml
import glob
import os
import numpy as np
import sys
import shutil

from ultralytics import YOLO

sys.path.insert(0, "../hindsight/hindsight_server/")
from db import HindsightDB
from utils import make_dir

project = "tweet_parse-2024-09-18-18-04-7d5636ed"

PROJECTS_DIR = os.path.abspath("/Users/connorparish/code/hindsight_parsing/playground/data_augmentation/tweet_clipping/data/")
MODELS_RUN_DIR = os.path.abspath("/Users/connorparish/code/hindsight_parsing/playground/data_augmentation/tweet_clipping/runs/")

project_dir = os.path.join(PROJECTS_DIR, project)
project_run_dir = os.path.join(MODELS_RUN_DIR, project)
make_dir(project_run_dir)

def create_config(project_dir):
    config_d = {"path" : project_dir, "train" : "images", "val" : "images"}
    with open(os.path.join(project_dir, "notes.json"), 'r') as infile:
        project_notes = json.load(infile)

    id_to_entity = {}
    for cat in project_notes['categories']:
        id_to_entity[cat['id']] = cat['name']

    config_d["names"] = id_to_entity

    config_f = os.path.join(project_dir, "train_config.yaml")
    with open(config_f, 'w') as outfile:
        yaml.dump(config_d, outfile)
    return config_f

if __name__ == "__main__":
    config_f = create_config(project_dir)

    model = YOLO("yolov8m.pt")
    results = model.train(data=config_f, epochs=30, device="mps", rect=True, 
                          augment=False, close_mosaic=0, batch=15, scale=0, 
                          translate=0, project=project_dir, name=project
                          )

