import os
import time
import sys
from bidi.algorithm import get_display
import tkinter as tk
import cv2
import numpy as np
import json
from google.cloud import vision
from PIL import Image, ImageTk
import qrcode

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/baruch/Desktop/MailLight/key.json"

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

class MailLightKiosk:
    def __init__(self, root):
        self.root = root
        self.root.title(get_display("MailLight - מסך דוור חכם"))
        
        self.root.geometry("800x480+0+0")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg="white")
        self.root.bind('<Double-Button-1>', self.secret_exit)
        
        try:
            original_image = Image.open("standby.png")
            resized_image = original_image.resize((80, 80), Image.Resampling.LANCZOS)
            self.sleep_img = ImageTk.PhotoImage(resized_image)
        except Exception as e: self.sleep_img = None 
            
        self.is_standby = True
        self.last_activity_time = 0
        self.cap = None
        
        # --- הכותרת והתמונה ---
        self.header_var = tk.StringVar()
        self.header_label = tk.Label(root, textvariable=self.header_var, font=("Helvetica", 24, "bold"), bg="white", cursor="hand2")
        self.header_label.place(relx=0.5, y=60, anchor=tk.CENTER)
        self.header_label.bind('<Button-1>', self.wake_up_system)
        
        self.arrow_var = tk.StringVar(value="")
        self.arrow_label = tk.Label(root, textvariable=self.arrow_var, font=("Helvetica", 20, "bold"), fg="red", bg="white")
        self.arrow_label.place(relx=0.5, y=110, anchor=tk.CENTER)
        
        # --- הברקוד והטקסט (נעוצים בצד ימין באמצע) ---
        self.qr_inst_var = tk.StringVar()
        self.qr_inst_label = tk.Label(root, textvariable=self.qr_inst_var, font=("Helvetica", 16, "bold"), fg="#1976D2", bg="white", justify=tk.CENTER)
        self.qr_inst_label.place(relx=0.85, rely=0.4, anchor=tk.CENTER)
        
        self.qr_label = tk.Label(root, bg="white")
        self.qr_label.place(relx=0.85, rely=0.65, anchor=tk.CENTER)
        
        # --- כפתור "מצב שינה" ידני (נעוץ בצד ימין למטה) ---
        # הכפתור מופיע רק כשהמערכת ערה, ומוסתר כשהיא ישנה
        self.sleep_button = tk.Button(root, text=get_display("מצב שינה 💤"), font=("Helvetica", 12, "bold"), bg="#f44336", fg="white", activebackground="#d32f2f", activeforeground="white", command=self.go_to_sleep, bd=2, relief=tk.RAISED)
        
        # --- טבלת התיבות (נעוצה למטה במרכז) ---
        self.grid_frame = tk.Frame(root, bg="white")
        self.grid_frame.place(relx=0.5, y=140, anchor=tk.N) 
        
        self.boxes = {}
        for i in range(1, 31):
            canvas = tk.Canvas(self.grid_frame, width=80, height=45, bg="#e0e0e0", highlightthickness=1, highlightbackground="#757575")
            canvas.create_rectangle(12, 8, 68, 12, fill="#333333", outline="")
            canvas.create_text(40, 25, text=str(i), font=("Helvetica", 12, "bold"), tags="txt")
            canvas.create_oval(35, 34, 45, 44, fill="#757575", outline="#333333")
            row = (i-1) // 5
            col = 4 - ((i-1) % 5)
            canvas.grid(row=row, column=col, padx=3, pady=2)
