import tkinter as tk

from tkinter import messagebox, filedialog

import cv2

import face_recognition

import os

import pickle

import threading

import time

import numpy as np

import gspread

from oauth2client.service_account import ServiceAccountCredentials

from datetime import datetime

import RPi.GPIO as GPIO

from PIL import Image, ImageTk



# --- GPIO LCD SETUP ---

GPIO.setwarnings(False)

GPIO.setmode(GPIO.BCM)

LCD_RS, LCD_E = 26, 19

LCD_D4, LCD_D5, LCD_D6, LCD_D7 = 13, 6, 5, 11

LCD_WIDTH, LCD_CHR, LCD_CMD = 16, True, False

LCD_LINE_1, LCD_LINE_2 = 0x80, 0xC0

E_PULSE, E_DELAY = 0.0005, 0.0005



for pin in [LCD_E, LCD_RS, LCD_D4, LCD_D5, LCD_D6, LCD_D7]:

    GPIO.setup(pin, GPIO.OUT)



def lcd_byte(bits, mode):

    GPIO.output(LCD_RS, mode)

    for pin, bit in zip([LCD_D4, LCD_D5, LCD_D6, LCD_D7], [0x10, 0x20, 0x40, 0x80]):

        GPIO.output(pin, bool(bits & bit))

    lcd_toggle_enable()

    for pin, bit in zip([LCD_D4, LCD_D5, LCD_D6, LCD_D7], [0x01, 0x02, 0x04, 0x08]):

        GPIO.output(pin, bool(bits & bit))

    lcd_toggle_enable()



def lcd_toggle_enable():

    time.sleep(E_DELAY); GPIO.output(LCD_E, True)

    time.sleep(E_PULSE); GPIO.output(LCD_E, False)

    time.sleep(E_DELAY)



def lcd_string(message, line):

    message = str(message).ljust(LCD_WIDTH, " ")

    lcd_byte(line, LCD_CMD)

    for char in message: lcd_byte(ord(char), LCD_CHR)



def lcd_init():

    for cmd in [0x33, 0x32, 0x06, 0x0C, 0x28, 0x01]: lcd_byte(cmd, LCD_CMD)

    time.sleep(E_DELAY)



lcd_init()

lcd_string("SYSTEM READY", LCD_LINE_1)



# --- THREADED CAMERA ENGINE ---

class VideoStream:

    def __init__(self):

        self.stream = cv2.VideoCapture(0)

        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 320)

        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        self.stopped = False

        self.frame = None



    def start(self):

        threading.Thread(target=self.update, args=(), daemon=True).start()

        return self



    def update(self):

        while not self.stopped:

            ret, frame = self.stream.read()

            if ret: self.frame = frame 



    def read(self): return self.frame



    def stop(self):

        self.stopped = True

        self.stream.release()



# --- MAIN APP ---

