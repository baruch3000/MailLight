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
        
        # חסימת התרחבות: גודל מסך קבוע בדיוק לפי מידות המסך שלך
        self.root.geometry("800x480+0+0")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg="white")
        self.root.bind('<Double-Button-1>', self.secret_exit)
        
        try:
            original_image = Image.open("standby.png")
            # תמונה קטנה יותר כדי שלא תתפוס גובה
            resized_image = original_image.resize((80, 80), Image.Resampling.LANCZOS)
            self.sleep_img = ImageTk.PhotoImage(resized_image)
        except Exception as e: self.sleep_img = None 
            
        self.is_standby = True
        self.last_activity_time = 0
        self.cap = None
        
        # --- עיצוב מקובע (Pinned Layout) - שום דבר לא בורח מהמסך ---
        
        # 1. הכותרת (נעוצה למעלה באמצע)
        self.header_var = tk.StringVar()
        self.header_label = tk.Label(root, textvariable=self.header_var, font=("Helvetica", 22, "bold"), bg="white", cursor="hand2")
        self.header_label.place(relx=0.5, y=35, anchor=tk.CENTER)
        self.header_label.bind('<Button-1>', self.wake_up_system)
        
        self.arrow_var = tk.StringVar(value="")
        self.arrow_label = tk.Label(root, textvariable=self.arrow_var, font=("Helvetica", 20, "bold"), fg="red", bg="white")
        self.arrow_label.place(relx=0.5, y=80, anchor=tk.CENTER)
        
        # 2. הברקוד והוראות לשליח (נעוצים בצד ימין למעלה!)
        self.qr_inst_var = tk.StringVar()
        self.qr_inst_label = tk.Label(root, textvariable=self.qr_inst_var, font=("Helvetica", 14, "bold"), fg="#1976D2", bg="white")
        self.qr_inst_label.place(relx=0.96, y=15, anchor=tk.NE)
        
        self.qr_label = tk.Label(root, bg="white")
        self.qr_label.place(relx=0.96, y=45, anchor=tk.NE)
        
        # 3. טבלת התיבות (נעוצה למטה במרכז)
        self.grid_frame = tk.Frame(root, bg="white")
        self.grid_frame.place(relx=0.5, y=130, anchor=tk.N) 
        
        self.boxes = {}
        for i in range(1, 31):
            canvas = tk.Canvas(self.grid_frame, width=80, height=45, bg="#e0e0e0", highlightthickness=1, highlightbackground="#757575")
            canvas.create_rectangle(12, 8, 68, 12, fill="#333333", outline="")
            canvas.create_text(40, 25, text=str(i), font=("Helvetica", 12, "bold"), tags="txt")
            canvas.create_oval(35, 34, 45, 44, fill="#757575", outline="#333333")
            row = (i-1) // 5
            col = 4 - ((i-1) % 5)
            canvas.grid(row=row, column=col, padx=3, pady=2)
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
            os.system("pkill -f launch_kiosk.sh")
            self.root.destroy()

    def go_to_sleep(self):
        self.is_standby = True
        if self.cap is not None: self.cap.release(); self.cap = None
        if self.sleep_img:
            self.header_label.config(image=self.sleep_img, compound=tk.TOP, fg="#4CAF50")
            self.header_var.set(get_display("לסריקת מכתב - גע במסך"))
        else:
            self.header_label.config(image="", compound=tk.NONE, fg="#4CAF50")
            self.header_var.set(get_display("מערכת בשינה - גע במסך להפעלה"))
        self.arrow_var.set("")
        self.qr_label.config(image="")
        self.qr_inst_var.set("")
        if self.blink_timer: self.root.after_cancel(self.blink_timer); self.blink_timer = None
        for b in range(1, 31): self.boxes[b].config(bg="#e0e0e0")
        self.root.update()

    def wake_up_system(self, event=None):
        if not self.is_standby: return 
        self.is_standby = False; self.last_activity_time = time.time()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.header_label.config(image="", compound=tk.NONE, fg="red")
            self.header_var.set(get_display("שגיאה: מצלמה לא מחוברת!"))
            self.cap = None; self.root.after(5000, self.go_to_sleep); return
        self.header_label.config(image="", compound=tk.NONE, fg="black")
        self.header_var.set(get_display("העבר מעטפה מול המצלמה..."))
        self.qr_label.config(image="")
        self.qr_inst_var.set("")
        self.last_frame = None; self.is_processing = False; self.frame_counter = 0
        self.root.after(100, self.camera_loop)

    def camera_loop(self):
        if self.is_standby or self.cap is None: return 
        if time.time() - self.last_activity_time > 180: self.go_to_sleep(); return
        ret, frame = self.cap.read()
        if ret and not self.is_processing:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            if self.last_frame is None: self.last_frame = gray
            else:
                frame_delta = cv2.absdiff(self.last_frame, gray)
                thresh = cv2.threshold(frame_delta, 30, 255, cv2.THRESH_BINARY)[1]
                if cv2.countNonZero(thresh) > 3000:
                    self.last_activity_time = time.time(); self.is_processing = True; self.process_mail(frame)
                else:
                    self.frame_counter += 1
                    if self.frame_counter > 5: self.last_frame = gray; self.frame_counter = 0
        self.root.after(50, self.camera_loop)

    def process_mail(self, frame):
        text = analyze_image_content(frame)
        found_data, _ = check_tenants(text)
        if found_data:
            if self.blink_timer: self.root.after_cancel(self.blink_timer); self.blink_timer = None
            for b in range(1, 31): self.boxes[b].config(bg="#e0e0e0")
            display_text = " ו- ".join([f"{name} (תיבה {box})" for box, name in found_data])
            final_msg = f"המכתב שייך ל-{display_text}"
            self.header_var.set(get_display(final_msg))
            self.blinking_boxes = [b for b, n in found_data]
            self.update_arrow(self.blinking_boxes[0])
            self.blink_state = True
            try:
                target_box = self.blinking_boxes[0]
                url = f"https://maillight-app.com/delivery?box={target_box}"
                
                # ברקוד מותאם בגודלו כדי שלא יפלוש לשטחים אחרים
                qr = qrcode.QRCode(box_size=3, border=1)
                qr.add_data(url); qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                self.qr_photo = ImageTk.PhotoImage(img); self.qr_label.config(image=self.qr_photo)
                
                self.qr_inst_var.set(get_display("לשליח: סרוק ברקוד"))
            except Exception as e: print("QR Error:", e)
            self.blink()
        self.root.after(1500, self.end_cooldown)

    def end_cooldown(self):
        if self.is_standby: return
        self.last_frame = None; self.is_processing = False 

    def update_arrow(self, box_num):
        col = (box_num - 1) % 5
        if col in [0, 1]: self.arrow_var.set("➡️") 
        elif col == 2: self.arrow_var.set("⬇️") 
        else: self.arrow_var.set("⬅️") 
        
    def blink(self):
        if not self.blinking_boxes: return
        new_bg = "#fff59d" if self.blink_state else "#e0e0e0"
        for box_num in self.blinking_boxes: self.boxes[box_num].config(bg=new_bg)
        self.blink_state = not self.blink_state
        self.blink_timer = self.root.after(500, self.blink)

if __name__ == "__main__":
    root = tk.Tk()
    app = MailLightKiosk(root)
    root.mainloop()
