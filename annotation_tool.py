import os
import cv2
from datetime import datetime
import platform
import matplotlib
import numpy as np
import pandas as pd
import tkinter as tk
import colorcet as cc
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from PIL import Image, ImageTk

import tzlocal
from zoneinfo import ZoneInfo
from dataclasses import dataclass

import sys
sys.path.insert(0, "../hindsight/hindsight_server/")

from db import HindsightDB
from utils import add_datetimes

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

@dataclass
class Screenshot:
    image: np.array
    text_df: pd.DataFrame
    timestamp: datetime.timestamp
    annotations: pd.DataFrame = None

class AnnotatorGUI:
    def __init__(self, master, frame_id = None, max_width=1536, max_height=1000):
        self.master = master
        self.db = HindsightDB()
        self.images_df = self.get_images_df()
        self.num_frames = len(self.images_df)
        self.max_frames_index = max(self.images_df.index)
        self.max_width = max_width
        self.max_height = max_height - 200

        self.screenshots_on_timeline = 40 

        if frame_id is None:
            self.scroll_frame_num = 0
        else:
            self.scroll_frame_num = self.images_df.index.get_loc(self.images_df[self.images_df['id'] == frame_id].index[0])
        self.scroll_frame_num_var = tk.StringVar()

        self.box_start = None
        self.box_end = None
        self.adjusting_box = False

        self.labels = {"test"}
        self.current_label = tk.StringVar()

        self.configure_window()
        self.setup_gui()

        self.exit_flag = False

    def configure_window(self):
        # Get the dimensions of the user's screen
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        # Calculate appropriate size and position
        window_width = min(self.max_width, screen_width - 100)  # Reserve some space
        window_height = min(self.max_height, screen_height - 100)  # Reserve some space
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2

        # Set the window size and position ('widthxheight+x+y')
        self.master.geometry(f'{window_width}x{window_height}+{x_position}+{y_position}')

    def get_images_df(self):
        """Gets a DataFrame of all images at the time of inititation"""
        images_df = self.db.get_frames(applications={'com-twitter-android'})
        images_df = images_df.sample(frac=1)
        images_df = add_datetimes(images_df)
        return images_df
    
    def setup_gui(self):
        self.master.title("Image Annotation Tool")

        # Main frame to hold everything
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame for the image and the canvas
        image_frame = ttk.Frame(main_frame)
        image_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Frame for label controls to the right of the image
        label_frame = ttk.Frame(main_frame)
        label_frame.grid(row=0, column=1, sticky="ns", padx=5, pady=5)

        # Configuration for grid to give more space to the image area
        main_frame.columnconfigure(0, weight=3)  # Image area gets more space
        main_frame.columnconfigure(1, weight=1)  # Label area gets less
        main_frame.rowconfigure(0, weight=1)

        # Setup the canvas within the image frame
        self.canvas = tk.Canvas(image_frame, width=self.max_width, height=self.max_height)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.handle_click)

        # Configure grid for label_frame to manage space allocation better
        label_frame.columnconfigure(0, weight=1)
        label_frame.columnconfigure(1, weight=1)
        label_frame.columnconfigure(2, weight=3)  # Give more space to combobox

        # Entry for adding new labels
        self.new_label_entry = ttk.Entry(label_frame)
        self.new_label_entry.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Button to add a new label to the combobox and label list
        add_label_button = ttk.Button(label_frame, text="Add Label", command=self.add_label)
        add_label_button.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Label selection combobox, given more space
        self.label_combobox = ttk.Combobox(label_frame, textvariable=self.current_label, values=list(self.labels))
        self.label_combobox.grid(row=0, column=2, sticky="ew", padx=5, pady=5)

        # Bind selection change of combobox to update current label
        self.label_combobox.bind("<<ComboboxSelected>>", self.label_selected)

        # Frame for the time label, centered below the image frame
        time_label_frame = ttk.Frame(self.master)
        time_label_frame.pack(fill=tk.X)
        self.time_label = ttk.Label(time_label_frame, textvariable=self.scroll_frame_num_var, font=("Arial", 24), anchor="center")
        self.time_label.pack(pady=5)

        # Load and display the initial frame
        self.displayed_frame_num = self.scroll_frame_num
        self.screenshot = self.get_screenshot(self.displayed_frame_num)
        self.display_frame()


    def resize_screenshot(self, screenshot, max_width, max_height):
        height, width, _ = screenshot.image.shape
        if width > max_width or height > max_height:
            scaling_factor = min(max_width / width, max_height / height)
            new_size = (int(width * scaling_factor), int(height * scaling_factor))
            self.image_width = new_size[0]
            self.image_height = new_size[1]
            screenshot.image = cv2.resize(screenshot.image, new_size, interpolation=cv2.INTER_AREA)
            if screenshot.text_df is not None:
                screenshot.text_df.loc[:, 'x'] = screenshot.text_df['x'] * scaling_factor
                screenshot.text_df.loc[:, 'y'] = screenshot.text_df['y'] * scaling_factor
                screenshot.text_df.loc[:, 'w'] = screenshot.text_df['w'] * scaling_factor
                screenshot.text_df.loc[:, 'h'] = screenshot.text_df['h'] * scaling_factor
        return screenshot
    
    def get_screenshot(self, i):
        """Loads and resizes the screenshot."""
        im_row = self.images_df.iloc[i]
        image = cv2.imread(im_row['path'])
        text_df = self.db.get_ocr_results(frame_id=im_row['id'])
        if set(text_df['text']) == {None}:
            text_df = None
        screenshot = Screenshot(image=image, text_df=text_df, timestamp=im_row['datetime_local'])
        screenshot_resized = self.resize_screenshot(screenshot, self.max_width, self.max_height)
        return screenshot_resized
    
    def display_frame(self):
        screenshot = self.screenshot
        cv2image = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, image=imgtk, anchor=tk.NW)
        self.canvas.image = imgtk  # Keep a reference!
        # if self.screenshot.annotations is not None:
        #     for _, row in self.screenshot.annotations.iterrows():
        #         self.draw_box(row)
        self.scroll_frame_num_var.set(f"{screenshot.timestamp.strftime('%A, %Y-%m-%d %H:%M')}")

    def add_label(self):
        new_label = self.new_label_entry.get()
        if new_label and new_label not in self.labels:
            self.labels.add(new_label)
            self.label_combobox['values'] = list(self.labels)
            self.label_combobox.set(new_label)
            self.new_label_entry.delete(0, tk.END)

    def label_selected(self, event=None):
        self.current_label.set(self.label_combobox.get())

    def click_left(self, event):
        """Move to the next frame on the right."""
        if self.scroll_frame_num < self.max_frames_index:
            self.scroll_frame_num += 1
            self.screenshot = self.get_screenshot(self.scroll_frame_num)
            self.display_frame() 

    def click_right(self, event):
        """Move to the previous frame on the left."""
        if self.scroll_frame_num > 0:
            self.scroll_frame_num -= 1
            self.screenshot = self.get_screenshot(self.scroll_frame_num)
            self.display_frame()

    def clamp(self, value, min_value, max_value):
        return max(min_value, min(value, max_value))
    
    def near_corner(self, x, y, corner_x, corner_y, threshold=10):
        """Check if a click is near a box corner."""
        return abs(x - corner_x) <= threshold and abs(y - corner_y) <= threshold
    
    def check_click_on_box_corner(self, event):
        """Check if the click is on any existing box corners."""
        if self.screenshot.annotations is not None:
            for index, row in self.screenshot.annotations.iterrows():
                for corner in [('x1', 'y1'), ('x2', 'y2')]:
                    if self.near_corner(event.x, event.y, row[corner[0]], row[corner[1]]):
                        return True, index, corner
        return False, None, None
    
    def adjust_box_corner(self, event):
        """Adjust the position of a box corner."""
        if self.adjusting_box and self.adjusting_corner:
            x = self.clamp(event.x, 0, self.image_width)
            y = self.clamp(event.y, 0, self.image_height)
            row = self.screenshot.annotations.iloc[self.adjusting_box_index]
            row[self.adjusting_corner[0]], row[self.adjusting_corner[1]] = x, y
            self.screenshot.annotations.iloc[self.adjusting_box_index] = row
            self.redraw_canvas()
            self.adjusting_box = False
            self.adjusting_corner = None


    def handle_click(self, event):
        """Handle click events to define or adjust corners of the bounding box."""
        clicked_on_box, box_index, corner = self.check_click_on_box_corner(event)
        if clicked_on_box:
            print("Adjusting Box")
            self.adjusting_box = True
            self.adjusting_box_index = box_index
            self.adjusting_corner = corner
        elif self.adjusting_box:
            self.adjust_box_corner(event)
        elif not self.box_start:
            # First click - set start corner of the box
            x = self.clamp(event.x, 0, self.image_width)
            y = self.clamp(event.y, 0, self.image_height)
            self.box_start = (x, y)
        else:
            # Second click - finalize the box
            x = self.clamp(event.x, 0, self.image_width)
            y = self.clamp(event.y, 0, self.image_height)
            self.box_end = (x, y)
            self.finalize_box()
            self.box_start = None

    def redraw_canvas(self):
        """Redraw the canvas, including any bounding boxes."""
        self.display_frame()
        if self.screenshot.annotations is not None:
            for _, row in self.screenshot.annotations.iterrows():
                print((row['x1'], row['y1']), (row['x2'], row['y2']))
                self.draw_box(row)

    def draw_box(self, row):
        """Draw a rectangle and circles on corners for adjustment."""
        self.canvas.create_rectangle(row['x1'], row['y1'], row['x2'], row['y2'], outline='red', width=2)
        # Draw circles on corners
        for x, y in [(row['x1'], row['y1']), (row['x2'], row['y2'])]:
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill='blue')

        if 'label' in row and row['label']:
            self.canvas.create_text(row['x1'], row['y1'], text=row['label'], anchor='nw', fill='yellow')

    def finalize_box(self):
        """Save the coordinates of the bounding box and redraw."""
        if self.box_start and self.box_end:
            box = {
                "x1": min(self.box_start[0], self.box_end[0]),
                "y1": min(self.box_start[1], self.box_end[1]),
                "x2": max(self.box_start[0], self.box_end[0]),
                "y2": max(self.box_start[1], self.box_end[1]),
                "label": self.current_label.get()
            }
            
            if self.screenshot.annotations is None:
                self.screenshot.annotations = pd.DataFrame([box])
            else:
                self.screenshot.annotations = pd.concat([self.screenshot.annotations, pd.DataFrame([box])], ignore_index=True)
            self.redraw_canvas()
            self.box_start = None
            self.box_end = None

    def save_boxes(self):
        """Placeholder for function to save boxes to file or database."""
        print("Boxes saved:", self.screenshot.annotations)

    def on_window_close(self):
        self.exit_flag = True
        self.master.destroy()

def main():
    root = tk.Tk()
    app = AnnotatorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()