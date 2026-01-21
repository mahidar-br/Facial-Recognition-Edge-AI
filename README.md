# Facial Recognition Using CNNs – Edge AI Implementation

## Overview
This project is an academic implementation of a real-time facial recognition system using CNN-based facial embeddings.  
It was developed as a final-year engineering project and focuses on **edge AI deployment, low-latency processing, and system-level design** rather than proposing a new algorithm.

The system was deployed on Raspberry Pi hardware and designed to reflect constraints similar to smart wearable devices such as smart glasses.

---

## Key Features
- Real-time facial recognition using CNN-based embeddings
- Zero-Lag asynchronous architecture using multithreading
- Edge deployment on Raspberry Pi
- Liveness detection to prevent photo spoofing
- Offline-first cloud synchronization (Google Sheets)
- Physical feedback using a 16×2 LCD display
- Visitor/unknown detection and logging

---

## System Architecture
The system is divided into independent execution paths:
- **Video Capture Thread** – continuous camera feed
- **AI Processing Thread** – face recognition and liveness detection
- **Network Thread** – cloud synchronization
- **UI Thread** – user interaction and display

This architecture prevents UI freezing on low-power devices.

---

## Hardware Setup
![Hardware Setup](images/hardware_setup.jpg)

---

## Software Interface
![GUI Running](images/gui_running.png)

---

## Technologies Used
- Python 3
- OpenCV
- face_recognition (CNN-based embeddings)
- Raspberry Pi
- Tkinter (GUI)
- Google Sheets API
- Multithreading

---

## Notes on Academic Use
This project is an academic prototype developed for learning and demonstration purposes.  
The title aligns with existing research literature, but this work does not reproduce or extend any specific published paper.

---

## Future Scope
- Porting the pipeline to wearable smart-glass hardware
- Optimizing inference using TensorFlow Lite
- Adding AR-based output interfaces
