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

project = "tweet_parse-2024-09-21-01-13-dc3535d9"

# PROJECTS_DIR = os.path.abspath("/Users/connorparish/code/hindsight_parsing/playground/data_augmentation/tweet_clipping/data/")
# MODELS_RUN_DIR = os.path.abspath("/Users/connorparish/code/hindsight_parsing/playground/data_augmentation/tweet_clipping/runs/")
PROJECTS_DIR = os.path.abspath("/Users/connorparish/code/hindsight_parsing/data/label_studio/")
MODELS_RUN_DIR = os.path.abspath("/Users/connorparish/code/hindsight_parsing/data/runs/")

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

    model_f = os.path.join(project_run_dir, f"{project}/weights/last.pt")
    if os.path.exists(model_f):
        print("Loading existing model", model_f)
        model = YOLO(model_f)
    else:
        model = YOLO("yolov8m.pt")

    # results = model.train(data=config_f, epochs=20, device="cpu", rect=True, 
    #                     augment=False, close_mosaic=0, batch=10, scale=0, erasing=0, fliplr=0,
    #                     translate=0, project=project_run_dir, name=project,
    #                     )
    results = model.train(data=config_f, epochs=40, device="mps", rect=True, 
                          augment=False, close_mosaic=0, batch=10, scale=0, 
                          translate=0, project=project_run_dir, name=project
                          )

