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
        self.root.geometry("800x480+0+0")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg="white")
        self.root.bind('<Double-Button-1>', self.secret_exit)
        
        self.is_standby = True
        self.cap = None
        
        self.header_var = tk.StringVar()
        self.header_label = tk.Label(root, textvariable=self.header_var, font=("Helvetica", 24, "bold"), bg="white")
        self.header_label.place(relx=0.5, y=60, anchor=tk.CENTER)
        
        self.qr_inst_var = tk.StringVar()
        self.qr_inst_label = tk.Label(root, textvariable=self.qr_inst_var, font=("Helvetica", 16, "bold"), fg="#1976D2", bg="white")
        self.qr_inst_label.place(relx=0.85, rely=0.4, anchor=tk.CENTER)
        
        self.qr_label = tk.Label(root, bg="white")
        self.qr_label.place(relx=0.85, rely=0.65, anchor=tk.CENTER)
        
        self.grid_frame = tk.Frame(root, bg="white")
        self.grid_frame.place(relx=0.5, y=140, anchor=tk.N) 
        
        self.boxes = {}
        for i in range(1, 31):
            canvas = tk.Canvas(self.grid_frame, width=80, height=45, bg="#e0e0e0", highlightthickness=1, highlightbackground="#757575")
            canvas.create_text(40, 25, text=str(i), font=("Helvetica", 12, "bold"))
            row = (i-1) // 5
            col = 4 - ((i-1) % 5)
            canvas.grid(row=row, column=col, padx=3, pady=2)
            self.boxes[i] = canvas
            
        self.go_to_sleep()

    def secret_exit(self, event):
        if self.cap: self.cap.release()
        self.root.destroy()

    def go_to_sleep(self):
        self.is_standby = True
        if self.cap: self.cap.release(); self.cap = None
        self.header_var.set(get_display("גע במסך להפעלה"))
        self.qr_label.config(image="")
        self.qr_inst_var.set("")
        self.root.update()
        self.root.after(1000, lambda: self.wake_up_system())

    def wake_up_system(self):
        self.is_standby = False
        self.cap = cv2.VideoCapture(0)
        self.header_var.set(get_display("סרוק מעטפה..."))
        self.camera_loop()

    def camera_loop(self):
        if self.is_standby: return
        ret, frame = self.cap.read()
        if ret:
            text = analyze_image_content(frame)
            found, _ = check_tenants(text)
            if found:
                box = found[0][0]
                self.header_var.set(get_display(f"מכתב לתיבה {box}"))
                url = f"https://maillight-app.com/delivery?box={box}"
                qr = qrcode.make(url)
                img = ImageTk.PhotoImage(qr.resize((100, 100)))
                self.qr_label.config(image=img)
                self.qr_label.image = img
                self.qr_inst_var.set(get_display("לשליח:\nסרוק ברקוד"))
                self.root.after(5000, self.go_to_sleep)
                return
        self.root.after(100, self.camera_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = MailLightKiosk(root)
    root.mainloop()
