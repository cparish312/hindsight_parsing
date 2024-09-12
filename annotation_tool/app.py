from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import os
import cv2
import numpy as np
import pandas as pd
from datetime import datetime

import sys
sys.path.insert(0, "../../hindsight/hindsight_server/")

from db import HindsightDB
from utils import add_datetimes

app = Flask(__name__)

BASE_IMAGE_PATH = '/Users/connorparish/.hindsight_server/data/raw_screenshots'

db = HindsightDB()

def get_images_df():
    """Gets a DataFrame of all images at the time of inititation"""
    images_df = db.get_frames(applications={'com-twitter-android'})
    images_df = images_df.sample(frac=1)
    images_df = add_datetimes(images_df)
    images_df['serve_path'] = images_df['path'].apply(lambda x: x.replace(BASE_IMAGE_PATH, ""))
    images_df['boxes'] = np.empty((len(images_df), 0)).tolist()
    return images_df

current_index = 0
images_df = get_images_df()

@app.route('/')
def index():
    global current_index, images_df
    image_path = images_df.iloc[current_index]['serve_path']
    return render_template('index.html', image_path=image_path, boxes=[])

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve an image file from the filesystem."""
    clean_filename = filename.lstrip('/')
    print("Serving file from:", os.path.join(BASE_IMAGE_PATH, clean_filename))

    return send_from_directory(BASE_IMAGE_PATH, clean_filename)

@app.route('/next_image', methods=['POST'])
def next_image():
    global current_index, images_df
    if current_index < len(images_df) - 1:
        current_index += 1
    else:
        current_index = 0  # Reset to first image or handle completion
    image_path = images_df.iloc[current_index]['serve_path']
    return jsonify({'new_image_url': url_for('serve_image', filename=image_path)})

@app.route('/previous_image', methods=['POST'])
def previous_image():
    global current_index, images_df
    if current_index > 0:
        current_index -= 1
    else:
        current_index = len(images_df) - 1  # Go to the last image
    image_path = images_df.iloc[current_index]['serve_path']
    return jsonify({'new_image_url': url_for('serve_image', filename=image_path)})

@app.route('/save_coordinates', methods=['POST'])
def save_coordinates():
    data = request.get_json()
    x1 = data['x1']
    y1 = data['y1']
    x2 = data['x2']
    y2 = data['y2']
    image_path = data['image_path'].replace("http://127.0.0.1:5000/images/", "")
    print("Image path", image_path)

    # Find the image in the DataFrame and add/update its bounding box
    global images_df
    idx = images_df[images_df['serve_path'] == image_path].index[0]
    if 'boxes' in images_df.columns:
        images_df.at[idx, 'boxes'].append((x1, y1, x2, y2))
    else:
        images_df.at[idx, 'boxes'] = [(x1, y1, x2, y2)]

    print(f"Bounding box received: ({x1}, {y1}, {x2}, {y2}) for image {image_path}")

    return jsonify({'status': 'success', 'message': 'Bounding box saved'})


if __name__ == "__main__":
    app.run(debug=True)