class SmartAttendanceAI:

    def __init__(self, root):

        self.root = root

        self.root.title("Pro-AI Attendance (Liveness+Sync)")

        self.root.geometry("450x550")

        

        tk.Label(root, text="Student Name:").pack(pady=5)

        self.name_var = tk.Entry(root); self.name_var.pack()

        tk.Label(root, text="Student ID:").pack(pady=5)

        self.id_var = tk.Entry(root); self.id_var.pack()



        tk.Button(root, text="1. Secure Capture", command=self.live_capture, bg="#3498db", fg="white", width=25).pack(pady=5)

        tk.Button(root, text="2. Train Model", command=self.train_model, bg="#f39c12", width=25).pack(pady=5)

        tk.Button(root, text="3. Detect (Liveness ON)", command=self.live_detect, bg="#27ae60", fg="white", width=25).pack(pady=5)



        self.detecting = False

        self.latest_label = "Scanning..."

        self.already_logged = {} 



    def train_model(self):

        known_encs, known_names = [], []

        if not os.path.exists("dataset"): os.makedirs("dataset"); return

        for file in os.listdir("dataset"):

            img = face_recognition.load_image_file(f"dataset/{file}")

            enc = face_recognition.face_encodings(img)

            if enc:

                known_encs.append(enc[0])

                known_names.append(file.replace(".jpg", ""))

        with open("trained_model.pkl", "wb") as f:

            pickle.dump((known_encs, known_names), f)

        messagebox.showinfo("Success", "128-Nodal Training Complete!")



    def update_google_sheets(self, name, sid):

        """Offline Mode + Auto Sync Logic"""

        now = datetime.now()

        date_s, time_s = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

        row = [sid, name, date_s, time_s]

        

        try:

            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

            creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)

            client = gspread.authorize(creds)

            sheet = client.open("Attendance_System").worksheet("Attendance_Raw")



            # Auto-Sync: Check if we have offline data to push

            if os.path.exists("offline_logs.csv"):

                with open("offline_logs.csv", "r") as f:

                    for line in f:

                        sheet.append_row(line.strip().split(","))

                os.remove("offline_logs.csv")

                print("🔄 Offline Buffer Synced!")



            sheet.append_row(row)

            print(f"✅ Cloud Success: {name}")

        except:

            # Save to Local Buffer if offline

            with open("offline_logs.csv", "a") as f:

                f.write(f"{sid},{name},{date_s},{time_s}\n")

            print("⚠️ Saved to Offline Buffer")



    def detection_worker(self, vs, known_encs, known_names):

        """Liveness Check + Recognition + Visitor Alert"""

        last_nose_y = 0

        motion_score = 0

        

        while self.detecting:

            frame = vs.read()

            if frame is None: continue

            

            small = cv2.resize(frame, (160, 120))

            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            

            # Use landmarks for Liveness (Blink/Movement)

            landmarks = face_recognition.face_landmarks(rgb_small)

            face_locs = face_recognition.face_locations(rgb_small)

            face_encs = face_recognition.face_encodings(rgb_small, face_locs)



            if face_encs and landmarks:

                for enc, lmark in zip(face_encs, landmarks):

                    # 1. Anti-Proxy: Check for micro-motion of nose

                    nose = lmark['nose_bridge'][0][1]

                    if abs(nose - last_nose_y) > 0.3: motion_score += 1

                    last_nose_y = nose



                    matches = face_recognition.compare_faces(known_encs, enc, tolerance=0.45)

                    

                    if True in matches:

                        idx = matches.index(True)

                        n, s = known_names[idx].split("_")

                        

                        # Only log if user isn't a static photo (motion_score check)

                        if motion_score > 3:

                            self.latest_label = f"LIVE: {n}"

                            lcd_string(f"VERIFIED: {s}", LCD_LINE_1)

                            lcd_string(f"HI {n[:13]}", LCD_LINE_2)

                            

                            cur = time.time()

                            if n not in self.already_logged or (cur - self.already_logged[n]) > 300:

                                self.already_logged[n] = cur

                                threading.Thread(target=self.update_google_sheets, args=(n, s), daemon=True).start()

                        else:

                            self.latest_label = "Liveness: BLINK NOW"

                    else:

                        # 2. Visitor Alert Mode

                        self.latest_label = "UNKNOWN - ALERT"

                        lcd_string("SECURITY ALERT", LCD_LINE_1)

                        if not os.path.exists("visitors"): os.makedirs("visitors")

                        cv2.imwrite(f"visitors/alert_{int(time.time())}.jpg", frame)

            else:

                self.latest_label = "Scanning..."

                motion_score = 0

            

            time.sleep(0.05)



    def live_detect(self):

        if not os.path.exists("trained_model.pkl"): return

        with open("trained_model.pkl", "rb") as f:

            known_encs, known_names = pickle.load(f)



        vs = VideoStream().start()

        self.detecting = True

        threading.Thread(target=self.detection_worker, args=(vs, known_encs, known_names), daemon=True).start()



        while self.detecting:

            frame = vs.read()

            if frame is not None:

                cv2.putText(frame, self.latest_label, (10, 25), 0, 0.6, (0, 255, 0), 2)

                cv2.imshow("Smart-AI Security Feed", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'): break

        

        self.detecting = False

        vs.stop(); cv2.destroyAllWindows()



    def live_capture(self):

        name, sid = self.name_var.get(), self.id_var.get()

        if not name or not sid: return

        cap = cv2.VideoCapture(0)

        while True:

            ret, frame = cap.read()

            if not ret: break

            cv2.imshow("Capture - Press S", frame)

            if cv2.waitKey(1) & 0xFF == ord('s'):

                if not os.path.exists("dataset"): os.makedirs("dataset")

                cv2.imwrite(f"dataset/{name}_{sid}.jpg", frame)

                break

        cap.release(); cv2.destroyAllWindows()



if __name__ == "__main__":

    root = tk.Tk(); app = SmartAttendanceAI(root)

    root.mainloop(); GPIO.cleanup()
