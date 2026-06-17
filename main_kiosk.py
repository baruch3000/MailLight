import os
import time
import sys
import urllib.request
from bidi.algorithm import get_display
import tkinter as tk
import cv2
import numpy as np
import json
from google.cloud import vision
from PIL import Image, ImageTk
import qrcode

# הגדרת המפתח של גוגל
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/baruch/Desktop/MailLight/key.json"

# --- כתובת העדכון האוטומטי המדויקת ---
UPDATE_URL = "https://raw.githubusercontent.com/baruch3000/MailLight/main/main_kiosk.py"

# --- טעינת נתונים ---
try:
    with open('tenants.json', 'r', encoding='utf-8') as file:
        tenants = json.load(file)
except FileNotFoundError:
    tenants = {}

client = vision.ImageAnnotatorClient()

def analyze_image_content(frame):
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, processed_image = cv2.imencode('.jpg', img)
    final_bytes = processed_image.tobytes()
    image_context = {'language_hints': ['he', 'iw']}
    image = vision.Image(content=final_bytes)
    response = client.annotate_image({
        'image': {'content': final_bytes},
        'features': [{'type_': vision.Feature.Type.TEXT_DETECTION}], 
        'image_context': image_context
    })
    return response.full_text_annotation.text if response.full_text_annotation else ""

def check_tenants(text):
    if not text: return [], ""
    text_clean = "".join(text.split()).lower()
    results = []
    for box, name in tenants.items():
        if "".join(name.split()).lower() in text_clean:
            results.append((int(box), name))
    return results, text

# --- ממשק גרפי ---
class MailLightKiosk:
    def __init__(self, root):
        self.root = root
        self.root.title(get_display("MailLight - מסך דוור חכם"))
        self.root.geometry("800x480")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg="white")
        
        self.root.bind('<Double-Button-1>', self.secret_exit)
        
        try:
            original_image = Image.open("standby.png")
            resized_image = original_image.resize((120, 120), Image.Resampling.LANCZOS)
            self.sleep_img = ImageTk.PhotoImage(resized_image)
        except Exception as e:
            self.sleep_img = None 
            
        self.is_standby = True
        self.last_activity_time = 0
        self.cap = None
        
        self.header_var = tk.StringVar()
        self.header_label = tk.Label(root, textvariable=self.header_var, font=("Helvetica", 26, "bold"), bg="white", cursor="hand2")
        self.header_label.pack(pady=5)
        self.header_label.bind('<Button-1>', self.wake_up_system)
        
        self.arrow_var = tk.StringVar(value="")
        tk.Label(root, textvariable=self.arrow_var, font=("Helvetica", 22, "bold"), fg="red", bg="white").pack()

        # לייבל חדש עבור ה-QR קוד
        self.qr_label = tk.Label(root, bg="white")
        self.qr_label.pack(pady=5)
        
        self.grid_frame = tk.Frame(root, bg="white")
        self.grid_frame.pack()
        
        self.boxes = {}
        for i in range(1, 31):
            canvas = tk.Canvas(self.grid_frame, width=90, height=45, bg="#e0e0e0", highlightthickness=2, highlightbackground="#757575")
            canvas.create_rectangle(15, 8, 75, 12, fill="#333333", outline="")
            canvas.create_text(45, 25, text=str(i), font=("Helvetica", 12, "bold"), tags="txt")
            canvas.create_oval(40, 34, 50, 44, fill="#757575", outline="#333333")
            row = (i-1) // 5
            col = 4 - ((i-1) % 5)
            canvas.grid(row=row, column=col, padx=2, pady=1)
            self.boxes[i] = canvas
            
        self.blinking_boxes = []
        self.blink_state = False
        self.blink_timer = None 
        self.last_frame = None
        self.is_processing = False
        self.frame_counter = 0
        
        self.go_to_sleep()

    def secret_exit(self, event):
        if event.x_root < 70 and event.y_root < 70:
            if self.cap is not None: self.cap.release()
            self.root.destroy()

    def go_to_sleep(self):
        self.is_standby = True
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        if self.sleep_img:
            self.header_label.config(image=self.
